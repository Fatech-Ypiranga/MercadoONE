"""add product material codes and remove brands

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-16 00:00:00.000000

The downgrade recreates the brand schema, but deleted brand rows and product
associations cannot be restored.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("material_code", sa.String(length=7), nullable=True))
    op.add_column("products", sa.Column("primary_supplier_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_products_primary_supplier_id_suppliers",
        "products",
        "suppliers",
        ["primary_supplier_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_products_primary_supplier_id"),
        "products",
        ["primary_supplier_id"],
        unique=False,
    )
    op.create_table(
        "product_material_sequences",
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id"),
    )

    op.execute(
        """
        WITH numbered AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY id) AS sequence
            FROM products
        )
        UPDATE products AS product
        SET material_code = LPAD(numbered.sequence::text, 7, '0')
        FROM numbered
        WHERE product.id = numbered.id
        """
    )
    op.execute(
        """
        INSERT INTO product_material_sequences (company_id, last_sequence)
        SELECT company_id, MAX(material_code::integer)
        FROM products
        GROUP BY company_id
        """
    )
    op.execute(
        """
        WITH inferred AS (
            SELECT mapping.product_id, MIN(mapping.supplier_id) AS supplier_id
            FROM supplier_product_mappings AS mapping
            JOIN products AS product ON product.id = mapping.product_id
            JOIN suppliers AS supplier ON supplier.id = mapping.supplier_id
            GROUP BY mapping.product_id
            HAVING COUNT(DISTINCT mapping.supplier_id) = 1
               AND MIN(supplier.company_id) = MIN(product.company_id)
        )
        UPDATE products AS product
        SET primary_supplier_id = inferred.supplier_id
        FROM inferred
        WHERE product.id = inferred.product_id
        """
    )

    op.alter_column("products", "material_code", nullable=False)
    op.create_unique_constraint(
        "uq_products_company_material_code",
        "products",
        ["company_id", "material_code"],
    )

    op.drop_constraint("products_brand_id_fkey", "products", type_="foreignkey")
    op.drop_column("products", "brand_id")
    op.drop_index("uq_brands_company_lower_name", table_name="brands")
    op.drop_table("brands")


def downgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_brands_created_by_users",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_brands_updated_by_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brands_name"), "brands", ["name"], unique=False)
    op.create_index(op.f("ix_brands_company_id"), "brands", ["company_id"], unique=False)
    op.create_index(
        "uq_brands_company_lower_name",
        "brands",
        ["company_id", sa.text("lower(name)")],
        unique=True,
    )
    op.add_column("products", sa.Column("brand_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "products_brand_id_fkey",
        "products",
        "brands",
        ["brand_id"],
        ["id"],
    )

    op.drop_constraint(
        "uq_products_company_material_code",
        "products",
        type_="unique",
    )
    op.drop_table("product_material_sequences")
    op.drop_index(op.f("ix_products_primary_supplier_id"), table_name="products")
    op.drop_constraint(
        "fk_products_primary_supplier_id_suppliers",
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "primary_supplier_id")
    op.drop_column("products", "material_code")
