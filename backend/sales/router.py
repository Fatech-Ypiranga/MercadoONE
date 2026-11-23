from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session

from database.connection import get_db
from sales.discount_policy import MAX_DISCOUNT_PERCENT, max_discount_percent
from sales.models import SaleDetailResponse
from sales.service import SaleService
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of, resolve_store_id
from shared.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page
from users.models import User

router = APIRouter(prefix="/sales", tags=["Vendas"])


class SaleItemInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class SalePaymentInput(BaseModel):
    method: str = Field(min_length=1, max_length=20)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SaleCreateInput(BaseModel):
    customer_id: int | None = None
    payment_method: str | None = Field(
        default=None,
        max_length=20,
        description="Legado: forma única de pagamento. Use `payments` para dividir a venda.",
    )
    payments: list[SalePaymentInput] | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="Pagamentos da venda; a soma deve ser igual ao total da venda",
    )
    store_id: int | None = None
    client_sale_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Chave de idempotência do cliente (PDV); repetir devolve a venda original",
    )
    discount_amount: Decimal | None = Field(default=None, ge=0)
    supervisor_authorization: str | None = Field(
        default=None,
        description="Token de autorização Supervisor+ (desconto/cancelamento no PDV)",
    )
    items: list[SaleItemInput]

    @model_validator(mode="after")
    def _single_payment_style(self):
        if self.payments is not None and self.payment_method is not None:
            raise ValueError("Send either payment_method or payments, not both.")
        return self


class DiscountPolicyResponse(BaseModel):
    profile: str
    max_discount_percent: Decimal = Field(
        description="Desconto máximo (% do total bruto) que o usuário atual concede sozinho"
    )
    requires_authorization_above_percent: Decimal = Field(
        description="Acima deste percentual é necessária autorização Supervisor+"
    )
    by_profile: dict[str, Decimal]


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
    sales, total = SaleService(db).list_sales(
        company_id,
        customer_id=customer_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        store_id=store_id,
        offset=offset,
        limit=limit,
    )
    return Page(items=sales, total=total, offset=offset, limit=limit)


@router.get(
    "/discount-policy",
    response_model=DiscountPolicyResponse,
    summary="Política de desconto por perfil",
)
def get_discount_policy(
    current_user: User = Depends(require_permission("sales:read")),
):
    own = max_discount_percent(current_user.profile)
    return DiscountPolicyResponse(
        profile=current_user.profile.value,
        max_discount_percent=own,
        requires_authorization_above_percent=own,
        by_profile={profile.value: pct for profile, pct in MAX_DISCOUNT_PERCENT.items()},
    )


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
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales:write")),
):
    company_id = company_id_of(current_user)
    store_id = resolve_store_id(db, current_user, sale_in.store_id)
    sale, created = SaleService(db).process_sale_idempotent(
        customer_id=sale_in.customer_id,
        items=[item.model_dump() for item in sale_in.items],
        user_id=current_user.id,
        company_id=company_id,
        store_id=store_id,
        payment_method=sale_in.payment_method,
        discount_amount=sale_in.discount_amount,
        supervisor_authorization=sale_in.supervisor_authorization,
        client_sale_id=sale_in.client_sale_id,
        payments=[p.model_dump() for p in sale_in.payments] if sale_in.payments else None,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return sale


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
