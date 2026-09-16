from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from purchases.models import PurchaseItem, PurchaseOrder, SupplierProductMapping
from shared.dates import inclusive_end_of_day
from utils.enums import PurchaseStatus


class PurchaseRepository:
    @staticmethod
    def _filtered_stmt(
        company_id: int,
        *,
        supplier_id: int | None = None,
        status: PurchaseStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        store_id: int | None = None,
    ):
        stmt = select(PurchaseOrder).where(PurchaseOrder.company_id == company_id)
        if supplier_id is not None:
            stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
        if status is not None:
            stmt = stmt.where(PurchaseOrder.status == status)
        if date_from is not None:
            stmt = stmt.where(PurchaseOrder.entry_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(PurchaseOrder.entry_date <= inclusive_end_of_day(date_to))
        if store_id is not None:
            stmt = stmt.where(PurchaseOrder.store_id == store_id)
        return stmt

    @staticmethod
    def find_all(
        db: Session,
        company_id: int,
        *,
        supplier_id: int | None = None,
        status: PurchaseStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        store_id: int | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[PurchaseOrder]:
        stmt = PurchaseRepository._filtered_stmt(
            company_id,
            supplier_id=supplier_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            store_id=store_id,
        ).order_by(PurchaseOrder.entry_date.desc())
        stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(db.exec(stmt).all())

    @staticmethod
    def count_all(
        db: Session,
        company_id: int,
        *,
        supplier_id: int | None = None,
        status: PurchaseStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        store_id: int | None = None,
    ) -> int:
        filtered = PurchaseRepository._filtered_stmt(
            company_id,
            supplier_id=supplier_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            store_id=store_id,
        ).subquery()
        return int(db.exec(select(func.count()).select_from(filtered)).one() or 0)

    @staticmethod
    def find_by_id(db: Session, purchase_id: int, company_id: int) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == purchase_id, PurchaseOrder.company_id == company_id)
            .options(selectinload(PurchaseOrder.items))
        )
        return db.exec(stmt).first()

    @staticmethod
    def find_by_invoice_key(db: Session, invoice_key: str, company_id: int) -> PurchaseOrder | None:
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.invoice_key == invoice_key,
            PurchaseOrder.company_id == company_id,
        )
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, purchase: PurchaseOrder) -> PurchaseOrder:
        db.add(purchase)
        db.flush()
        return purchase

    @staticmethod
    def add_item(db: Session, item: PurchaseItem) -> PurchaseItem:
        db.add(item)
        db.flush()
        return item

    @staticmethod
    def update_status(
        db: Session, purchase_id: int, company_id: int, status: PurchaseStatus
    ) -> PurchaseOrder | None:
        purchase = PurchaseRepository.find_by_id(db, purchase_id, company_id)
        if not purchase:
            return None
        purchase.status = status
        db.add(purchase)
        db.flush()
        return purchase


class SupplierMappingRepository:
    @staticmethod
    def find_mapping(
        db: Session, supplier_id: int, supplier_product_code: str
    ) -> SupplierProductMapping | None:
        stmt = select(SupplierProductMapping).where(
            SupplierProductMapping.supplier_id == supplier_id,
            SupplierProductMapping.supplier_product_code == supplier_product_code,
        )
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, mapping: SupplierProductMapping) -> SupplierProductMapping:
        db.add(mapping)
        db.flush()
        return mapping
