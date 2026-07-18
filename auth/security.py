import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_JWT_SECRET = "change-me-in-production"
WEAK_ADMIN_PASSWORDS = frozenset({"admin123", "CHANGE_ME_STRONG_PASSWORD", ""})

JWT_SECRET = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))


def validate_production_config() -> None:
    """Fail fast when production is misconfigured."""
    env = os.getenv("ENV", "development").lower()
    if env != "production":
        return

    secret = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    if not secret or secret == DEFAULT_JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be set to a secure, unique value when ENV=production.")

    admin_password = os.getenv("ADMIN_PASSWORD") or ""
    if admin_password in WEAK_ADMIN_PASSWORDS:
        raise RuntimeError("ADMIN_PASSWORD must be set to a strong password when ENV=production.")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


PDV_AUTHORIZE_EXPIRE_SECONDS = int(os.getenv("PDV_AUTHORIZE_EXPIRE_SECONDS", "120"))


def create_access_token(*, user_id: int, profile: str, company_id: int) -> tuple[str, int]:
    expires_in = JWT_EXPIRE_HOURS * 3600
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "sub": str(user_id),
        "profile": profile,
        "company_id": company_id,
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
        "typ": "pdv_authorization",
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
