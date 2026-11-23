"""add sales.client_sale_id for idempotent sale creation

Revision ID: n4c5d6e7f8a9
Revises: m3b4c5d6e7f8
Create Date: 2026-11-23 00:00:00.000000

Nullable key supplied by the client (PDV). Unique per company when present,
so retries of POST /sales return the original sale instead of duplicating it.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "m3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sales", sa.Column("client_sale_id", sa.String(length=64), nullable=True))
    op.create_index(
        "uq_sales_company_client_sale_id",
        "sales",
        ["company_id", "client_sale_id"],
        unique=True,
        postgresql_where=sa.text("client_sale_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_sales_company_client_sale_id", table_name="sales")
    op.drop_column("sales", "client_sale_id")
