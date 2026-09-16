from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class CompanyRegistrationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CompanyRegistrationCreate(SQLModel):
    legal_name: str = Field(max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    document: str = Field(max_length=18, description="CNPJ")
    state_registration: Optional[str] = Field(default=None, max_length=14)
    admin_name: str = Field(max_length=150)
    admin_email: str = Field(max_length=255)
    admin_cpf: str = Field(max_length=14, description="CPF do admin inicial")
    admin_phone: Optional[str] = Field(default=None, max_length=20)
    declared_store_count: int = Field(ge=1, le=100)


class CompanyRegistrationReject(SQLModel):
    notes: Optional[str] = Field(default=None, max_length=1000)


class CompanyRegistrationApprove(SQLModel):
    has_branches: bool = False
    notes: Optional[str] = Field(default=None, max_length=1000)
    initial_store_name: Optional[str] = Field(default=None, max_length=150)
    initial_store_code: Optional[str] = Field(default=None, max_length=20)


class CompanyRegistrationResponse(SQLModel):
    id: int
    legal_name: str
    trade_name: Optional[str] = None
    document: str
    state_registration: Optional[str] = None
    admin_name: str
    admin_email: str
    admin_cpf: str
    admin_phone: Optional[str] = None
    declared_store_count: int
    status: CompanyRegistrationStatus
    notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    created_company_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class CompanyRegistrationApproveResponse(SQLModel):
    registration: CompanyRegistrationResponse
    company_id: int
    admin_username: str
    admin_email: str
    temporary_password: str


class CompanyRegistrationRequest(SQLModel, table=True):
    __tablename__ = "company_registration_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    legal_name: str = Field(max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    document: str = Field(max_length=14, index=True)
    state_registration: Optional[str] = Field(default=None, max_length=14)
    admin_name: str = Field(max_length=150)
    admin_email: str = Field(max_length=255)
    admin_cpf: str = Field(max_length=11)
    admin_phone: Optional[str] = Field(default=None, max_length=20)
    declared_store_count: int
    status: str = Field(default=CompanyRegistrationStatus.PENDING.value, max_length=20, index=True)
    notes: Optional[str] = Field(default=None, max_length=1000)
    reviewed_at: Optional[datetime] = Field(default=None)
    reviewed_by: Optional[str] = Field(default=None, max_length=100)
    created_company_id: Optional[int] = Field(default=None, foreign_key="companies.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
