"""add suppliers and purchases tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-10 02:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

purchasestatus_enum = postgresql.ENUM(
    "Rascunho",
    "Confirmado",
    "Cancelado",
    name="purchasestatus",
    create_type=False,
)


def upgrade() -> None:
    purchasestatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "suppliers",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("trade_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("document", sqlmodel.sql.sqltypes.AutoString(length=14), nullable=False),
        sa.Column("state_registration", sqlmodel.sql.sqltypes.AutoString(length=14), nullable=True),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=True),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document"),
    )
    op.create_index(op.f("ix_suppliers_document"), "suppliers", ["document"], unique=True)

    op.create_table(
        "purchase_orders",
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("invoice_series", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
        sa.Column("invoice_key", sqlmodel.sql.sqltypes.AutoString(length=44), nullable=True),
        sa.Column("issue_date", sa.DateTime(), nullable=True),
        sa.Column("entry_date", sa.DateTime(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", purchasestatus_enum, nullable=False),
        sa.Column("xml_path", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_key"),
    )
    op.create_index(
        op.f("ix_purchase_orders_invoice_key"), "purchase_orders", ["invoice_key"], unique=True
    )
    op.create_index(
        op.f("ix_purchase_orders_supplier_id"), "purchase_orders", ["supplier_id"], unique=False
    )

    op.create_table(
        "purchase_items",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("discount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("ipi_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("icms_st_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column(
            "supplier_product_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_purchase_items_purchase_order_id"),
        "purchase_items",
        ["purchase_order_id"],
        unique=False,
    )

    op.create_table(
        "supplier_product_mappings",
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column(
            "supplier_product_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False
        ),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supplier_id", "supplier_product_code", name="uq_supplier_product_code"
        ),
    )
    op.create_index(
        op.f("ix_supplier_product_mappings_supplier_id"),
        "supplier_product_mappings",
        ["supplier_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_product_mappings_supplier_product_code"),
        "supplier_product_mappings",
        ["supplier_product_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("supplier_product_mappings")
    op.drop_table("purchase_items")
    op.drop_table("purchase_orders")
    op.drop_table("suppliers")
    purchasestatus_enum.drop(op.get_bind(), checkfirst=True)
