"""Security headers and login rate limiting (P2-06)."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


def _login_rate_limit() -> int:
    return int(os.getenv("LOGIN_RATE_LIMIT", "10"))


def _login_rate_window() -> int:
    return int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "60"))


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window limiter for POST /auth/login."""

    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_limited(self, key: str) -> bool:
        limit = _login_rate_limit()
        window = _login_rate_window()
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if len(bucket) >= limit:
                return True
            bucket.append(now)
            return False

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.rstrip("/") or "/"
        if request.method == "POST" and path.endswith("/auth/login"):
            if self._is_limited(self._client_key(request)):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Muitas tentativas de login. Tente novamente em breve."},
                    headers={"Retry-After": str(_login_rate_window())},
                )
        return await call_next(request)
