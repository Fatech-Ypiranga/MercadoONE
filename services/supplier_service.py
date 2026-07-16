from datetime import datetime, timezone

from sqlmodel import Session

from models.supplier import Supplier, SupplierCreate, SupplierUpdate
from repositories.supplier_repository import SupplierRepository
from services.audit_service import AuditService
from services.exceptions import ConflictException, ResourceNotFoundException, ValidationError
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
        self, supplier_in: SupplierCreate, *, company_id: int, actor_id: int | None = None
    ) -> Supplier:
        # #region agent log
        import json as _json, time as _time
        from pathlib import Path as _Path
        from utils.cnpj import is_valid_cnpj as _is_valid_cnpj, normalize_cnpj as _normalize_cnpj
        _log_path = _Path(__file__).resolve().parents[1] / "debug-80ed7a.log"
        _raw = supplier_in.document
        _norm = _normalize_cnpj(_raw)
        _valid = _is_valid_cnpj(_raw)
        with _log_path.open("a", encoding="utf-8") as _f:
            _f.write(_json.dumps({"sessionId":"80ed7a","runId":"post-fix","hypothesisId":"A","location":"supplier_service.py:create","message":"supplier create entry","data":{"raw_document":_raw,"normalized":_norm,"is_valid_cnpj":_valid,"name":supplier_in.name},"timestamp":int(_time.time()*1000)}) + "\n")
        # #endregion
        try:
            document = self._normalize_document(supplier_in.document)
        except ValidationError as exc:
            # #region agent log
            with _log_path.open("a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"sessionId":"80ed7a","runId":"post-fix","hypothesisId":"A","location":"supplier_service.py:create","message":"CNPJ validation failed","data":{"error":str(exc),"normalized":_norm},"timestamp":int(_time.time()*1000)}) + "\n")
            # #endregion
            raise
        # #region agent log
        with _log_path.open("a", encoding="utf-8") as _f:
            _f.write(_json.dumps({"sessionId":"80ed7a","runId":"post-fix","hypothesisId":"A","location":"supplier_service.py:create","message":"CNPJ validation passed","data":{"normalized":document},"timestamp":int(_time.time()*1000)}) + "\n")
        # #endregion
        if SupplierRepository.find_by_document(self.db, document, company_id):
            raise ConflictException(f"Supplier with document {document} already exists.")

        supplier = Supplier.model_validate(
            {**supplier_in.model_dump(), "document": document, "company_id": company_id}
        )
        if actor_id is not None:
            supplier.created_by = actor_id
            supplier.updated_by = actor_id
        SupplierRepository.create(self.db, supplier)

        if actor_id is not None:
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.CREATE,
                entity_type="supplier",
                entity_id=supplier.id,
            )

        self.db.commit()
        self.db.refresh(supplier)
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
        self.db.refresh(supplier)
        return supplier

    def delete(self, supplier_id: int, *, company_id: int, actor_id: int | None = None) -> None:
        self.get_by_id(supplier_id, company_id)

        if SupplierRepository.count_purchase_orders(self.db, supplier_id) > 0:
            raise ConflictException("Fornecedor possui compras vinculadas.")

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
