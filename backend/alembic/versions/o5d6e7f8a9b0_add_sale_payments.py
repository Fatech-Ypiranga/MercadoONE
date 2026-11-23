"""add sale_payments (several payments per sale)

Revision ID: o5d6e7f8a9b0
Revises: n4c5d6e7f8a9
Create Date: 2026-11-23 00:00:00.000000

sales.payment_method is kept (single method, or "multiplo" for split sales).
Existing sales that had a payment_method get one sale_payments row with the
whole sale total, so reports can sum by payment for old and new sales alike.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "n4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sale_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id"), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
    )
    op.create_index("ix_sale_payments_sale_id", "sale_payments", ["sale_id"])
    op.execute(
        """
        INSERT INTO sale_payments (sale_id, method, amount)
        SELECT id, lower(trim(payment_method)), total_amount
        FROM sales
        WHERE payment_method IS NOT NULL AND trim(payment_method) <> '' AND total_amount > 0
        """
    )


def downgrade() -> None:
    op.drop_index("ix_sale_payments_sale_id", table_name="sale_payments")
    op.drop_table("sale_payments")
