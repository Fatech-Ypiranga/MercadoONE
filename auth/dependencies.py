from typing import Annotated, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session

from auth.permissions import has_permission
from auth.security import decode_access_token
from database.connection import get_db
from models.user import User
from repositories.user_repository import UserRepository
from services.exceptions import ForbiddenException, UnauthorizedException

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedException("Authentication required.")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise UnauthorizedException("Invalid or expired token.")

    user = UserRepository.find_by_id(db, user_id)
    if not user or not user.is_active:
        raise UnauthorizedException("Invalid or inactive user.")

    return user


def require_permission(permission: str) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user.profile, permission):
            raise ForbiddenException(f"Permission denied: {permission}")
        return current_user

    return dependency
