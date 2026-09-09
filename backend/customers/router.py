from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from customers.models import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerAddressUpdate,
    CustomerCreate,
    CustomerDetailResponse,
    CustomerResponse,
    CustomerUpdate,
)
from customers.service import CustomerService
from database.connection import get_db
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of
from shared.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from users.models import User

router = APIRouter(prefix="/customers", tags=["Clientes"])


@router.get("/", response_model=Page[CustomerResponse], summary="Listar clientes")
def list_customers(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers:read")),
):
    company_id = company_id_of(current_user)
    return paginate(CustomerService(db).list_customers(company_id), offset=offset, limit=limit)


@router.get(
    "/{customer_id}", response_model=CustomerDetailResponse, summary="Buscar cliente por ID"
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers:read")),
):
    company_id = company_id_of(current_user)
    return CustomerService(db).get_by_id(customer_id, company_id)


@router.post(
    "/",
    response_model=CustomerDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar cliente",
)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers:write")),
):
    company_id = company_id_of(current_user)
    return CustomerService(db).create(customer_in, company_id=company_id, actor_id=current_user.id)


@router.put("/{customer_id}", response_model=CustomerResponse, summary="Atualizar cliente")
def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers:write")),
):
    company_id = company_id_of(current_user)
    return CustomerService(db).update(
        customer_id, customer_in, company_id=company_id, actor_id=current_user.id
    )


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir cliente")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers:write")),
):
    company_id = company_id_of(current_user)
    CustomerService(db).delete(customer_id, company_id=company_id, actor_id=current_user.id)


@router.post(
    "/{customer_id}/addresses",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar endereço ao cliente",
)
def create_address(
    customer_id: int,
    address_in: CustomerAddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers:write")),
):
    company_id = company_id_of(current_user)
    return CustomerService(db).create_address(
        customer_id, address_in, company_id=company_id, actor_id=current_user.id
    )


@router.put(
    "/{customer_id}/addresses/{address_id}",
    response_model=CustomerAddressResponse,
    summary="Atualizar endereço do cliente",
)
def update_address(
    customer_id: int,
    address_id: int,
    address_in: CustomerAddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers:write")),
):
    company_id = company_id_of(current_user)
    return CustomerService(db).update_address(
        customer_id, address_id, address_in, company_id=company_id, actor_id=current_user.id
    )


@router.delete(
    "/{customer_id}/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir endereço do cliente",
)
def delete_address(
    customer_id: int,
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers:write")),
):
    company_id = company_id_of(current_user)
    CustomerService(db).delete_address(
        customer_id, address_id, company_id=company_id, actor_id=current_user.id
    )
