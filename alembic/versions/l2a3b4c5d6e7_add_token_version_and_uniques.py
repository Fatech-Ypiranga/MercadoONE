"""add users.token_version for JWT revocation

Revision ID: l2a3b4c5d6e7
Revises: k1f2a3b4c5d6
Create Date: 2026-07-20 20:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "k1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
    )
    # Partial unique: multiple NULL barcodes allowed; non-null barcodes unique per company.
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_products_company_barcode "
            "ON products (company_id, barcode) WHERE barcode IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_purchase_orders_company_invoice_key "
            "ON purchase_orders (company_id, invoice_key) WHERE invoice_key IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_purchase_orders_company_invoice_key"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_products_company_barcode"))
    op.drop_column("users", "token_version")
