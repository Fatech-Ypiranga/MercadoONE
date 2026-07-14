from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from utils.enums import CustomerType, StateRegistrationIndicator, enum_column


class CustomerBase(SQLModel):
    name: str = Field(index=True, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255, description="Nome fantasia")
    email: Optional[str] = Field(default=None, index=True, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)

    customer_type: CustomerType = Field(default=CustomerType.FISICA)

    document: str = Field(index=True, max_length=14, description="CPF ou CNPJ, somente dígitos")
    state_registration: Optional[str] = Field(
        default=None, max_length=14, description="Inscrição estadual (IE)"
    )
    ie_indicator: StateRegistrationIndicator = Field(
        default=StateRegistrationIndicator.NAO_CONTRIBUINTE
    )

    is_active: bool = Field(default=True)


class CustomerCreate(CustomerBase):
    addresses: List["CustomerAddressCreate"] = []


class CustomerUpdate(SQLModel):
    name: Optional[str] = None
    trade_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    customer_type: Optional[CustomerType] = None
    document: Optional[str] = None
    state_registration: Optional[str] = None
    ie_indicator: Optional[StateRegistrationIndicator] = None
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


class Customer(CustomerBase, table=True):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("company_id", "document", name="uq_customers_company_document"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    customer_type: CustomerType = Field(
        default=CustomerType.FISICA, sa_column=enum_column(CustomerType)
    )
    ie_indicator: StateRegistrationIndicator = Field(
        default=StateRegistrationIndicator.NAO_CONTRIBUINTE,
        sa_column=enum_column(StateRegistrationIndicator),
    )

    addresses: List["CustomerAddress"] = Relationship(back_populates="customer")


class CustomerAddressBase(SQLModel):
    description: str = Field(max_length=50, default="Principal")
    zip_code: str = Field(max_length=8)
    street: str = Field(max_length=255)
    number: str = Field(max_length=20)
    complement: Optional[str] = Field(default=None, max_length=100)
    neighborhood: str = Field(max_length=100)
    city: str = Field(max_length=100)
    state: str = Field(max_length=2)
    ibge_code: Optional[str] = Field(default=None, max_length=7)


class CustomerAddressCreate(CustomerAddressBase):
    pass


class CustomerAddressUpdate(SQLModel):
    description: Optional[str] = None
    zip_code: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    ibge_code: Optional[str] = None


class CustomerAddressResponse(CustomerAddressBase):
    id: int


class CustomerAddress(CustomerAddressBase, table=True):
    __tablename__ = "customer_addresses"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customers.id")
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    customer: Customer = Relationship(back_populates="addresses")


class CustomerDetailResponse(CustomerResponse):
    addresses: List[CustomerAddressResponse] = []
