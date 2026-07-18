from datetime import datetime, timezone
from typing import Optional

from pydantic import field_validator, model_validator
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

BRAZILIAN_STATE_IBGE_CODES = {
    "AC": "12",
    "AL": "27",
    "AP": "16",
    "AM": "13",
    "BA": "29",
    "CE": "23",
    "DF": "53",
    "ES": "32",
    "GO": "52",
    "MA": "21",
    "MT": "51",
    "MS": "50",
    "MG": "31",
    "PA": "15",
    "PB": "25",
    "PR": "41",
    "PE": "26",
    "PI": "22",
    "RJ": "33",
    "RN": "24",
    "RS": "43",
    "RO": "11",
    "RR": "14",
    "SC": "42",
    "SP": "35",
    "SE": "28",
    "TO": "17",
}


class SupplierAddressBase(SQLModel):
    description: str = Field(default="Principal", max_length=50)
    zip_code: str = Field(max_length=8)
    street: str = Field(max_length=255)
    number: str = Field(max_length=20)
    complement: Optional[str] = Field(default=None, max_length=100)
    neighborhood: str = Field(max_length=100)
    city: str = Field(max_length=100)
    state: str = Field(max_length=2)
    ibge_code: str = Field(max_length=7)

    @field_validator("zip_code", mode="before")
    @classmethod
    def normalize_zip_code(cls, value: object) -> str:
        digits = "".join(character for character in str(value or "") if character.isdigit())
        if len(digits) != 8:
            raise ValueError("zip_code must contain 8 digits")
        return digits

    @field_validator(
        "description", "street", "number", "neighborhood", "city", mode="before"
    )
    @classmethod
    def require_text(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("field must not be empty")
        return normalized

    @field_validator("state", mode="before")
    @classmethod
    def normalize_state(cls, value: object) -> str:
        state = str(value or "").strip().upper()
        if state not in BRAZILIAN_STATE_IBGE_CODES:
            raise ValueError("state must be a valid Brazilian UF")
        return state

    @field_validator("ibge_code", mode="before")
    @classmethod
    def validate_ibge_digits(cls, value: object) -> str:
        code = str(value or "").strip()
        if len(code) != 7 or not code.isdigit():
            raise ValueError("ibge_code must contain 7 digits")
        return code

    @model_validator(mode="after")
    def validate_state_matches_ibge(self):
        if not self.ibge_code.startswith(BRAZILIAN_STATE_IBGE_CODES[self.state]):
            raise ValueError("ibge_code does not match the selected state")
        return self


class SupplierAddressCreate(SupplierAddressBase):
    pass


class SupplierAddressUpdate(SQLModel):
    description: Optional[str] = None
    zip_code: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    ibge_code: Optional[str] = None


class SupplierAddressResponse(SupplierAddressBase):
    id: int


class SupplierBase(SQLModel):
    name: str = Field(max_length=255, description="Razão social")
    trade_name: Optional[str] = Field(default=None, max_length=255, description="Nome fantasia")
    document: str = Field(max_length=14, index=True, description="CNPJ apenas dígitos")
    state_registration: Optional[str] = Field(default=None, max_length=14)
    email: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)


class SupplierCreate(SupplierBase):
    document: str = Field(max_length=18, description="CNPJ com ou sem pontuação")
    address: SupplierAddressCreate


class SupplierUpdate(SQLModel):
    name: Optional[str] = None
    trade_name: Optional[str] = None
    document: Optional[str] = Field(default=None, max_length=18)
    state_registration: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    address: Optional[SupplierAddressUpdate] = None


class SupplierResponse(SupplierBase):
    id: int
    company_id: int
    code: Optional[str] = None
    address: Optional[SupplierAddressResponse] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


class Supplier(SupplierBase, table=True):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("company_id", "document", name="uq_suppliers_company_document"),
        UniqueConstraint("company_id", "code", name="uq_suppliers_company_code"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    code: Optional[str] = Field(default=None, max_length=8)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    address: Optional["SupplierAddress"] = Relationship(
        back_populates="supplier",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "single_parent": True,
        },
    )


class SupplierAddress(SupplierAddressBase, table=True):
    __tablename__ = "supplier_addresses"
    __table_args__ = (
        UniqueConstraint("supplier_id", name="uq_supplier_addresses_supplier_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    supplier_id: int = Field(foreign_key="suppliers.id")
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    supplier: Supplier = Relationship(back_populates="address")


class SupplierMunicipality(SQLModel, table=True):
    __tablename__ = "supplier_municipalities"
    __table_args__ = (
        UniqueConstraint("state", "ibge_code", name="uq_supplier_municipality_state_ibge"),
        UniqueConstraint("state", "sequence", name="uq_supplier_municipality_state_sequence"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    state: str = Field(max_length=2)
    ibge_code: str = Field(max_length=7)
    sequence: int


class SupplierSequence(SQLModel, table=True):
    __tablename__ = "supplier_sequences"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "municipality_id",
            name="uq_supplier_sequence_company_municipality",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    municipality_id: int = Field(foreign_key="supplier_municipalities.id")
    last_sequence: int = Field(default=0)
