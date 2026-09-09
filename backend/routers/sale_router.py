from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from database.connection import get_db
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from models.sale import SaleDetailResponse
from models.user import User
from services.sale_service import SaleService
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of, resolve_store_id

router = APIRouter(prefix="/sales", tags=["Vendas"])


class SaleItemInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class SaleCreateInput(BaseModel):
    customer_id: int | None = None
    payment_method: str | None = None
    store_id: int | None = None
    discount_amount: Decimal | None = Field(default=None, ge=0)
    supervisor_authorization: str | None = Field(
        default=None,
        description="Token de autorização Supervisor+ (desconto/cancelamento no PDV)",
    )
    items: list[SaleItemInput]


class SaleCancelInput(BaseModel):
    supervisor_authorization: str | None = None


@router.get(
    "/", response_model=Page[SaleDetailResponse], summary="Listar vendas com filtros opcionais"
)
def list_sales(
    customer_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    store_id: int | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales:read")),
):
    company_id = company_id_of(current_user)
    sales = SaleService(db).list_sales(
        company_id,
        customer_id=customer_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        store_id=store_id,
    )
    return paginate(sales, offset=offset, limit=limit)


@router.get("/{sale_id}", response_model=SaleDetailResponse, summary="Buscar venda por ID")
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales:read")),
):
    company_id = company_id_of(current_user)
    sale = SaleService(db).get_by_id(sale_id, company_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Sale {sale_id} was not found."
        )
    return sale


@router.post(
    "/",
    response_model=SaleDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Processar venda",
)
def process_sale(
    sale_in: SaleCreateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales:write")),
):
    company_id = company_id_of(current_user)
    store_id = resolve_store_id(db, current_user, sale_in.store_id)
    return SaleService(db).process_sale(
        customer_id=sale_in.customer_id,
        items=[item.model_dump() for item in sale_in.items],
        user_id=current_user.id,
        company_id=company_id,
        store_id=store_id,
        payment_method=sale_in.payment_method,
        discount_amount=sale_in.discount_amount,
        supervisor_authorization=sale_in.supervisor_authorization,
    )


@router.post(
    "/{sale_id}/cancel",
    response_model=SaleDetailResponse,
    summary="Cancelar venda e estornar estoque",
)
def cancel_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales:write")),
    body: SaleCancelInput = SaleCancelInput(),
):
    company_id = company_id_of(current_user)
    return SaleService(db).cancel_sale(
        sale_id,
        company_id=company_id,
        actor_id=current_user.id,
        supervisor_authorization=body.supervisor_authorization,
    )
