from datetime import datetime, timezone

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import func, text
from sqlmodel import Session, select

from services.exceptions import (
    BusinessRuleException,
    ConflictException,
    ResourceNotFoundException,
    ValidationError,
)
from shared.audit import AuditService
from suppliers.models import (
    BRAZILIAN_STATE_IBGE_CODES,
    Supplier,
    SupplierAddress,
    SupplierAddressCreate,
    SupplierCreate,
    SupplierMunicipality,
    SupplierSequence,
    SupplierUpdate,
)
from suppliers.repository import SupplierRepository
from utils.cnpj import is_valid_cnpj, normalize_cnpj
from utils.enums import AuditAction


class SupplierService:
    def __init__(self, db: Session):
        self.db = db

    def list_suppliers(
        self,
        company_id: int,
        *,
        name: str | None = None,
        document: str | None = None,
        code: str | None = None,
        active_only: bool = False,
    ) -> list[Supplier]:
        if document:
            document = normalize_cnpj(document)
        return SupplierRepository.find_all(
            self.db,
            company_id,
            active_only=active_only,
            name=name,
            document=document,
            code=code,
        )

    def get_by_id(self, supplier_id: int, company_id: int) -> Supplier:
        supplier = SupplierRepository.find_by_id(self.db, supplier_id, company_id)
        if not supplier:
            raise ResourceNotFoundException(f"Supplier with ID {supplier_id} was not found.")
        return supplier

    def get_by_document(self, document: str, company_id: int) -> Supplier:
        normalized = normalize_cnpj(document)
        supplier = SupplierRepository.find_by_document(self.db, normalized, company_id)
        if not supplier:
            raise ResourceNotFoundException(f"Supplier with document {normalized} was not found.")
        return supplier

    def create(
        self,
        supplier_in: SupplierCreate,
        *,
        company_id: int,
        actor_id: int | None = None,
        commit: bool = True,
    ) -> Supplier:
        try:
            supplier = self._create_uncommitted(
                supplier_in, company_id=company_id, actor_id=actor_id
            )
            if commit:
                self.db.commit()
                return self.get_by_id(supplier.id, company_id)
            return supplier
        except (ValidationError, ConflictException, ResourceNotFoundException):
            if commit:
                self.db.rollback()
            raise
        except Exception as exc:
            if commit:
                self.db.rollback()
            raise BusinessRuleException(f"Error saving supplier: {exc}") from exc

    def _create_uncommitted(
        self,
        supplier_in: SupplierCreate,
        *,
        company_id: int,
        actor_id: int | None = None,
    ) -> Supplier:
        document = self._normalize_document(supplier_in.document)
        if SupplierRepository.find_by_document(self.db, document, company_id):
            raise ConflictException(f"Supplier with document {document} already exists.")

        supplier = Supplier.model_validate(
            {
                **supplier_in.model_dump(exclude={"address"}),
                "document": document,
                "company_id": company_id,
                "code": self._allocate_code(company_id, supplier_in.address),
            }
        )
        if actor_id is not None:
            supplier.created_by = actor_id
            supplier.updated_by = actor_id
        SupplierRepository.create(self.db, supplier)
        self.db.add(
            SupplierAddress(
                **supplier_in.address.model_dump(),
                supplier_id=supplier.id,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )

        if actor_id is not None:
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.CREATE,
                entity_type="supplier",
                entity_id=supplier.id,
            )

        self.db.flush()
        return supplier

    def update(
        self,
        supplier_id: int,
        supplier_in: SupplierUpdate,
        *,
        company_id: int,
        actor_id: int | None = None,
    ) -> Supplier:
        supplier = self.get_by_id(supplier_id, company_id)
        update_data = supplier_in.model_dump(exclude_unset=True)
        address_input = update_data.pop("address", None)
        needs_regularization = supplier.code is None or supplier.address is None
        if needs_regularization and address_input is None:
            raise ValidationError(
                "A complete address is required to regularize this legacy supplier."
            )

        validated_address = None
        if address_input is not None:
            if needs_regularization:
                candidate = address_input
            else:
                candidate = {
                    **supplier.address.model_dump(
                        include={
                            "description",
                            "zip_code",
                            "street",
                            "number",
                            "complement",
                            "neighborhood",
                            "city",
                            "state",
                            "ibge_code",
                        }
                    ),
                    **address_input,
                }
            try:
                validated_address = SupplierAddressCreate.model_validate(candidate)
            except PydanticValidationError as exc:
                raise ValidationError(f"Invalid supplier address: {exc}") from exc

        if needs_regularization:
            supplier.code = self._allocate_code(company_id, validated_address)

        if validated_address is not None:
            if supplier.address is None:
                supplier.address = SupplierAddress(
                    **validated_address.model_dump(),
                    supplier_id=supplier.id,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            else:
                for field_name, field_value in validated_address.model_dump().items():
                    setattr(supplier.address, field_name, field_value)
                supplier.address.updated_by = actor_id
                self.db.add(supplier.address)
        if "document" in update_data and update_data["document"] is not None:
            update_data["document"] = self._normalize_document(update_data["document"])
            existing = SupplierRepository.find_by_document(
                self.db, update_data["document"], company_id
            )
            if existing and existing.id != supplier_id:
                raise ConflictException(
                    f"Supplier with document {update_data['document']} already exists."
                )

        for field_name, field_value in update_data.items():
            setattr(supplier, field_name, field_value)
        supplier.updated_at = datetime.now(timezone.utc)
        if actor_id is not None:
            supplier.updated_by = actor_id
        self.db.add(supplier)

        if actor_id is not None:
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.UPDATE,
                entity_type="supplier",
                entity_id=supplier_id,
            )

        self.db.commit()
        return self.get_by_id(supplier.id, company_id)

    def delete(self, supplier_id: int, *, company_id: int, actor_id: int | None = None) -> None:
        self.get_by_id(supplier_id, company_id)

        if SupplierRepository.count_purchase_orders(self.db, supplier_id) > 0:
            raise ConflictException("Fornecedor possui compras vinculadas.")
        if SupplierRepository.count_primary_products(self.db, supplier_id, company_id) > 0:
            raise ConflictException("Fornecedor é fornecedor principal de produtos cadastrados.")

        deleted = SupplierRepository.delete(self.db, supplier_id, company_id)
        if not deleted:
            raise ResourceNotFoundException(f"Supplier {supplier_id} was not found.")

        if actor_id is not None:
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.DELETE,
                entity_type="supplier",
                entity_id=supplier_id,
            )

        self.db.commit()

    @staticmethod
    def _normalize_document(document: str) -> str:
        normalized = normalize_cnpj(document)
        if not is_valid_cnpj(normalized):
            raise ValidationError("Supplier document must be a valid CNPJ.")
        return normalized

    def _allocate_code(self, company_id: int, address: SupplierAddressCreate) -> str:
        state = address.state
        ibge_code = address.ibge_code
        self._transaction_lock(f"supplier-municipality:{state}")

        municipality = self.db.exec(
            select(SupplierMunicipality)
            .where(
                SupplierMunicipality.state == state,
                SupplierMunicipality.ibge_code == ibge_code,
            )
            .with_for_update()
        ).first()
        if municipality is None:
            last_municipality_sequence = self.db.exec(
                select(func.max(SupplierMunicipality.sequence)).where(
                    SupplierMunicipality.state == state
                )
            ).one()
            municipality_sequence = int(last_municipality_sequence or 0) + 1
            if municipality_sequence > 999:
                raise ValidationError(f"Municipality code capacity exhausted for {state}.")
            municipality = SupplierMunicipality(
                state=state,
                ibge_code=ibge_code,
                sequence=municipality_sequence,
            )
            self.db.add(municipality)
            self.db.flush()

        self._transaction_lock(f"supplier-sequence:{company_id}:{municipality.id}")
        counter = self.db.exec(
            select(SupplierSequence)
            .where(
                SupplierSequence.company_id == company_id,
                SupplierSequence.municipality_id == municipality.id,
            )
            .with_for_update()
        ).first()
        if counter is None:
            counter = SupplierSequence(
                company_id=company_id,
                municipality_id=municipality.id,
                last_sequence=1,
            )
        else:
            counter.last_sequence += 1
        if counter.last_sequence > 999:
            raise ValidationError(
                "Supplier code capacity exhausted for this company and municipality."
            )
        self.db.add(counter)
        self.db.flush()

        return (
            f"{BRAZILIAN_STATE_IBGE_CODES[state]}"
            f"{municipality.sequence:03d}"
            f"{counter.last_sequence:03d}"
        )

    def _transaction_lock(self, key: str) -> None:
        if self.db.get_bind().dialect.name == "postgresql":
            self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                {"key": key},
            )
