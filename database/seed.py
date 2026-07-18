import os
from datetime import datetime, timezone

from sqlmodel import Session

from auth.security import hash_password, verify_password
from models.company import Branch, Company, Store
from models.user import User
from repositories.company_repository import (
    BranchRepository,
    CompanyRepository,
    StoreRepository,
)
from repositories.user_repository import UserRepository
from services.pdv_credentials import ensure_pdv_id
from utils.enums import UserProfile

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@pyerp.local")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_CPF = os.getenv("ADMIN_CPF", "39053344705")
ADMIN_FULL_NAME = os.getenv("ADMIN_FULL_NAME", "Administrador")


def _require_admin_password() -> str:
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        raise RuntimeError(
            "ADMIN_PASSWORD must be set in the environment before seeding the admin user."
        )
    return password


SEED_COMPANY_DOCUMENT = os.getenv("SEED_COMPANY_DOCUMENT", "00000000000191")
SEED_COMPANY_LEGAL_NAME = os.getenv("SEED_COMPANY_LEGAL_NAME", "PyERP Demo Ltda")
SEED_COMPANY_TRADE_NAME = os.getenv("SEED_COMPANY_TRADE_NAME", "PyERP Demo")
SEED_BRANCH_CODE = "MATRIZ"
SEED_BRANCH_NAME = "Matriz"
SEED_STORE_CODE = "LOJA-CENTRO"
SEED_STORE_NAME = "Loja Centro"


def ensure_demo_organization(db: Session) -> tuple[Company, Branch, Store]:
    company = CompanyRepository.find_by_document(db, SEED_COMPANY_DOCUMENT)
    if not company:
        company = CompanyRepository.create(
            db,
            Company(
                legal_name=SEED_COMPANY_LEGAL_NAME,
                trade_name=SEED_COMPANY_TRADE_NAME,
                document=SEED_COMPANY_DOCUMENT,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        )

    branch = BranchRepository.find_by_code(db, company.id, SEED_BRANCH_CODE)
    if not branch:
        branch = BranchRepository.create(
            db,
            Branch(
                company_id=company.id,
                name=SEED_BRANCH_NAME,
                code=SEED_BRANCH_CODE,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        )

    store = StoreRepository.find_by_code(db, company.id, SEED_STORE_CODE)
    if not store:
        store = StoreRepository.create(
            db,
            Store(
                company_id=company.id,
                branch_id=branch.id,
                name=SEED_STORE_NAME,
                code=SEED_STORE_CODE,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        )

    db.flush()
    return company, branch, store


def seed_admin_user(db: Session) -> None:
    admin_password = _require_admin_password()
    company, branch, store = ensure_demo_organization(db)

    existing = UserRepository.find_by_email(db, ADMIN_EMAIL, company_id=company.id)
    if existing is None:
        existing = UserRepository.find_by_username(db, ADMIN_USERNAME, company_id=company.id)

    if existing:
        # Dev/local: keep admin password aligned with ADMIN_PASSWORD in `.env`.
        # Production never auto-overwrites an existing hash.
        if os.getenv("ENV", "development").lower() != "production":
            if not verify_password(admin_password, existing.password_hash):
                existing.password_hash = hash_password(admin_password)
                existing.updated_at = datetime.now(timezone.utc)
            ensure_pdv_id(db, existing)
            db.add(existing)
            db.commit()
        return

    admin = User(
        full_name=ADMIN_FULL_NAME,
        cpf=ADMIN_CPF,
        email=ADMIN_EMAIL,
        username=ADMIN_USERNAME,
        password_hash=hash_password(admin_password),
        profile=UserProfile.ADMIN,
        is_active=True,
        company_id=company.id,
        default_branch_id=branch.id,
        default_store_id=store.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    UserRepository.create(db, admin)
    ensure_pdv_id(db, admin)
    db.add(admin)
    db.commit()
