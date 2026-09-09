from datetime import datetime, timezone

from sqlmodel import Session

from models.user import User
from organization.models import (
    Branch,
    BranchCreate,
    BranchUpdate,
    Company,
    CompanyUpdate,
    Store,
    StoreCreate,
    StorePdvPinResponse,
    StoreUpdate,
)
from organization.repository import BranchRepository, CompanyRepository, StoreRepository
from services.exceptions import ResourceNotFoundException, ValidationError
from services.pdv_credentials import is_supervisor_plus
from utils.cnpj import is_valid_cnpj, normalize_cnpj


class OrgService:
    def __init__(self, db: Session):
        self.db = db

    def get_company(self, company_id: int) -> Company:
        company = CompanyRepository.find_by_id(self.db, company_id)
        if not company:
            raise ResourceNotFoundException(f"Company with ID {company_id} was not found.")
        return company

    def update_company(
        self,
        company_id: int,
        company_in: CompanyUpdate,
        *,
        actor_id: int,
    ) -> Company:
        company = self.get_company(company_id)
        update_data = company_in.model_dump(exclude_unset=True)

        if "document" in update_data:
            document = normalize_cnpj(update_data["document"])
            if not is_valid_cnpj(document):
                raise ValidationError("Invalid CNPJ.")
            existing = CompanyRepository.find_by_document(self.db, document)
            if existing and existing.id != company_id:
                raise ValidationError("A company with this CNPJ already exists.")
            update_data["document"] = document

        for field_name, field_value in update_data.items():
            setattr(company, field_name, field_value)
        company.updated_at = datetime.now(timezone.utc)
        company.updated_by = actor_id
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def list_branches(self, company_id: int) -> list[Branch]:
        return BranchRepository.find_all_for_company(self.db, company_id)

    def get_branch(self, branch_id: int, company_id: int) -> Branch:
        branch = BranchRepository.find_by_id_for_company(self.db, branch_id, company_id)
        if not branch:
            raise ResourceNotFoundException(f"Branch with ID {branch_id} was not found.")
        return branch

    def create_branch(self, branch_in: BranchCreate, *, company_id: int) -> Branch:
        existing = BranchRepository.find_by_code(self.db, company_id, branch_in.code)
        if existing:
            raise ValidationError(f"Branch code '{branch_in.code}' already exists.")

        branch = Branch.model_validate({**branch_in.model_dump(), "company_id": company_id})
        BranchRepository.create(self.db, branch)
        self.db.commit()
        self.db.refresh(branch)
        return branch

    def update_branch(self, branch_id: int, branch_in: BranchUpdate, *, company_id: int) -> Branch:
        branch = self.get_branch(branch_id, company_id)
        update_data = branch_in.model_dump(exclude_unset=True)

        if "code" in update_data and update_data["code"] != branch.code:
            existing = BranchRepository.find_by_code(self.db, company_id, update_data["code"])
            if existing and existing.id != branch_id:
                raise ValidationError(f"Branch code '{update_data['code']}' already exists.")

        for field_name, field_value in update_data.items():
            setattr(branch, field_name, field_value)
        branch.updated_at = datetime.now(timezone.utc)
        BranchRepository.update(self.db, branch)
        self.db.commit()
        self.db.refresh(branch)
        return branch

    def delete_branch(self, branch_id: int, *, company_id: int) -> None:
        branch = self.get_branch(branch_id, company_id)
        BranchRepository.delete(self.db, branch)
        self.db.commit()

    def list_stores(self, company_id: int) -> list[Store]:
        return StoreRepository.find_all_for_company(self.db, company_id)

    def get_store(self, store_id: int, company_id: int) -> Store:
        store = StoreRepository.find_by_id_for_company(self.db, store_id, company_id)
        if not store:
            raise ResourceNotFoundException(f"Store with ID {store_id} was not found.")
        return store

    def get_store_pdv_pin(self, store_id: int, *, actor: User) -> StorePdvPinResponse:
        """PIN hash do usuário autenticado para importação offline no PDV da loja."""
        self.get_store(store_id, actor.company_id)
        if not is_supervisor_plus(actor.profile):
            raise ValidationError("Only Supervisor+ profiles can sync a PDV PIN.")
        if not actor.pdv_pin_hash:
            raise ValidationError(
                "No PDV PIN configured for this user. Generate one via POST /users/{id}/pdv-pin."
            )
        if not actor.pdv_pin_hash.startswith("$argon2id$"):
            raise ValidationError(
                "Stored PDV PIN hash is not Argon2id. Regenerate via POST /users/{id}/pdv-pin."
            )
        return StorePdvPinResponse(
            pin_hash=actor.pdv_pin_hash,
            store_id=store_id,
            user_id=actor.id,
        )

    def create_store(self, store_in: StoreCreate, *, company_id: int) -> Store:
        branch = BranchRepository.find_by_id_for_company(self.db, store_in.branch_id, company_id)
        if not branch:
            raise ValidationError("branch_id does not belong to this company.")

        existing = StoreRepository.find_by_code(self.db, company_id, store_in.code)
        if existing:
            raise ValidationError(f"Store code '{store_in.code}' already exists.")

        store = Store.model_validate({**store_in.model_dump(), "company_id": company_id})
        StoreRepository.create(self.db, store)
        self.db.commit()
        self.db.refresh(store)
        return store

    def update_store(self, store_id: int, store_in: StoreUpdate, *, company_id: int) -> Store:
        store = self.get_store(store_id, company_id)
        update_data = store_in.model_dump(exclude_unset=True)

        if "branch_id" in update_data:
            branch = BranchRepository.find_by_id_for_company(
                self.db, update_data["branch_id"], company_id
            )
            if not branch:
                raise ValidationError("branch_id does not belong to this company.")

        if "code" in update_data and update_data["code"] != store.code:
            existing = StoreRepository.find_by_code(self.db, company_id, update_data["code"])
            if existing and existing.id != store_id:
                raise ValidationError(f"Store code '{update_data['code']}' already exists.")

        for field_name, field_value in update_data.items():
            setattr(store, field_name, field_value)
        store.updated_at = datetime.now(timezone.utc)
        StoreRepository.update(self.db, store)
        self.db.commit()
        self.db.refresh(store)
        return store

    def delete_store(self, store_id: int, *, company_id: int) -> None:
        store = self.get_store(store_id, company_id)
        StoreRepository.delete(self.db, store)
        self.db.commit()
