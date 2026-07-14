from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class SupplierBase(SQLModel):
    name: str = Field(max_length=255, description="Razão social")
    trade_name: Optional[str] = Field(default=None, max_length=255, description="Nome fantasia")
    document: str = Field(max_length=14, index=True, description="CNPJ apenas dígitos")
    state_registration: Optional[str] = Field(default=None, max_length=14)
    email: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(SQLModel):
    name: Optional[str] = None
    trade_name: Optional[str] = None
    document: Optional[str] = None
    state_registration: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


class Supplier(SupplierBase, table=True):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("company_id", "document", name="uq_suppliers_company_document"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")
