from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from models.product import BrandCreate, BrandResponse, BrandUpdate
from models.user import User
from services.brand_service import BrandService

router = APIRouter(prefix="/brands", tags=["Marcas"])


@router.get("/", response_model=Page[BrandResponse], summary="Listar marcas")
def list_brands(
    q: str | None = Query(default=None, description="Filtrar por nome (case-insensitive)"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:read")),
):
    company_id = company_id_of(current_user)
    return paginate(BrandService(db).list_brands(company_id, q=q), offset=offset, limit=limit)


@router.get(
    "/by-name/{name}",
    response_model=BrandResponse,
    summary="Buscar marca por nome (case-insensitive)",
)
def get_brand_by_name(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:read")),
):
    company_id = company_id_of(current_user)
    return BrandService(db).get_by_name(name, company_id)


@router.get("/{brand_id}", response_model=BrandResponse, summary="Buscar marca por ID")
def get_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:read")),
):
    company_id = company_id_of(current_user)
    return BrandService(db).get_by_id(brand_id, company_id)


@router.post(
    "/",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar marca",
)
def create_brand(
    brand_in: BrandCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:write")),
):
    company_id = company_id_of(current_user)
    return BrandService(db).create(brand_in, company_id=company_id, actor_id=current_user.id)


@router.put("/{brand_id}", response_model=BrandResponse, summary="Atualizar marca")
def update_brand(
    brand_id: int,
    brand_in: BrandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:write")),
):
    company_id = company_id_of(current_user)
    return BrandService(db).update(
        brand_id, brand_in, company_id=company_id, actor_id=current_user.id
    )


@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir marca",
    description="Remove a marca quando não há produtos vinculados. Retorna 409 se existirem produtos na marca.",
)
def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:write")),
):
    company_id = company_id_of(current_user)
    BrandService(db).delete(brand_id, company_id=company_id, actor_id=current_user.id)
