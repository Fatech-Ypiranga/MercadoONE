from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Annotated, Optional

from pydantic import StringConstraints
from sqlalchemy import Index, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from categories.models import Category, CategoryResponse


class UnitOfMeasure(str, PyEnum):
    UN = "UN"
    KG = "KG"
    CX = "CX"


class ProductFiscalBase(SQLModel):
    ncm: str = Field(max_length=8)
    cest: Optional[str] = Field(default=None, max_length=7)
    cfop_default: str = Field(max_length=4)
    origem_produto: int = Field(default=0)


class ProductFiscalCreate(ProductFiscalBase):
    pass


class ProductFiscalResponse(ProductFiscalBase):
    id: int


class ProductFiscal(ProductFiscalBase, table=True):
    __tablename__ = "product_fiscals"
    id: Optional[int] = Field(default=None, primary_key=True)

    product_id: int = Field(foreign_key="products.id", unique=True)
    product: "Product" = Relationship(back_populates="fiscal")


class ProductBase(SQLModel):
    name: str = Field(index=True, max_length=255)
    sku: str = Field(index=True, max_length=50)
    barcode: Optional[str] = Field(default=None, max_length=14, index=True)
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)

    cost_price: Decimal = Field(default=0.0, decimal_places=2, max_digits=10)
    sale_price: Decimal = Field(default=0.0, decimal_places=2, max_digits=10)
    weight_net: Optional[Decimal] = Field(default=Decimal("0"), decimal_places=3, max_digits=10)
    weight_gross: Optional[Decimal] = Field(default=Decimal("0"), decimal_places=3, max_digits=10)
    unit_of_measure: UnitOfMeasure = Field(default=UnitOfMeasure.UN)
    min_stock: Optional[Decimal] = Field(default=None, decimal_places=3, max_digits=10, ge=0)

    category_id: int = Field(foreign_key="categories.id")


class ProductCreate(ProductBase):
    primary_supplier_id: int
    fiscal: Optional[ProductFiscalCreate] = None


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    cost_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    weight_net: Optional[Decimal] = None
    weight_gross: Optional[Decimal] = None
    unit_of_measure: Optional[UnitOfMeasure] = None
    min_stock: Optional[Decimal] = Field(default=None, ge=0)
    category_id: Optional[int] = None
    primary_supplier_id: Optional[int] = None
    fiscal: Optional[ProductFiscalCreate] = None


class ProductResponse(ProductBase):
    id: int
    company_id: int
    material_code: Annotated[str, StringConstraints(pattern=r"^\d{7}$")]
    primary_supplier_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


class ProductDetailResponse(ProductResponse):
    category: "CategoryResponse"
    fiscal: Optional[ProductFiscalResponse] = None


class Product(ProductBase, table=True):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_products_company_sku"),
        UniqueConstraint(
            "company_id",
            "material_code",
            name="uq_products_company_material_code",
        ),
        Index(
            "uq_products_company_barcode",
            "company_id",
            "barcode",
            unique=True,
            postgresql_where=text("barcode IS NOT NULL"),
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    material_code: str = Field(max_length=7)
    primary_supplier_id: Optional[int] = Field(
        default=None,
        foreign_key="suppliers.id",
        index=True,
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    category: "Category" = Relationship(back_populates="products")
    fiscal: Optional[ProductFiscal] = Relationship(back_populates="product")


class ProductMaterialSequence(SQLModel, table=True):
    __tablename__ = "product_material_sequences"

    company_id: int = Field(
        primary_key=True,
        foreign_key="companies.id",
    )
    last_sequence: int = Field(default=0)


from categories.models import CategoryResponse

ProductDetailResponse.model_rebuild()
