from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from database.connection import get_db
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of, resolve_store_id
from stock.models import StockMovementCreate, StockMovementResponse
from stock.service import StockMovementService
from users.models import User

router = APIRouter(prefix="/stock", tags=["Estoque"])


@router.post(
    "/move",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar movimentação de estoque (Entrada/Saída)",
)
def move_stock(
    movement_in: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stock:write")),
):
    company_id = company_id_of(current_user)
    store_id = resolve_store_id(db, current_user, movement_in.store_id)
    db_movement = StockMovementService(db).create_movement(
        movement_in,
        company_id=company_id,
        store_id=store_id,
        actor_id=current_user.id,
    )

    if not db_movement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operação inválida. Verifique o ID do produto ou a quantidade.",
        )

    return db_movement


@router.get("/product/{product_id}/balance", summary="Obter o saldo atual de um produto")
def get_product_balance(
    product_id: int,
    store_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stock:read")),
):
    resolved_store_id = resolve_store_id(db, current_user, store_id)
    balance = StockMovementService(db).get_current_balance(
        product_id,
        resolved_store_id,
        company_id=company_id_of(current_user),
    )
    return {
        "product_id": product_id,
        "store_id": resolved_store_id,
        "current_balance": balance,
    }


@router.get(
    "/product/{product_id}/extract",
    response_model=List[StockMovementResponse],
    summary="Ver o extrato de movimentações de um produto",
)
def get_product_extract(
    product_id: int,
    store_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stock:read")),
):
    company_id = company_id_of(current_user)
    resolved_store_id = resolve_store_id(db, current_user, store_id)
    return StockMovementService(db).get_extract_by_product(
        product_id, company_id, store_id=resolved_store_id
    )
