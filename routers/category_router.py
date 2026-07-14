from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.category import CategoryCreate, CategoryDetailResponse, CategoryResponse, CategoryUpdate
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from models.user import User
from services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categorias"])


@router.get("/", response_model=Page[CategoryResponse], summary="Listar categorias")
def list_categories(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("categories:read")),
):
    company_id = company_id_of(current_user)
    return paginate(CategoryService(db).list_categories(company_id), offset=offset, limit=limit)


@router.get(
    "/{category_id}", response_model=CategoryDetailResponse, summary="Buscar categoria por ID"
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("categories:read")),
):
    company_id = company_id_of(current_user)
    return CategoryService(db).get_by_id(category_id, company_id)


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar categoria",
)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("categories:write")),
):
    company_id = company_id_of(current_user)
    return CategoryService(db).create(category_in, company_id=company_id, actor_id=current_user.id)


@router.put("/{category_id}", response_model=CategoryResponse, summary="Atualizar categoria")
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("categories:write")),
):
    company_id = company_id_of(current_user)
    return CategoryService(db).update(
        category_id, category_in, company_id=company_id, actor_id=current_user.id
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir categoria",
    description="Remove a categoria quando não há produtos vinculados. Retorna 409 se existirem produtos na categoria.",
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("categories:write")),
):
    company_id = company_id_of(current_user)
    CategoryService(db).delete(category_id, company_id=company_id, actor_id=current_user.id)
