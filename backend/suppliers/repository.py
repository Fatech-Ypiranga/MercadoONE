from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from products.models import Product
from purchases.models import PurchaseOrder, SupplierProductMapping
from suppliers.models import Supplier


class SupplierRepository:
    @staticmethod
    def find_by_ids(db: Session, ids: list[int], company_id: int) -> dict[int, Supplier]:
        """Batch lookup keyed by id, for callers that would otherwise fetch one-by-one."""
        if not ids:
            return {}
        stmt = select(Supplier).where(Supplier.id.in_(set(ids)), Supplier.company_id == company_id)
        return {supplier.id: supplier for supplier in db.exec(stmt).all()}

    @staticmethod
    def find_all(
        db: Session,
        company_id: int,
        *,
        active_only: bool = False,
        name: str | None = None,
        document: str | None = None,
        code: str | None = None,
    ) -> list[Supplier]:
        stmt = (
            select(Supplier)
            .options(selectinload(Supplier.address))
            .where(Supplier.company_id == company_id)
        )
        if active_only:
            stmt = stmt.where(Supplier.is_active.is_(True))
        if name:
            stmt = stmt.where(Supplier.name.ilike(f"%{name}%"))
        if document:
            stmt = stmt.where(Supplier.document == document)
        if code:
            stmt = stmt.where(Supplier.code == code)
        stmt = stmt.order_by(Supplier.name)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, supplier_id: int, company_id: int) -> Supplier | None:
        stmt = (
            select(Supplier)
            .options(selectinload(Supplier.address))
            .where(Supplier.id == supplier_id, Supplier.company_id == company_id)
        )
        return db.exec(stmt).first()

    @staticmethod
    def find_by_document(db: Session, document: str, company_id: int) -> Supplier | None:
        stmt = (
            select(Supplier)
            .options(selectinload(Supplier.address))
            .where(Supplier.document == document, Supplier.company_id == company_id)
        )
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, supplier: Supplier) -> Supplier:
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
    def count_primary_products(db: Session, supplier_id: int, company_id: int) -> int:
        return int(
            db.exec(
                select(func.count())
                .select_from(Product)
                .where(
                    Product.primary_supplier_id == supplier_id,
                    Product.company_id == company_id,
                )
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
