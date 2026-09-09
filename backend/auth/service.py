from datetime import datetime, timezone

from jose import JWTError
from sqlmodel import Session

from organization.repository import CompanyRepository
from shared.audit import AuditService
from shared.exceptions import UnauthorizedException, ValidationError
from shared.identity.pdv_credentials import PDV_PIN_LENGTH, is_supervisor_plus
from shared.identity.permissions import has_permission
from shared.identity.security import (
    PDV_AUTHORIZATION_TYP,
    create_access_token,
    create_pdv_authorization_token,
    decode_access_token,
    hash_password,
    verify_password,
    verify_pdv_pin,
)
from users.models import User
from users.repository import UserRepository
from utils.cnpj import normalize_cnpj
from utils.enums import AuditAction

ALLOWED_PDV_ACTIONS = frozenset({"discount", "cancel"})


def bump_token_version(user: User) -> None:
    user.token_version = int(getattr(user, "token_version", 1) or 1) + 1


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def login(self, login: str, password: str, *, company_document: str) -> dict:
        company = self._resolve_company(company_document)
        user = UserRepository.find_by_login(self.db, login, company_id=company.id)
        return self._issue_token_for_user(user, password=password)

    def pdv_login(self, *, company_document: str, pdv_id: str, password: str) -> dict:
        company = self._resolve_company(company_document)
        normalized_pdv_id = self._normalize_pdv_id(pdv_id)
        user = UserRepository.find_by_pdv_id(self.db, normalized_pdv_id, company_id=company.id)
        return self._issue_token_for_user(user, password=password)

    def pdv_authorize(
        self,
        *,
        operator: User,
        pdv_id: str,
        pin: str,
        actions: list[str],
    ) -> dict:
        if not actions:
            raise ValidationError("At least one action is required.")
        normalized_actions = [action.strip().lower() for action in actions]
        if any(action not in ALLOWED_PDV_ACTIONS for action in normalized_actions):
            raise ValidationError("Invalid PDV authorization action.")

        normalized_pdv_id = self._normalize_pdv_id(pdv_id)
        supervisor = UserRepository.find_by_pdv_id(
            self.db, normalized_pdv_id, company_id=operator.company_id
        )
        if (
            not supervisor
            or not supervisor.is_active
            or not is_supervisor_plus(supervisor.profile)
            or not supervisor.pdv_pin_hash
        ):
            raise UnauthorizedException("Invalid supervisor credentials.")

        if not verify_pdv_pin(self._normalize_pin(pin), supervisor.pdv_pin_hash):
            raise UnauthorizedException("Invalid supervisor credentials.")

        for action in normalized_actions:
            if not has_permission(supervisor.profile, f"sales:{action}"):
                raise UnauthorizedException(f"Supervisor cannot authorize {action}.")

        token, expires_in = create_pdv_authorization_token(
            supervisor_user_id=supervisor.id,
            company_id=operator.company_id,
            actions=normalized_actions,
            operator_user_id=operator.id,
        )
        return {
            "authorization_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "actions": normalized_actions,
            "supervisor_user_id": supervisor.id,
            "supervisor_pdv_id": supervisor.pdv_id,
        }

    def validate_pdv_authorization(
        self,
        *,
        token: str,
        operator: User,
        required_action: str,
    ) -> int:
        try:
            payload = decode_access_token(token)
        except JWTError as exc:
            raise UnauthorizedException("Invalid supervisor authorization.") from exc

        if payload.get("typ") != PDV_AUTHORIZATION_TYP:
            raise UnauthorizedException("Invalid supervisor authorization.")
        if int(payload.get("company_id", 0)) != operator.company_id:
            raise UnauthorizedException("Invalid supervisor authorization.")
        if int(payload.get("operator_user_id", 0)) != operator.id:
            raise UnauthorizedException("Invalid supervisor authorization.")

        actions = payload.get("actions") or []
        if required_action not in actions:
            raise UnauthorizedException(f"Authorization does not include {required_action}.")

        return int(payload["sub"])

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
        if verify_password(new_password, user.password_hash):
            raise ValidationError("New password must be different from the current password.")

        user.password_hash = hash_password(new_password)
        bump_token_version(user)
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

    def _issue_token_for_user(self, user: User | None, *, password: str) -> dict:
        if not user or not user.is_active:
            raise UnauthorizedException("Invalid credentials.")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid credentials.")

        if not user.email and not user.username:
            raise UnauthorizedException("Invalid credentials.")

        if user.company_id is None:
            raise UnauthorizedException("Invalid credentials.")

        token, expires_in = create_access_token(
            user_id=user.id,
            profile=user.profile.value,
            company_id=user.company_id,
            token_version=int(getattr(user, "token_version", 1) or 1),
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    def _resolve_company(self, company_document: str):
        document = normalize_cnpj(company_document)
        if len(document) != 14:
            raise ValidationError("company_document must be a CNPJ with 14 digits.")
        company = CompanyRepository.find_by_document(self.db, document)
        if not company or not company.is_active:
            raise UnauthorizedException("Invalid credentials.")
        return company

    @staticmethod
    def _normalize_pdv_id(pdv_id: str) -> str:
        digits = "".join(ch for ch in pdv_id if ch.isdigit())
        if len(digits) != 6:
            raise ValidationError("pdv_id must contain exactly 6 digits.")
        return digits

    @staticmethod
    def _normalize_pin(pin: str) -> str:
        digits = "".join(ch for ch in pin if ch.isdigit())
        if len(digits) != PDV_PIN_LENGTH:
            raise ValidationError(f"PIN must contain exactly {PDV_PIN_LENGTH} digits.")
        return digits
