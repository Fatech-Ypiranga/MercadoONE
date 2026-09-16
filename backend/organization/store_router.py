from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from database.connection import get_db
from organization.models import StoreCreate, StorePdvPinResponse, StoreResponse, StoreUpdate
from organization.service import OrgService
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of
from shared.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from users.models import User

router = APIRouter(prefix="/stores", tags=["Lojas"])


@router.get("/", response_model=Page[StoreResponse], summary="Listar lojas")
def list_stores(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stores:read")),
):
    company_id = company_id_of(current_user)
    return paginate(OrgService(db).list_stores(company_id), offset=offset, limit=limit)


@router.get(
    "/{store_id}/pdv-pin",
    response_model=StorePdvPinResponse,
    summary="Obter hash do PIN PDV para sync no caixa",
)
def get_store_pdv_pin(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stores:read")),
):
    """Retorna o pin_hash Argon2id do usuário autenticado (Supervisor+) para a loja.

    O PDV importa este PHC sem re-hash e usa offline para abrir turno / overrides.
    """
    return OrgService(db).get_store_pdv_pin(store_id, actor=current_user)


@router.get("/{store_id}", response_model=StoreResponse, summary="Buscar loja por ID")
def get_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stores:read")),
):
    company_id = company_id_of(current_user)
    return OrgService(db).get_store(store_id, company_id)


@router.post(
    "/",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar loja",
)
def create_store(
    store_in: StoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stores:write")),
):
    company_id = company_id_of(current_user)
    return OrgService(db).create_store(store_in, company_id=company_id, actor_id=current_user.id)


@router.put("/{store_id}", response_model=StoreResponse, summary="Atualizar loja")
def update_store(
    store_id: int,
    store_in: StoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stores:write")),
):
    company_id = company_id_of(current_user)
    return OrgService(db).update_store(
        store_id, store_in, company_id=company_id, actor_id=current_user.id
    )


@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir loja",
)
def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stores:write")),
):
    company_id = company_id_of(current_user)
    OrgService(db).delete_store(store_id, company_id=company_id, actor_id=current_user.id)
