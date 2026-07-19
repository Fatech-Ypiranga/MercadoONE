from decimal import Decimal

from sqlalchemy import case
from sqlmodel import Session, func, select

from models.product import Product
from models.sale import Sale, SaleItem
from models.stock_movement import MovementType, StockMovement


class ReportService:
    @staticmethod
    def get_top_selling_products(
        db: Session, company_id: int, *, limit: int = 5, store_id: int | None = None
    ) -> list[dict]:
        stmt = (
            select(
                Product.id,
                Product.name,
                func.coalesce(func.sum(SaleItem.quantity), 0).label("total_sold"),
            )
            .join(SaleItem, SaleItem.product_id == Product.id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Product.company_id == company_id, Sale.company_id == company_id)
            .group_by(Product.id, Product.name)
            .order_by(func.sum(SaleItem.quantity).desc())
            .limit(limit)
        )
        if store_id is not None:
            stmt = stmt.where(Sale.store_id == store_id)

        rows = db.exec(stmt).all()
        return [dict(row._mapping) for row in rows]

    @staticmethod
    def get_average_ticket(db: Session, company_id: int, *, store_id: int | None = None) -> Decimal:
        stmt = select(func.coalesce(func.avg(Sale.total_amount), 0)).where(
            Sale.company_id == company_id
        )
        if store_id is not None:
            stmt = stmt.where(Sale.store_id == store_id)
        result = db.exec(stmt).one()
        return Decimal(result or 0)

    @staticmethod
    def get_critical_stock_products(
        db: Session,
        company_id: int,
        *,
        min_threshold: int = 5,
        store_id: int | None = None,
    ) -> list[dict]:
        stmt = select(Product.id, Product.name, Product.min_stock).where(
            Product.company_id == company_id
        )
        products = db.exec(stmt).all()
        fallback = Decimal(min_threshold)

        critical_products = []
        for product_id, product_name, product_min_stock in products:
            balance_stmt = select(
                func.coalesce(
                    func.sum(
                        case(
                            (StockMovement.type == MovementType.ENTRADA, StockMovement.quantity),
                            else_=-StockMovement.quantity,
                        )
                    ),
                    0,
                )
            ).where(
                StockMovement.product_id == product_id,
                StockMovement.company_id == company_id,
            )
            if store_id is not None:
                balance_stmt = balance_stmt.where(StockMovement.store_id == store_id)

            current_stock = Decimal(db.exec(balance_stmt).one() or 0)
            effective_min = (
                Decimal(product_min_stock) if product_min_stock is not None else fallback
            )
            if current_stock < effective_min:
                critical_products.append(
                    {
                        "id": product_id,
                        "name": product_name,
                        "current_stock": current_stock,
                        "min_stock": effective_min,
                    }
                )

        return critical_products
