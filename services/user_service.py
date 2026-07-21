from datetime import datetime, timezone

from sqlmodel import Session

from auth.security import hash_password, hash_pdv_pin
from models.user import User, UserCreate, UserPdvPinResponse, UserResponse, UserUpdate
from repositories.company_repository import BranchRepository, StoreRepository
from repositories.user_repository import UserRepository
from services.audit_service import AuditService
from services.auth_service import bump_token_version
from services.exceptions import ConflictException, ResourceNotFoundException, ValidationError
from services.pdv_credentials import (
    PDV_PIN_LENGTH,
    ensure_pdv_id,
    generate_pdv_id,
    generate_pdv_pin,
    is_pdv_eligible,
    is_supervisor_plus,
)
from utils.cpf import is_valid_cpf, normalize_cpf
from utils.enums import AuditAction, UserProfile


def to_user_response(user: User) -> UserResponse:
    data = UserResponse.model_validate(user)
    data.has_pdv_pin = bool(user.pdv_pin_hash)
    return data


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def list_users(
        self,
        company_id: int,
        *,
        q: str | None = None,
        profile: UserProfile | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        return UserRepository.find_all(
            self.db,
            company_id=company_id,
            include_inactive=True,
            q=q,
            profile=profile,
            is_active=is_active,
        )

    def get_by_id(self, user_id: int, company_id: int) -> User:
        user = UserRepository.find_by_id(self.db, user_id, company_id=company_id)
        if not user:
            raise ResourceNotFoundException(f"User with ID {user_id} was not found.")
        return user

    def create_user(self, user_in: UserCreate, *, company_id: int, actor_id: int) -> User:
        cpf = self._normalize_and_validate_cpf(user_in.cpf)
        self._validate_unique_fields(company_id, cpf, user_in.email, user_in.username)
        self._validate_login_identifiers(user_in.email, user_in.username)
        self._validate_org_defaults(
            company_id,
            default_branch_id=user_in.default_branch_id,
            default_store_id=user_in.default_store_id,
        )

        user = User(
            full_name=user_in.full_name,
            cpf=cpf,
            email=user_in.email,
            username=user_in.username,
            profile=user_in.profile,
            is_active=user_in.is_active,
            company_id=company_id,
            default_branch_id=user_in.default_branch_id,
            default_store_id=user_in.default_store_id,
            password_hash=hash_password(user_in.password),
            created_by=actor_id,
            updated_by=actor_id,
        )
        UserRepository.create(self.db, user)
        ensure_pdv_id(self.db, user)
        self.db.add(user)

        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.CREATE,
            entity_type="user",
            entity_id=user.id,
            details={"profile": user.profile.value, "pdv_id": user.pdv_id},
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(
        self, user_id: int, user_in: UserUpdate, *, company_id: int, actor_id: int
    ) -> User:
        user = self.get_by_id(user_id, company_id)
        update_data = user_in.model_dump(exclude_unset=True)

        if "cpf" in update_data:
            update_data["cpf"] = self._normalize_and_validate_cpf(update_data["cpf"])
            existing = UserRepository.find_by_cpf(
                self.db, update_data["cpf"], company_id=company_id
            )
            if existing and existing.id != user_id:
                raise ValidationError("CPF already registered.")

        if "email" in update_data and update_data["email"]:
            existing = UserRepository.find_by_email(
                self.db, update_data["email"], company_id=company_id
            )
            if existing and existing.id != user_id:
                raise ValidationError("Email already registered.")

        if "username" in update_data and update_data["username"]:
            existing = UserRepository.find_by_username(
                self.db, update_data["username"], company_id=company_id
            )
            if existing and existing.id != user_id:
                raise ValidationError("Username already registered.")

        branch_id = update_data.get("default_branch_id", user.default_branch_id)
        store_id = update_data.get("default_store_id", user.default_store_id)
        if "default_branch_id" in update_data or "default_store_id" in update_data:
            self._validate_org_defaults(
                company_id,
                default_branch_id=branch_id,
                default_store_id=store_id,
            )

        profile_changed = "profile" in update_data and update_data["profile"] != user.profile
        deactivated = (
            "is_active" in update_data and update_data["is_active"] is False and user.is_active
        )

        for field_name, field_value in update_data.items():
            setattr(user, field_name, field_value)

        if is_pdv_eligible(user.profile):
            ensure_pdv_id(self.db, user)
        else:
            user.pdv_id = None
            user.pdv_pin_hash = None

        if not is_supervisor_plus(user.profile):
            user.pdv_pin_hash = None

        if deactivated:
            bump_token_version(user)

        user.updated_at = datetime.now(timezone.utc)
        user.updated_by = actor_id
        self.db.add(user)

        action = AuditAction.ROLE_CHANGE if profile_changed or deactivated else AuditAction.UPDATE
        details = {k: (v.value if hasattr(v, "value") else v) for k, v in update_data.items()}
        if not is_supervisor_plus(user.profile) and "profile" in update_data:
            details["pdv_pin_cleared"] = True
        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=action,
            entity_type="user",
            entity_id=user.id,
            details=details,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_password(
        self, user_id: int, new_password: str, *, company_id: int, actor_id: int
    ) -> User:
        user = self.get_by_id(user_id, company_id)
        user.password_hash = hash_password(new_password)
        bump_token_version(user)
        user.updated_at = datetime.now(timezone.utc)
        user.updated_by = actor_id
        self.db.add(user)

        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user.id,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def regenerate_pdv_id(self, user_id: int, *, company_id: int, actor_id: int) -> User:
        user = self.get_by_id(user_id, company_id)
        if not is_pdv_eligible(user.profile):
            raise ValidationError("Only PDV-eligible profiles can have a PDV ID.")
        user.pdv_id = generate_pdv_id(self.db, company_id)
        user.updated_at = datetime.now(timezone.utc)
        user.updated_by = actor_id
        self.db.add(user)
        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user.id,
            details={"pdv_id": user.pdv_id},
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def generate_pdv_pin(
        self, user_id: int, *, company_id: int, actor_id: int
    ) -> UserPdvPinResponse:
        user = self.get_by_id(user_id, company_id)
        if not is_supervisor_plus(user.profile):
            raise ValidationError("Only Supervisor+ profiles can have a PDV PIN.")
        ensure_pdv_id(self.db, user)
        pin = generate_pdv_pin()
        if len(pin) != PDV_PIN_LENGTH or not pin.isdigit():
            raise ValidationError("Failed to generate a valid PDV PIN.")

        user.pdv_pin_hash = hash_pdv_pin(pin)
        user.updated_at = datetime.now(timezone.utc)
        user.updated_by = actor_id
        self.db.add(user)

        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user.id,
            details={"pdv_pin_regenerated": True},
        )
        self.db.commit()
        self.db.refresh(user)
        return UserPdvPinResponse(user_id=user.id, pdv_id=user.pdv_id or "", pdv_pin=pin)

    def delete(self, user_id: int, *, company_id: int, actor_id: int) -> None:
        if user_id == actor_id:
            raise ValidationError("Cannot delete your own account.")

        self.get_by_id(user_id, company_id)

        if UserRepository.count_required_refs(self.db, user_id) > 0:
            raise ConflictException("Usuário possui compras vinculadas.")

        UserRepository.detach_optional_refs(self.db, user_id)
        deleted = UserRepository.delete(self.db, user_id, company_id=company_id)
        if not deleted:
            raise ResourceNotFoundException(f"User with ID {user_id} was not found.")

        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.DELETE,
            entity_type="user",
            entity_id=user_id,
        )
        self.db.commit()

    def _validate_unique_fields(
        self, company_id: int, cpf: str, email: str | None, username: str | None
    ) -> None:
        if UserRepository.find_by_cpf(self.db, cpf, company_id=company_id):
            raise ValidationError("CPF already registered.")
        if email and UserRepository.find_by_email(self.db, email, company_id=company_id):
            raise ValidationError("Email already registered.")
        if username and UserRepository.find_by_username(self.db, username, company_id=company_id):
            raise ValidationError("Username already registered.")

    def _validate_org_defaults(
        self,
        company_id: int,
        *,
        default_branch_id: int | None,
        default_store_id: int | None,
    ) -> None:
        if default_branch_id is not None:
            branch = BranchRepository.find_by_id_for_company(self.db, default_branch_id, company_id)
            if not branch:
                raise ValidationError("Invalid default_branch_id for this company.")

        if default_store_id is not None:
            store = StoreRepository.find_by_id_for_company(self.db, default_store_id, company_id)
            if not store:
                raise ValidationError("Invalid default_store_id for this company.")
            if default_branch_id is not None and store.branch_id != default_branch_id:
                raise ValidationError("default_store_id does not belong to default_branch_id.")

    @staticmethod
    def _normalize_and_validate_cpf(cpf: str) -> str:
        normalized = normalize_cpf(cpf)
        if not is_valid_cpf(normalized):
            raise ValidationError("CPF must be a valid 11-digit document.")
        return normalized

    @staticmethod
    def _validate_login_identifiers(email: str | None, username: str | None) -> None:
        if not email and not username:
            raise ValidationError("User must have at least email or username for login.")
