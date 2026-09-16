from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import Index, text
from sqlmodel import Field, Relationship, SQLModel

from suppliers.models import SupplierAddressCreate
from utils.enums import PurchaseStatus, enum_column


class SupplierProductMappingBase(SQLModel):
    supplier_id: int = Field(foreign_key="suppliers.id", index=True)
    supplier_product_code: str = Field(max_length=50, index=True)
    product_id: int = Field(foreign_key="products.id")


class SupplierProductMapping(SupplierProductMappingBase, table=True):
    __tablename__ = "supplier_product_mappings"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PurchaseItemBase(SQLModel):
    product_id: int = Field(foreign_key="products.id")
    quantity: Decimal = Field(gt=0, decimal_places=3, max_digits=10)
    unit_cost: Decimal = Field(decimal_places=2, max_digits=12)
    discount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=12)
    ipi_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=12)
    icms_st_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=12)
    total_cost: Decimal = Field(decimal_places=2, max_digits=12)


class PurchaseItemResponse(PurchaseItemBase):
    id: int
    purchase_order_id: int
    supplier_product_code: Optional[str] = None
    product_name: Optional[str] = None


class PurchaseItem(PurchaseItemBase, table=True):
    __tablename__ = "purchase_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    purchase_order_id: int = Field(foreign_key="purchase_orders.id", index=True)
    supplier_product_code: Optional[str] = Field(default=None, max_length=50)

    purchase_order: "PurchaseOrder" = Relationship(back_populates="items")


class PurchaseOrderBase(SQLModel):
    supplier_id: int = Field(foreign_key="suppliers.id", index=True)
    user_id: int = Field(foreign_key="users.id")
    invoice_number: Optional[str] = Field(default=None, max_length=20)
    invoice_series: Optional[str] = Field(default=None, max_length=10)
    invoice_key: Optional[str] = Field(default=None, max_length=44, index=True)
    issue_date: Optional[datetime] = None
    entry_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_amount: Decimal = Field(decimal_places=2, max_digits=12)
    status: PurchaseStatus = Field(default=PurchaseStatus.CONFIRMADO)
    xml_path: Optional[str] = Field(default=None, max_length=255)


class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    company_id: int
    store_id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    supplier_name: Optional[str] = None


class PurchaseOrderDetailResponse(PurchaseOrderResponse):
    items: list[PurchaseItemResponse] = []


class PurchaseOrder(PurchaseOrderBase, table=True):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index(
            "uq_purchase_orders_company_invoice_key",
            "company_id",
            "invoice_key",
            unique=True,
            postgresql_where=text("invoice_key IS NOT NULL"),
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)
    store_id: int = Field(foreign_key="stores.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

    status: PurchaseStatus = Field(sa_column=enum_column(PurchaseStatus))
    items: list[PurchaseItem] = Relationship(back_populates="purchase_order")


class NfeItemPreview(SQLModel):
    line_number: int
    supplier_product_code: str
    barcode: Optional[str] = None
    name: str
    ncm: str
    unit: str
    quantity: Decimal
    unit_cost: Decimal
    discount: Decimal
    ipi_amount: Decimal
    icms_st_amount: Decimal
    entry_unit_cost: Decimal
    total_cost: Decimal
    mapping_status: Literal["mapped", "unmapped"]
    suggested_product_id: Optional[int] = None
    suggested_product_name: Optional[str] = None


class NfeSupplierAddressPreview(SQLModel):
    zip_code: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    ibge_code: Optional[str] = None


class NfeSupplierPreview(SQLModel):
    document: str
    name: str
    trade_name: Optional[str] = None
    state_registration: Optional[str] = None
    address: NfeSupplierAddressPreview
    exists_in_database: bool = False
    supplier_id: Optional[int] = None


class NfeInvoicePreview(SQLModel):
    access_key: str
    invoice_number: str
    invoice_series: str
    issue_date: datetime
    total_amount: Decimal


class NfeUploadPreviewResponse(SQLModel):
    supplier: NfeSupplierPreview
    invoice: NfeInvoicePreview
    items: list[NfeItemPreview]


class PurchaseProductCreateInput(SQLModel):
    name: str
    sku: str
    barcode: Optional[str] = None
    category_id: int
    cost_price: Decimal = Field(ge=0)
    sale_price: Optional[Decimal] = Field(default=None, ge=0)
    unit_of_measure: str = "UN"
    ncm: Optional[str] = None


class PurchaseConfirmItemInput(SQLModel):
    supplier_product_code: str
    quantity: Decimal = Field(gt=0, decimal_places=3, max_digits=10)
    unit_cost: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, max_digits=12)
    ipi_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, max_digits=12)
    icms_st_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, max_digits=12)
    total_cost: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    product_id: Optional[int] = None
    create_product: Optional[PurchaseProductCreateInput] = None


class PurchaseConfirmRequest(SQLModel):
    access_key: str
    invoice_number: str
    invoice_series: str
    issue_date: datetime
    supplier_id: Optional[int] = None
    create_supplier: bool = False
    supplier_name: Optional[str] = None
    supplier_trade_name: Optional[str] = None
    supplier_document: Optional[str] = None
    supplier_state_registration: Optional[str] = None
    supplier_address: SupplierAddressCreate | None = None
    items: list[PurchaseConfirmItemInput]
    xml_path: Optional[str] = None
    store_id: Optional[int] = None


PurchaseOrderDetailResponse.model_rebuild()
