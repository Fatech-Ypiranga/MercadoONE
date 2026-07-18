from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from models.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from models.user import User
from services.supplier_service import SupplierService

router = APIRouter(prefix="/suppliers", tags=["Fornecedores"])


@router.get("/", response_model=Page[SupplierResponse], summary="Listar fornecedores")
def list_suppliers(
    name: Annotated[str | None, Query()] = None,
    document: Annotated[str | None, Query()] = None,
    code: Annotated[str | None, Query(min_length=8, max_length=8)] = None,
    active_only: Annotated[bool, Query()] = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:read")),
):
    company_id = company_id_of(current_user)
    return paginate(
        SupplierService(db).list_suppliers(
            company_id,
            name=name,
            document=document,
            code=code,
            active_only=active_only,
        ),
        offset=offset,
        limit=limit,
    )


@router.get(
    "/by-document/{document:path}",
    response_model=SupplierResponse,
    summary="Buscar fornecedor por CNPJ",
)
def get_supplier_by_document(
    document: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:read")),
):
    company_id = company_id_of(current_user)
    return SupplierService(db).get_by_document(document, company_id)


@router.get("/{supplier_id}", response_model=SupplierResponse, summary="Buscar fornecedor por ID")
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:read")),
):
    company_id = company_id_of(current_user)
    return SupplierService(db).get_by_id(supplier_id, company_id)


@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar fornecedor",
)
def create_supplier(
    supplier_in: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:write")),
):
    company_id = company_id_of(current_user)
    return SupplierService(db).create(supplier_in, company_id=company_id, actor_id=current_user.id)


@router.put("/{supplier_id}", response_model=SupplierResponse, summary="Atualizar fornecedor")
def update_supplier(
    supplier_id: int,
    supplier_in: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:write")),
):
    company_id = company_id_of(current_user)
    return SupplierService(db).update(
        supplier_id, supplier_in, company_id=company_id, actor_id=current_user.id
    )


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir fornecedor",
    description="Remove o fornecedor permanentemente. Retorna 409 se houver compras vinculadas.",
)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:write")),
):
    company_id = company_id_of(current_user)
    SupplierService(db).delete(supplier_id, company_id=company_id, actor_id=current_user.id)
