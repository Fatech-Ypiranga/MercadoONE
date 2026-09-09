from typing import Annotated, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session

from database.connection import get_db
from models.user import User
from repositories.user_repository import UserRepository
from services.exceptions import ForbiddenException, UnauthorizedException
from shared.identity.permissions import has_permission
from shared.identity.security import decode_and_require_access_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedException("Authentication required.")

    try:
        payload = decode_and_require_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        token_ver = int(payload.get("ver", 1))
    except (JWTError, KeyError, ValueError, TypeError):
        raise UnauthorizedException("Invalid or expired token.")

    user = UserRepository.find_by_id(db, user_id)
    if not user or not user.is_active:
        raise UnauthorizedException("Invalid or inactive user.")

    current_ver = int(getattr(user, "token_version", 1) or 1)
    if token_ver != current_ver:
        raise UnauthorizedException("Invalid or expired token.")

    return user


def require_permission(permission: str) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user.profile, permission):
            raise ForbiddenException(f"Permission denied: {permission}")
        return current_user

    return dependency
