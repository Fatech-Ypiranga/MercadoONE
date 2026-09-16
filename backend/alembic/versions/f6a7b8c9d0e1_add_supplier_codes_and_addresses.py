"""add supplier codes and main addresses

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("code", sa.String(length=8), nullable=True))
    op.create_unique_constraint(
        "uq_suppliers_company_code",
        "suppliers",
        ["company_id", "code"],
    )

    op.create_table(
        "supplier_municipalities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("ibge_code", sa.String(length=7), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "state",
            "ibge_code",
            name="uq_supplier_municipality_state_ibge",
        ),
        sa.UniqueConstraint(
            "state",
            "sequence",
            name="uq_supplier_municipality_state_sequence",
        ),
    )
    op.create_table(
        "supplier_sequences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("municipality_id", sa.Integer(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["municipality_id"],
            ["supplier_municipalities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "municipality_id",
            name="uq_supplier_sequence_company_municipality",
        ),
    )
    op.create_table(
        "supplier_addresses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=50), nullable=False),
        sa.Column("zip_code", sa.String(length=8), nullable=False),
        sa.Column("street", sa.String(length=255), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("complement", sa.String(length=100), nullable=True),
        sa.Column("neighborhood", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("ibge_code", sa.String(length=7), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supplier_id",
            name="uq_supplier_addresses_supplier_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("supplier_addresses")
    op.drop_table("supplier_sequences")
    op.drop_table("supplier_municipalities")
    op.drop_constraint("uq_suppliers_company_code", "suppliers", type_="unique")
    op.drop_column("suppliers", "code")
