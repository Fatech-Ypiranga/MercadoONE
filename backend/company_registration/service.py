import re
import secrets
from datetime import datetime, timezone

from sqlmodel import Session

from company_registration.models import (
    CompanyRegistrationApprove,
    CompanyRegistrationApproveResponse,
    CompanyRegistrationCreate,
    CompanyRegistrationReject,
    CompanyRegistrationRequest,
    CompanyRegistrationResponse,
    CompanyRegistrationStatus,
)
from company_registration.repository import CompanyRegistrationRepository
from organization.models import Branch, Company, Store
from organization.repository import (
    BranchRepository,
    CompanyRepository,
    StoreRepository,
)
from shared.exceptions import ConflictException, ResourceNotFoundException, ValidationError
from shared.identity.pdv_credentials import ensure_pdv_id
from shared.identity.security import hash_password
from users.models import User
from users.repository import UserRepository
from utils.cnpj import require_valid_cnpj
from utils.cpf import require_valid_cpf
from utils.enums import UserProfile

MAX_SELF_SERVICE_STORES = 15
SALES_CONTACT_MESSAGE = (
    "Empresas com mais de 15 lojas devem entrar em contato com o time de vendas."
)


def to_registration_response(row: CompanyRegistrationRequest) -> CompanyRegistrationResponse:
    return CompanyRegistrationResponse(
        id=row.id,
        legal_name=row.legal_name,
        trade_name=row.trade_name,
        document=row.document,
        state_registration=row.state_registration,
        admin_name=row.admin_name,
        admin_email=row.admin_email,
        admin_cpf=row.admin_cpf,
        admin_phone=row.admin_phone,
        declared_store_count=row.declared_store_count,
        status=CompanyRegistrationStatus(row.status),
        notes=row.notes,
        reviewed_at=row.reviewed_at,
        reviewed_by=row.reviewed_by,
        created_company_id=row.created_company_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class CompanyRegistrationService:
    def __init__(self, db: Session):
        self.db = db

    def create_request(self, payload: CompanyRegistrationCreate) -> CompanyRegistrationRequest:
        document = require_valid_cnpj(payload.document, entity="Company document")
        admin_cpf = require_valid_cpf(payload.admin_cpf, entity="Admin CPF")

        admin_email = payload.admin_email.strip().lower()
        if "@" not in admin_email:
            raise ValidationError("Invalid admin email.")

        if payload.declared_store_count > MAX_SELF_SERVICE_STORES:
            raise ValidationError(SALES_CONTACT_MESSAGE)

        if CompanyRepository.find_by_document(self.db, document):
            raise ConflictException("A company with this CNPJ already exists.")

        if CompanyRegistrationRepository.find_pending_by_document(self.db, document):
            raise ConflictException("A pending registration already exists for this CNPJ.")

        row = CompanyRegistrationRequest(
            legal_name=payload.legal_name.strip(),
            trade_name=payload.trade_name.strip() if payload.trade_name else None,
            document=document,
            state_registration=payload.state_registration,
            admin_name=payload.admin_name.strip(),
            admin_email=admin_email,
            admin_cpf=admin_cpf,
            admin_phone=payload.admin_phone,
            declared_store_count=payload.declared_store_count,
            status=CompanyRegistrationStatus.PENDING.value,
        )
        CompanyRegistrationRepository.create(self.db, row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_requests(self, *, status: str | None = None) -> list[CompanyRegistrationRequest]:
        if status is not None:
            try:
                CompanyRegistrationStatus(status)
            except ValueError as exc:
                raise ValidationError("Invalid status filter.") from exc
        return CompanyRegistrationRepository.list_all(self.db, status=status)

    def get_request(self, request_id: int) -> CompanyRegistrationRequest:
        row = CompanyRegistrationRepository.find_by_id(self.db, request_id)
        if not row:
            raise ResourceNotFoundException(
                f"Registration request with ID {request_id} was not found."
            )
        return row

    def reject(
        self,
        request_id: int,
        payload: CompanyRegistrationReject,
        *,
        reviewed_by: str,
    ) -> CompanyRegistrationRequest:
        row = self.get_request(request_id)
        if row.status != CompanyRegistrationStatus.PENDING.value:
            raise ValidationError("Only pending registrations can be rejected.")

        now = datetime.now(timezone.utc)
        row.status = CompanyRegistrationStatus.REJECTED.value
        row.notes = payload.notes
        row.reviewed_at = now
        row.reviewed_by = reviewed_by
        row.updated_at = now
        CompanyRegistrationRepository.update(self.db, row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def approve(
        self,
        request_id: int,
        payload: CompanyRegistrationApprove,
        *,
        reviewed_by: str,
    ) -> CompanyRegistrationApproveResponse:
        row = self.get_request(request_id)
        if row.status != CompanyRegistrationStatus.PENDING.value:
            raise ValidationError("Only pending registrations can be approved.")

        if CompanyRepository.find_by_document(self.db, row.document):
            raise ConflictException("A company with this CNPJ already exists.")

        now = datetime.now(timezone.utc)
        company = CompanyRepository.create(
            self.db,
            Company(
                legal_name=row.legal_name,
                trade_name=row.trade_name,
                document=row.document,
                state_registration=row.state_registration,
                is_active=True,
                has_branches=payload.has_branches,
                created_at=now,
                updated_at=now,
            ),
        )

        branch = BranchRepository.create(
            self.db,
            Branch(
                company_id=company.id,
                name="Matriz",
                code="MATRIZ",
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        )

        store_name = (payload.initial_store_name or "Loja Centro").strip()
        store_code = (payload.initial_store_code or "LOJA-01").strip().upper()
        store = StoreRepository.create(
            self.db,
            Store(
                company_id=company.id,
                branch_id=branch.id,
                name=store_name,
                code=store_code,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        )

        admin_username = self._username_from_email(row.admin_email)
        temporary_password = secrets.token_urlsafe(12)
        admin = User(
            full_name=row.admin_name,
            cpf=row.admin_cpf,
            email=row.admin_email,
            username=admin_username,
            password_hash=hash_password(temporary_password),
            profile=UserProfile.ADMIN,
            is_active=True,
            company_id=company.id,
            default_branch_id=branch.id,
            default_store_id=store.id,
            created_at=now,
            updated_at=now,
        )
        UserRepository.create(self.db, admin)
        ensure_pdv_id(self.db, admin)
        self.db.add(admin)

        row.status = CompanyRegistrationStatus.APPROVED.value
        row.notes = payload.notes
        row.reviewed_at = now
        row.reviewed_by = reviewed_by
        row.created_company_id = company.id
        row.updated_at = now
        CompanyRegistrationRepository.update(self.db, row)

        self.db.commit()
        self.db.refresh(row)

        return CompanyRegistrationApproveResponse(
            registration=to_registration_response(row),
            company_id=company.id,
            admin_username=admin_username,
            admin_email=row.admin_email,
            temporary_password=temporary_password,
        )

    @staticmethod
    def _username_from_email(email: str) -> str:
        local = email.split("@", 1)[0]
        cleaned = re.sub(r"[^a-zA-Z0-9._-]", "", local).lower()
        if not cleaned:
            cleaned = "admin"
        return cleaned[:50]
