from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from models.product import ProductCreate, ProductDetailResponse, ProductResponse, ProductUpdate
from models.user import User
from services.exceptions import ResourceNotFoundException
from services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Produtos"])


@router.post(
    "/",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar um novo produto",
)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products:write")),
):
    company_id = company_id_of(current_user)
    return ProductService(db).create(product_in, company_id=company_id, actor_id=current_user.id)


@router.get(
    "/",
    response_model=Page[ProductResponse],
    summary="Listar produtos",
)
def list_products(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products:read")),
):
    company_id = company_id_of(current_user)
    return paginate(ProductService(db).get_all(company_id), offset=offset, limit=limit)


@router.get(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Buscar produto por ID",
)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products:read")),
):
    company_id = company_id_of(current_user)
    db_product = ProductService(db).get_by_id(product_id, company_id)
    if not db_product:
        raise ResourceNotFoundException(f"Product with ID {product_id} was not found.")
    return db_product


@router.put(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Atualizar produto",
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products:write")),
):
    company_id = company_id_of(current_user)
    return ProductService(db).update(
        product_id, product_in, company_id=company_id, actor_id=current_user.id
    )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir produto",
    description="Remove o produto permanentemente. Retorna 409 se houver estoque, vendas ou compras vinculadas.",
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products:write")),
):
    company_id = company_id_of(current_user)
    ProductService(db).delete(product_id, company_id=company_id, actor_id=current_user.id)
