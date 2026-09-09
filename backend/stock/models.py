from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from utils.enums import MovementReason, MovementType, enum_column

if TYPE_CHECKING:
    from products.models import Product


class StockMovementBase(SQLModel):
    product_id: int = Field(foreign_key="products.id", index=True)

    quantity: Decimal = Field(gt=0, decimal_places=3, max_digits=10)

    type: MovementType = Field(description="Entrada ou saída")
    reason: MovementReason = Field(description="Motivo da movimentação")

    source_sale_id: Optional[int] = Field(default=None, description="Venda de origem, se houver")
    observations: Optional[str] = Field(default=None, description="Observações livres")


class StockMovementCreate(StockMovementBase):
    store_id: Optional[int] = None


class StockMovementResponse(StockMovementBase):
    id: int
    company_id: int
    store_id: int
    created_at: datetime


class StockMovement(StockMovementBase, table=True):
    __tablename__ = "stock_movements"

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    store_id: int = Field(foreign_key="stores.id", index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    type: MovementType = Field(sa_column=enum_column(MovementType))
    reason: MovementReason = Field(sa_column=enum_column(MovementReason))

    product: Optional["Product"] = Relationship()
