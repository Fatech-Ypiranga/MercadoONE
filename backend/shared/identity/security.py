import os
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jwt import InvalidTokenError
from passlib.context import CryptContext

# bcrypt_sha256 avoids silent 72-byte truncation; bcrypt kept for legacy hashes.
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
_pdv_pin_hasher = PasswordHasher()

DEFAULT_JWT_SECRET = "change-me-in-production"
WEAK_ADMIN_PASSWORDS = frozenset(
    {
        "admin123",
        "CHANGE_ME_STRONG_PASSWORD",
        "",
        "password",
        "12345678",
        "admin",
        "qwerty",
        "pyerp2025",
    }
)

JWT_SECRET = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))
ACCESS_TOKEN_TYP = "access"
PDV_AUTHORIZATION_TYP = "pdv_authorization"


NON_PRODUCTION_ENVS = frozenset({"development", "test", "local"})


def is_production_env() -> bool:
    """Treat unset or unrecognized ENV values as production, not development.

    A deploy that forgets to set ENV must fail safe (strict config checks,
    hidden API docs) rather than silently behave like a developer's laptop
    with a hardcoded JWT secret and no admin-password strength check.
    """
    env = os.getenv("ENV")
    if env is None:
        return True
    return env.strip().lower() not in NON_PRODUCTION_ENVS


def validate_production_config() -> None:
    """Fail fast when production is misconfigured."""
    if not is_production_env():
        return

    secret = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    if not secret or secret == DEFAULT_JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be set to a secure, unique value when ENV=production.")

    admin_password = os.getenv("ADMIN_PASSWORD") or ""
    if admin_password in WEAK_ADMIN_PASSWORDS or len(admin_password) < 12:
        raise RuntimeError("ADMIN_PASSWORD must be set to a strong password when ENV=production.")

    allow_missing_sentry = os.getenv("ALLOW_MISSING_SENTRY", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not os.getenv("SENTRY_DSN", "").strip() and not allow_missing_sentry:
        raise RuntimeError(
            "SENTRY_DSN must be set when ENV=production (or set ALLOW_MISSING_SENTRY=1 to bypass)."
        )

    workers = int(os.getenv("UVICORN_WORKERS", "1") or "1")
    allow_missing_redis = os.getenv("ALLOW_MISSING_REDIS", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if workers > 1 and not os.getenv("REDIS_URL", "").strip() and not allow_missing_redis:
        raise RuntimeError(
            "REDIS_URL must be set when UVICORN_WORKERS>1 in production "
            "(shared login rate limit), or set ALLOW_MISSING_REDIS=1 to bypass."
        )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_pdv_pin(pin: str) -> str:
    return _pdv_pin_hasher.hash(pin)


def verify_pdv_pin(pin: str, hashed_pin: str) -> bool:
    try:
        return _pdv_pin_hasher.verify(hashed_pin, pin)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


PDV_AUTHORIZE_EXPIRE_SECONDS = int(os.getenv("PDV_AUTHORIZE_EXPIRE_SECONDS", "120"))


def create_access_token(
    *,
    user_id: int,
    profile: str,
    company_id: int,
    token_version: int = 1,
) -> tuple[str, int]:
    expires_in = JWT_EXPIRE_HOURS * 3600
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "typ": ACCESS_TOKEN_TYP,
        "sub": str(user_id),
        "profile": profile,
        "company_id": company_id,
        "ver": int(token_version),
        "exp": expire,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_in


def create_pdv_authorization_token(
    *,
    supervisor_user_id: int,
    company_id: int,
    actions: list[str],
    operator_user_id: int,
) -> tuple[str, int]:
    expires_in = PDV_AUTHORIZE_EXPIRE_SECONDS
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "typ": PDV_AUTHORIZATION_TYP,
        "sub": str(supervisor_user_id),
        "company_id": company_id,
        "operator_user_id": operator_user_id,
        "actions": actions,
        "exp": expire,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def decode_and_require_access_token(token: str) -> dict:
    """Decode JWT and require typ=access (rejects PDV authorization tokens)."""
    payload = decode_access_token(token)
    typ = payload.get("typ")
    # Legacy access tokens (pre-typ claim) are treated as access.
    if typ is not None and typ != ACCESS_TOKEN_TYP:
        raise InvalidTokenError("Token type is not an access token.")
    return payload
