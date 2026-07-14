from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.user import User
from services.report_service import ReportService

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
