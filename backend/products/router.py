from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from database.connection import get_db
from products.models import ProductCreate, ProductDetailResponse, ProductResponse, ProductUpdate
from products.service import ProductService
from shared.exceptions import ResourceNotFoundException
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of
from shared.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from users.models import User

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
    q: Annotated[
        str | None,
        Query(description="Busca por nome, SKU, barcode ou código de material (ilike)"),
    ] = None,
    sku: Annotated[str | None, Query(description="Filtro exato por SKU")] = None,
    barcode: Annotated[str | None, Query(description="Filtro exato por código de barras")] = None,
    material_code: Annotated[
        str | None,
        Query(description="Filtro exato por código interno de material"),
    ] = None,
    category_id: Annotated[int | None, Query(description="Filtro por categoria")] = None,
    primary_supplier_id: Annotated[
        int | None,
        Query(description="Filtro por fornecedor principal"),
    ] = None,
    is_active: Annotated[bool | None, Query(description="Filtrar por status ativo")] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products:read")),
):
    company_id = company_id_of(current_user)
    products = ProductService(db).list_products(
        company_id,
        q=q,
        sku=sku,
        barcode=barcode,
        material_code=material_code,
        category_id=category_id,
        primary_supplier_id=primary_supplier_id,
        is_active=is_active,
    )
    return paginate(products, offset=offset, limit=limit)


@router.get(
    "/by-sku/{sku}",
    response_model=ProductDetailResponse,
    summary="Buscar produto por SKU",
)
def get_product_by_sku(
    sku: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products:read")),
):
    company_id = company_id_of(current_user)
    return ProductService(db).get_by_sku(sku, company_id)


@router.get(
    "/by-barcode/{barcode}",
    response_model=ProductDetailResponse,
    summary="Buscar produto por código de barras",
)
def get_product_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("products:read")),
):
    company_id = company_id_of(current_user)
    return ProductService(db).get_by_barcode(barcode, company_id)


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
