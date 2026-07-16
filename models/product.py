from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy as sa
from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .category import Category, CategoryResponse


class UnitOfMeasure(str, PyEnum):
    UN = "UN"
    KG = "KG"
    CX = "CX"


class BrandBase(SQLModel):
    name: str = Field(index=True, max_length=100)


class BrandCreate(BrandBase):
    pass


class BrandUpdate(SQLModel):
    name: Optional[str] = None


class BrandResponse(BrandBase):
    id: int
    company_id: int


class Brand(BrandBase, table=True):
    __tablename__ = "brands"
    __table_args__ = (
        Index("uq_brands_company_lower_name", "company_id", sa.func.lower("name"), unique=True),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    products: List["Product"] = Relationship(back_populates="brand")


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

    category_id: int = Field(foreign_key="categories.id")
    brand_id: Optional[int] = Field(default=None, foreign_key="brands.id")


class ProductCreate(ProductBase):
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
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    fiscal: Optional[ProductFiscalCreate] = None


class ProductResponse(ProductBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


class ProductDetailResponse(ProductResponse):
    category: "CategoryResponse"
    brand: Optional[BrandResponse] = None
    fiscal: Optional[ProductFiscalResponse] = None


class Product(ProductBase, table=True):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("company_id", "sku", name="uq_products_company_sku"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    category: "Category" = Relationship(back_populates="products")
    brand: Optional[Brand] = Relationship(back_populates="products")
    fiscal: Optional[ProductFiscal] = Relationship(back_populates="product")


from .category import CategoryResponse

ProductDetailResponse.model_rebuild()
