from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Index, text
from sqlmodel import Field, Relationship, SQLModel


class SaleStatus(str):
    EM_ANDAMENTO = "Em_Andamento"
    CONCLUIDA = "Concluida"
    CANCELADA = "Cancelada"
    SUSPENSA = "Suspensa"


class SaleBase(SQLModel):
    customer_id: Optional[int] = Field(default=None, foreign_key="customers.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    sale_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    total_amount: Decimal = Field(default=0.0, decimal_places=2, max_digits=12)
    discount_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=12)
    payment_method: Optional[str] = Field(default=None, max_length=20)
    status: str = Field(default=SaleStatus.EM_ANDAMENTO, max_length=20, index=True)


class SaleCreate(SaleBase):
    pass


class SaleResponse(SaleBase):
    id: int
    company_id: int
    store_id: int
    client_sale_id: Optional[str] = None


class SalePaymentBase(SQLModel):
    sale_id: int = Field(foreign_key="sales.id", index=True)
    method: str = Field(max_length=20)
    amount: Decimal = Field(decimal_places=2, max_digits=12)


class SalePaymentResponse(SQLModel):
    id: int
    method: str
    amount: Decimal


class SaleItemBase(SQLModel):
    sale_id: int = Field(foreign_key="sales.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(decimal_places=2, max_digits=12)


class SaleItemCreate(SaleItemBase):
    pass


class SaleItemResponse(SaleItemBase):
    id: int


class SalePayment(SalePaymentBase, table=True):
    __tablename__ = "sale_payments"

    id: Optional[int] = Field(default=None, primary_key=True)
    sale: Optional["Sale"] = Relationship(back_populates="payments")


class SaleItem(SaleItemBase, table=True):
    __tablename__ = "sale_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    sale: Optional["Sale"] = Relationship(back_populates="items")


class Sale(SaleBase, table=True):
    __tablename__ = "sales"
    __table_args__ = (
        Index(
            "uq_sales_company_client_sale_id",
            "company_id",
            "client_sale_id",
            unique=True,
            postgresql_where=text("client_sale_id IS NOT NULL"),
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    store_id: int = Field(foreign_key="stores.id", index=True)
    client_sale_id: Optional[str] = Field(default=None, max_length=64)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")
    items: list[SaleItem] = Relationship(back_populates="sale")
    payments: list[SalePayment] = Relationship(
        back_populates="sale", sa_relationship_kwargs={"order_by": "SalePayment.id"}
    )


class SaleDetailResponse(SaleResponse):
    items: list[SaleItemResponse] = []
    payments: list[SalePaymentResponse] = []


SaleDetailResponse.model_rebuild()
