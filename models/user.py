from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from utils.enums import UserProfile, enum_column


class UserBase(SQLModel):
    full_name: str = Field(max_length=255)
    cpf: str = Field(index=True, max_length=11)
    email: Optional[str] = Field(default=None, index=True, max_length=150)
    username: Optional[str] = Field(default=None, index=True, max_length=50)
    profile: UserProfile = Field(default=UserProfile.COLABORADOR)
    is_active: bool = Field(default=True)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)
    default_branch_id: Optional[int] = None
    default_store_id: Optional[int] = None


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    profile: Optional[UserProfile] = None
    is_active: Optional[bool] = None
    default_branch_id: Optional[int] = None
    default_store_id: Optional[int] = None


class UserPasswordReset(SQLModel):
    new_password: str = Field(min_length=6, max_length=128)


class UserPdvPinResponse(SQLModel):
    user_id: int
    pdv_id: str
    pdv_pin: str
    message: str = "PIN gerado. Guarde agora — não será exibido novamente."


class UserResponse(UserBase):
    id: int
    company_id: int
    default_branch_id: Optional[int] = None
    default_store_id: Optional[int] = None
    pdv_id: Optional[str] = None
    has_pdv_pin: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


class MeCompanyInfo(SQLModel):
    id: int
    legal_name: str
    trade_name: Optional[str] = None
    document: str
    has_branches: bool = False


class MeBranchInfo(SQLModel):
    id: int
    name: str
    code: str


class MeStoreInfo(SQLModel):
    id: int
    name: str
    code: str
    branch_id: int


class MeResponse(UserResponse):
    company: Optional[MeCompanyInfo] = None
    default_branch: Optional[MeBranchInfo] = None
    default_store: Optional[MeStoreInfo] = None


class User(UserBase, table=True):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("company_id", "cpf", name="uq_users_company_cpf"),
        UniqueConstraint("company_id", "email", name="uq_users_company_email"),
        UniqueConstraint("company_id", "username", name="uq_users_company_username"),
        UniqueConstraint("company_id", "pdv_id", name="uq_users_company_pdv_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str = Field(max_length=255)
    pdv_id: Optional[str] = Field(default=None, max_length=6, index=True)
    pdv_pin_hash: Optional[str] = Field(default=None, max_length=255)
    company_id: int = Field(foreign_key="companies.id", index=True)
    default_branch_id: Optional[int] = Field(default=None, foreign_key="branches.id")
    default_store_id: Optional[int] = Field(default=None, foreign_key="stores.id")

    profile: UserProfile = Field(
        default=UserProfile.COLABORADOR, sa_column=enum_column(UserProfile)
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")
