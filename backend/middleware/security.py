"""Security headers and auth endpoint rate limiting."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",
}

# Paths that accept unauthenticated or credential-guessing traffic.
_RATE_LIMITED_POST_SUFFIXES = (
    "/auth/login",
    "/auth/pdv-login",
    "/auth/pdv-authorize",
    "/auth/change-password",
    "/company-registrations",
)


def _trusted_proxy_hosts() -> set[str]:
    raw = os.getenv("TRUSTED_PROXY_HOSTS", "127.0.0.1,::1")
    return {host.strip() for host in raw.split(",") if host.strip()}


def resolve_client_ip(request: Request) -> str:
    """Prefer peer address; honour X-Forwarded-For only behind trusted proxies."""
    peer = request.client.host if request.client else "unknown"
    trusted = _trusted_proxy_hosts()
    if peer not in trusted:
        return peer
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or peer
    return peer


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


def _login_rate_limit() -> int:
    return int(os.getenv("LOGIN_RATE_LIMIT", "10"))


def _login_rate_window() -> int:
    return int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "60"))


class RateLimiter(Protocol):
    def is_limited(self, key: str) -> bool: ...


class InMemoryRateLimiter:
    """Process-local sliding-window limiter (fallback when Redis is unset)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def is_limited(self, key: str) -> bool:
        limit = _login_rate_limit()
        window = _login_rate_window()
        now = time.monotonic()
        with self._lock:
            stale_keys = [
                k for k, bucket in self._hits.items() if not bucket or now - bucket[-1] > window * 2
            ]
            for stale in stale_keys[:64]:
                del self._hits[stale]

            bucket = self._hits[key]
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if len(bucket) >= limit:
                return True
            bucket.append(now)
            return False


class RedisRateLimiter:
    """Shared sliding-window limiter via Redis INCR + EXPIRE."""

    def __init__(self, client) -> None:
        self._client = client

    def is_limited(self, key: str) -> bool:
        limit = _login_rate_limit()
        window = _login_rate_window()
        redis_key = f"pyerp:login_rl:{key}"
        count = self._client.incr(redis_key)
        if count == 1:
            self._client.expire(redis_key, window)
        return int(count) > limit


def build_rate_limiter() -> RateLimiter:
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return InMemoryRateLimiter()
    try:
        import redis

        client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        logger.info("Login rate limit backend: redis")
        return RedisRateLimiter(client)
    except Exception:
        logger.warning(
            "REDIS_URL set but unreachable; falling back to in-memory rate limit",
            exc_info=True,
        )
        return InMemoryRateLimiter()


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limiter for auth-sensitive POST endpoints."""

    def __init__(self, app, limiter: RateLimiter | None = None):
        super().__init__(app)
        self._limiter = limiter or build_rate_limiter()

    @staticmethod
    def _is_rate_limited_path(path: str) -> bool:
        return any(path.endswith(suffix) for suffix in _RATE_LIMITED_POST_SUFFIXES)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.rstrip("/") or "/"
        if request.method == "POST" and self._is_rate_limited_path(path):
            if self._limiter.is_limited(resolve_client_ip(request)):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Muitas tentativas. Tente novamente em breve."},
                    headers={"Retry-After": str(_login_rate_window())},
                )
        return await call_next(request)
