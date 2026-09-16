"""add composite/missing indexes for hot-path list queries

Revision ID: m3b4c5d6e7f8
Revises: l2a3b4c5d6e7
Create Date: 2026-09-09 00:00:00.000000

Adds indexes identified by the performance review in docs/ROADMAP.md
(DB-01, DB-03, DB-04): sales and purchase_orders listing filter by
company_id + a date column + status, but only had single-column indexes
on each, forcing Postgres to pick one and filter the rest. stock_movements'
balance calculation (SUM over product_id/store_id/type) had the same gap.
These are additive, non-destructive index-only changes.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "m3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "l2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_sales_company_saledate_status",
        "sales",
        ["company_id", "sale_date", "status"],
    )
    op.create_index("ix_sales_customer_id", "sales", ["customer_id"])
    op.create_index(
        "ix_purchase_orders_company_entrydate",
        "purchase_orders",
        ["company_id", "entry_date"],
    )
    op.create_index(
        "ix_stock_movements_product_store_type",
        "stock_movements",
        ["product_id", "store_id", "type"],
    )


def downgrade() -> None:
    op.drop_index("ix_stock_movements_product_store_type", table_name="stock_movements")
    op.drop_index("ix_purchase_orders_company_entrydate", table_name="purchase_orders")
    op.drop_index("ix_sales_customer_id", table_name="sales")
    op.drop_index("ix_sales_company_saledate_status", table_name="sales")
