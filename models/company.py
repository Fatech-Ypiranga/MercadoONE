from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class CompanyBase(SQLModel):
    legal_name: str = Field(max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    document: str = Field(max_length=14, index=True, description="CNPJ, somente dígitos")
    state_registration: Optional[str] = Field(default=None, max_length=14)
    is_active: bool = Field(default=True)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(SQLModel):
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    document: Optional[str] = None
    state_registration: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


class Company(CompanyBase, table=True):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("document", name="uq_companies_document"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")


class BranchBase(SQLModel):
    name: str = Field(max_length=150)
    code: str = Field(max_length=20, description="Código único por empresa")
    is_active: bool = Field(default=True)


class BranchCreate(BranchBase):
    pass


class BranchUpdate(SQLModel):
    name: Optional[str] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None


class BranchResponse(BranchBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime


class Branch(BranchBase, table=True):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_branches_company_code"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StoreBase(SQLModel):
    name: str = Field(max_length=150)
    code: str = Field(max_length=20, description="Código único por empresa")
    is_active: bool = Field(default=True)


class StoreCreate(StoreBase):
    branch_id: int


class StoreUpdate(SQLModel):
    name: Optional[str] = None
    code: Optional[str] = None
    branch_id: Optional[int] = None
    is_active: Optional[bool] = None


class StoreResponse(StoreBase):
    id: int
    company_id: int
    branch_id: int
    created_at: datetime
    updated_at: datetime


class Store(StoreBase, table=True):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_stores_company_code"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    branch_id: int = Field(foreign_key="branches.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
