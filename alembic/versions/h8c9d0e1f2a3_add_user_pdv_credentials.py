"""add user pdv credentials and sale discount

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-07-18 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "g7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pdv_id", sa.String(length=6), nullable=True))
    op.add_column("users", sa.Column("pdv_pin_hash", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_users_pdv_id"), "users", ["pdv_id"], unique=False)
    op.create_unique_constraint("uq_users_company_pdv_id", "users", ["company_id", "pdv_id"])

    op.add_column(
        "sales",
        sa.Column(
            "discount_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_column("sales", "discount_amount")
    op.drop_constraint("uq_users_company_pdv_id", "users", type_="unique")
    op.drop_index(op.f("ix_users_pdv_id"), table_name="users")
    op.drop_column("users", "pdv_pin_hash")
    op.drop_column("users", "pdv_id")
