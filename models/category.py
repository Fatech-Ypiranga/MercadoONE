from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .product import Product


class CategoryBase(SQLModel):
    name: str = Field(index=True, max_length=100, description="Nome da categoria")
    slug: str = Field(max_length=100, index=True, description="Slug amigável (ex.: eletronicos)")
    is_active: bool = Field(default=True)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


class Category(CategoryBase, table=True):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("company_id", "slug", name="uq_categories_company_slug"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    products: List["Product"] = Relationship(back_populates="category")


from .product import ProductResponse


class CategoryDetailResponse(CategoryResponse):
    products: List["ProductResponse"] = []


CategoryDetailResponse.model_rebuild()
