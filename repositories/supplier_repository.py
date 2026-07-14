from sqlalchemy import func
from sqlmodel import Session, select

from models.purchase import PurchaseOrder, SupplierProductMapping
from models.supplier import Supplier


class SupplierRepository:
    @staticmethod
    def find_all(
        db: Session,
        company_id: int,
        *,
        active_only: bool = False,
        name: str | None = None,
        document: str | None = None,
    ) -> list[Supplier]:
        stmt = select(Supplier).where(Supplier.company_id == company_id)
        if active_only:
            stmt = stmt.where(Supplier.is_active.is_(True))
        if name:
            stmt = stmt.where(Supplier.name.ilike(f"%{name}%"))
        if document:
            stmt = stmt.where(Supplier.document == document)
        stmt = stmt.order_by(Supplier.name)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, supplier_id: int, company_id: int) -> Supplier | None:
        stmt = select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_document(db: Session, document: str, company_id: int) -> Supplier | None:
        stmt = select(Supplier).where(
            Supplier.document == document, Supplier.company_id == company_id
        )
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, supplier: Supplier) -> Supplier:
        db.add(supplier)
        db.flush()
        return supplier

    @staticmethod
    def update(db: Session, supplier_id: int, company_id: int, **fields) -> Supplier | None:
        supplier = SupplierRepository.find_by_id(db, supplier_id, company_id)
        if not supplier:
            return None
        for field_name, field_value in fields.items():
            if field_value is not None:
                setattr(supplier, field_name, field_value)
        db.add(supplier)
        db.flush()
        return supplier

    @staticmethod
    def count_purchase_orders(db: Session, supplier_id: int) -> int:
        return int(
            db.exec(
                select(func.count())
                .select_from(PurchaseOrder)
                .where(PurchaseOrder.supplier_id == supplier_id)
            ).one()
        )

    @staticmethod
    def delete(db: Session, supplier_id: int, company_id: int) -> bool:
        supplier = SupplierRepository.find_by_id(db, supplier_id, company_id)
        if not supplier:
            return False

        for mapping in db.exec(
            select(SupplierProductMapping).where(SupplierProductMapping.supplier_id == supplier_id)
        ).all():
            db.delete(mapping)

        db.delete(supplier)
        db.flush()
        return True
