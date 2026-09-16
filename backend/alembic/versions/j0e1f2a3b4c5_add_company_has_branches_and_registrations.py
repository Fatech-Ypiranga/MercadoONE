"""add company has_branches and registration requests

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
Create Date: 2026-07-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "i9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("has_branches", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "company_registration_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("trade_name", sa.String(length=255), nullable=True),
        sa.Column("document", sa.String(length=14), nullable=False),
        sa.Column("state_registration", sa.String(length=14), nullable=True),
        sa.Column("admin_name", sa.String(length=150), nullable=False),
        sa.Column("admin_email", sa.String(length=255), nullable=False),
        sa.Column("admin_cpf", sa.String(length=11), nullable=False),
        sa.Column("admin_phone", sa.String(length=20), nullable=True),
        sa.Column("declared_store_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("created_company_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_company_id"],
            ["companies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_company_registration_requests_document"),
        "company_registration_requests",
        ["document"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_registration_requests_status"),
        "company_registration_requests",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_company_registration_requests_status"),
        table_name="company_registration_requests",
    )
    op.drop_index(
        op.f("ix_company_registration_requests_document"),
        table_name="company_registration_requests",
    )
    op.drop_table("company_registration_requests")
    op.drop_column("companies", "has_branches")
