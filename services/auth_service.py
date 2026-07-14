from datetime import datetime, timezone

from sqlmodel import Session

from auth.security import create_access_token, hash_password, verify_password
from models.user import User
from repositories.user_repository import UserRepository
from services.audit_service import AuditService
from services.exceptions import UnauthorizedException, ValidationError
from utils.enums import AuditAction


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def login(self, login: str, password: str) -> dict:
        user = UserRepository.find_by_login(self.db, login)
        if not user or not user.is_active:
            raise UnauthorizedException("Invalid credentials.")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid credentials.")

        if not user.email and not user.username:
            raise UnauthorizedException("User has no login identifier configured.")

        if user.company_id is None:
            raise UnauthorizedException("User is not linked to a company.")

        token, expires_in = create_access_token(
            user_id=user.id,
            profile=user.profile.value,
            company_id=user.company_id,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect.")

        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        user.updated_by = user.id
        self.db.add(user)

        AuditService(self.db).log(
            user_id=user.id,
            company_id=user.company_id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user.id,
            ip_address=ip_address,
        )
        self.db.commit()
