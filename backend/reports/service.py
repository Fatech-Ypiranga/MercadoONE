from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, case
from sqlmodel import Session, func, select

from customers.models import Customer
from products.models import Product
from sales.models import Sale, SaleItem, SaleStatus
from shared.dates import inclusive_end_of_day
from stock.models import MovementType, StockMovement
from users.models import User


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
            .where(
                Product.company_id == company_id,
                Sale.company_id == company_id,
                Sale.status != SaleStatus.CANCELADA,
            )
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
            Sale.company_id == company_id,
            Sale.status != SaleStatus.CANCELADA,
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
        # Balance computed via a single aggregated LEFT JOIN instead of one query
        # per product (was O(n) roundtrips for n products in the company).
        join_conditions = [
            StockMovement.product_id == Product.id,
            StockMovement.company_id == company_id,
        ]
        if store_id is not None:
            join_conditions.append(StockMovement.store_id == store_id)

        signed_quantity = case(
            (StockMovement.type == MovementType.ENTRADA, StockMovement.quantity),
            else_=-StockMovement.quantity,
        )
        stmt = (
            select(
                Product.id,
                Product.name,
                Product.min_stock,
                func.coalesce(func.sum(signed_quantity), 0).label("current_stock"),
            )
            .select_from(Product)
            .outerjoin(StockMovement, and_(*join_conditions))
            .where(Product.company_id == company_id)
            .group_by(Product.id, Product.name, Product.min_stock)
        )

        fallback = Decimal(min_threshold)
        critical_products = []
        for product_id, product_name, product_min_stock, current_stock in db.exec(stmt).all():
            effective_min = (
                Decimal(product_min_stock) if product_min_stock is not None else fallback
            )
            if Decimal(current_stock) < effective_min:
                critical_products.append(
                    {
                        "id": product_id,
                        "name": product_name,
                        "current_stock": Decimal(current_stock),
                        "min_stock": effective_min,
                    }
                )

        return critical_products


def _sales_filters(
    company_id: int,
    *,
    store_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> list:
    conditions = [Sale.company_id == company_id, Sale.status != SaleStatus.CANCELADA]
    if store_id is not None:
        conditions.append(Sale.store_id == store_id)
    if date_from is not None:
        conditions.append(Sale.sale_date >= date_from)
    if date_to is not None:
        conditions.append(Sale.sale_date <= inclusive_end_of_day(date_to))
    return conditions


def _grouped_sales_report(
    db: Session,
    company_id: int,
    *,
    id_col,
    name_col,
    join_model,
    store_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int,
) -> list[dict]:
    total = func.coalesce(func.sum(Sale.total_amount), 0)
    count = func.count(Sale.id)
    stmt = (
        select(
            id_col.label("id"),
            name_col.label("name"),
            count.label("sales_count"),
            total.label("total_amount"),
        )
        .join(join_model, join_model.id == id_col)
        .where(
            join_model.company_id == company_id,
            *_sales_filters(company_id, store_id=store_id, date_from=date_from, date_to=date_to),
        )
        .group_by(id_col, name_col)
        .order_by(total.desc(), id_col)
        .limit(limit)
    )
    result = []
    for row in db.exec(stmt).all():
        sales_count = int(row.sales_count)
        total_amount = Decimal(row.total_amount)
        result.append(
            {
                "id": row.id,
                "name": row.name,
                "sales_count": sales_count,
                "total_amount": total_amount,
                "average_ticket": (total_amount / sales_count).quantize(Decimal("0.01"))
                if sales_count
                else Decimal("0.00"),
            }
        )
    return result


def sales_by_operator(
    db: Session,
    company_id: int,
    *,
    store_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
) -> list[dict]:
    """Non-cancelled sales grouped by the operator who made them, biggest first."""
    return _grouped_sales_report(
        db,
        company_id,
        id_col=Sale.user_id,
        name_col=User.full_name,
        join_model=User,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


def sales_by_customer(
    db: Session,
    company_id: int,
    *,
    store_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
) -> list[dict]:
    """Non-cancelled sales grouped by identified customer (sales without one are skipped)."""
    return _grouped_sales_report(
        db,
        company_id,
        id_col=Sale.customer_id,
        name_col=Customer.name,
        join_model=Customer,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
