from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from database.connection import get_db
from reports.service import ReportService, sales_by_customer, sales_by_operator
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of
from users.models import User

router = APIRouter(prefix="/reports", tags=["Relatórios"])


@router.get("/top-products", summary="Produtos mais vendidos")
def top_products(
    limit: int = Query(default=5, ge=1, le=100),
    store_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:read")),
):
    company_id = company_id_of(current_user)
    return ReportService.get_top_selling_products(db, company_id, limit=limit, store_id=store_id)


@router.get("/average-ticket", summary="Ticket médio de vendas")
def average_ticket(
    store_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:read")),
):
    company_id = company_id_of(current_user)
    return {"average_ticket": ReportService.get_average_ticket(db, company_id, store_id=store_id)}


@router.get("/critical-stock", summary="Produtos com estoque crítico")
def critical_stock(
    min_threshold: int = Query(default=5, ge=0),
    store_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:read")),
):
    company_id = company_id_of(current_user)
    return ReportService.get_critical_stock_products(
        db, company_id, min_threshold=min_threshold, store_id=store_id
    )


class SalesGroupRow(BaseModel):
    id: int
    name: str
    sales_count: int
    total_amount: Decimal
    average_ticket: Decimal


@router.get(
    "/sales-by-operator",
    response_model=list[SalesGroupRow],
    summary="Vendas por operador (exclui canceladas)",
)
def report_sales_by_operator(
    store_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:read")),
):
    return sales_by_operator(
        db,
        company_id_of(current_user),
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get(
    "/sales-by-customer",
    response_model=list[SalesGroupRow],
    summary="Vendas por cliente identificado (exclui canceladas)",
)
def report_sales_by_customer(
    store_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:read")),
):
    return sales_by_customer(
        db,
        company_id_of(current_user),
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
