from datetime import datetime

from sqlmodel import Session, select

from models.sale import Sale, SaleItem


class SaleRepository:
    @staticmethod
    def find_all(db: Session, company_id: int, *, store_id: int | None = None) -> list[Sale]:
        stmt = select(Sale).where(Sale.company_id == company_id).order_by(Sale.sale_date.desc())
        if store_id is not None:
            stmt = stmt.where(Sale.store_id == store_id)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, sale_id: int, company_id: int) -> Sale | None:
        stmt = select(Sale).where(Sale.id == sale_id, Sale.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def create(
        db: Session,
        *,
        company_id: int,
        store_id: int,
        customer_id: int | None = None,
        user_id: int | None = None,
        total_amount=0.0,
        payment_method: str | None = None,
        status: str = "Em_Andamento",
        created_by: int | None = None,
    ) -> Sale:
        sale = Sale(
            company_id=company_id,
            store_id=store_id,
            customer_id=customer_id,
            user_id=user_id,
            total_amount=total_amount,
            payment_method=payment_method,
            status=status,
            created_by=created_by,
            updated_by=created_by,
        )
        db.add(sale)
        db.flush()
        return sale

    @staticmethod
    def add_item(db: Session, sale_id: int, product_id: int, quantity: int, unit_price) -> SaleItem:
        sale_item = SaleItem(
            sale_id=sale_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )
        db.add(sale_item)
        db.flush()
        return sale_item

    @staticmethod
    def find_items_by_sale(db: Session, sale_id: int) -> list[SaleItem]:
        stmt = select(SaleItem).where(SaleItem.sale_id == sale_id)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_filtered(
        db: Session,
        company_id: int,
        *,
        customer_id: int | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        store_id: int | None = None,
    ) -> list[Sale]:
        stmt = select(Sale).where(Sale.company_id == company_id).order_by(Sale.sale_date.desc())

        if customer_id is not None:
            stmt = stmt.where(Sale.customer_id == customer_id)
        if status is not None:
            stmt = stmt.where(Sale.status == status)
        if date_from is not None:
            stmt = stmt.where(Sale.sale_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Sale.sale_date <= date_to)
        if store_id is not None:
            stmt = stmt.where(Sale.store_id == store_id)

        return list(db.exec(stmt).all())

    @staticmethod
    def update_status(
        db: Session,
        sale_id: int,
        company_id: int,
        status: str,
        *,
        updated_by: int | None = None,
    ) -> Sale | None:
        sale = SaleRepository.find_by_id(db, sale_id, company_id)
        if not sale:
            return None

        sale.status = status
        if updated_by is not None:
            sale.updated_by = updated_by
        db.add(sale)
        db.flush()
        return sale
