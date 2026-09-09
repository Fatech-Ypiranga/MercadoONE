"""add companies branches stores and tenant columns

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-11 01:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_CNPJ = "00000000000191"


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("legal_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("trade_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("document", sqlmodel.sql.sqltypes.AutoString(length=14), nullable=False),
        sa.Column("state_registration", sqlmodel.sql.sqltypes.AutoString(length=14), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document", name="uq_companies_document"),
    )
    op.create_index(op.f("ix_companies_document"), "companies", ["document"], unique=False)

    op.create_table(
        "branches",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_branches_company_code"),
    )
    op.create_index(op.f("ix_branches_company_id"), "branches", ["company_id"], unique=False)

    op.create_table(
        "stores",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_stores_company_code"),
    )
    op.create_index(op.f("ix_stores_branch_id"), "stores", ["branch_id"], unique=False)
    op.create_index(op.f("ix_stores_company_id"), "stores", ["company_id"], unique=False)

    # Seed default org for backfill
    op.execute(
        sa.text(
            """
            INSERT INTO companies (legal_name, trade_name, document, is_active, created_at, updated_at)
            VALUES (
                'PyERP Demo Ltda',
                'PyERP Demo',
                :cnpj,
                true,
                NOW(),
                NOW()
            )
            """
        ).bindparams(cnpj=SEED_CNPJ)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO branches (name, code, is_active, company_id, created_at, updated_at)
            SELECT 'Matriz', 'MATRIZ', true, id, NOW(), NOW()
            FROM companies WHERE document = :cnpj
            """
        ).bindparams(cnpj=SEED_CNPJ)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO stores (name, code, is_active, company_id, branch_id, created_at, updated_at)
            SELECT 'Loja Centro', 'LOJA-CENTRO', true, b.company_id, b.id, NOW(), NOW()
            FROM branches b
            JOIN companies c ON c.id = b.company_id
            WHERE c.document = :cnpj AND b.code = 'MATRIZ'
            """
        ).bindparams(cnpj=SEED_CNPJ)
    )

    # --- users ---
    op.add_column("users", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("default_branch_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("default_store_id", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE users SET
                company_id = (SELECT id FROM companies WHERE document = :cnpj),
                default_branch_id = (
                    SELECT b.id FROM branches b
                    JOIN companies c ON c.id = b.company_id
                    WHERE c.document = :cnpj AND b.code = 'MATRIZ'
                ),
                default_store_id = (
                    SELECT s.id FROM stores s
                    JOIN companies c ON c.id = s.company_id
                    WHERE c.document = :cnpj AND s.code = 'LOJA-CENTRO'
                )
            """
        ).bindparams(cnpj=SEED_CNPJ)
    )
    op.alter_column("users", "company_id", nullable=False)
    op.create_foreign_key("fk_users_company_id", "users", "companies", ["company_id"], ["id"])
    op.create_foreign_key(
        "fk_users_default_branch_id", "users", "branches", ["default_branch_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_users_default_store_id", "users", "stores", ["default_store_id"], ["id"]
    )
    op.create_index(op.f("ix_users_company_id"), "users", ["company_id"], unique=False)

    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_cpf_key")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key")
    op.execute("DROP INDEX IF EXISTS ix_users_cpf")
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.create_index(op.f("ix_users_cpf"), "users", ["cpf"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)
    op.create_unique_constraint("uq_users_company_cpf", "users", ["company_id", "cpf"])
    op.create_unique_constraint("uq_users_company_email", "users", ["company_id", "email"])
    op.create_unique_constraint("uq_users_company_username", "users", ["company_id", "username"])

    def add_company_id(table: str) -> None:
        op.add_column(table, sa.Column("company_id", sa.Integer(), nullable=True))
        op.execute(
            sa.text(
                f"UPDATE {table} SET company_id = (SELECT id FROM companies WHERE document = :cnpj)"
            ).bindparams(cnpj=SEED_CNPJ)
        )
        op.alter_column(table, "company_id", nullable=False)
        op.create_foreign_key(f"fk_{table}_company_id", table, "companies", ["company_id"], ["id"])
        op.create_index(op.f(f"ix_{table}_company_id"), table, ["company_id"], unique=False)

    def add_company_and_store(table: str) -> None:
        add_company_id(table)
        op.add_column(table, sa.Column("store_id", sa.Integer(), nullable=True))
        op.execute(
            sa.text(
                f"""
                UPDATE {table} SET store_id = (
                    SELECT s.id FROM stores s
                    JOIN companies c ON c.id = s.company_id
                    WHERE c.document = :cnpj AND s.code = 'LOJA-CENTRO'
                )
                """
            ).bindparams(cnpj=SEED_CNPJ)
        )
        op.alter_column(table, "store_id", nullable=False)
        op.create_foreign_key(f"fk_{table}_store_id", table, "stores", ["store_id"], ["id"])
        op.create_index(op.f(f"ix_{table}_store_id"), table, ["store_id"], unique=False)

    # categories: company_id + composite unique slug
    add_company_id("categories")
    op.execute("ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_slug_key")
    op.execute("DROP INDEX IF EXISTS ix_categories_slug")
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=False)
    op.create_unique_constraint("uq_categories_company_slug", "categories", ["company_id", "slug"])

    add_company_id("brands")

    # products
    add_company_id("products")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_sku_key")
    op.execute("DROP INDEX IF EXISTS ix_products_sku")
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=False)
    op.create_unique_constraint("uq_products_company_sku", "products", ["company_id", "sku"])

    # customers
    add_company_id("customers")
    op.execute("ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_document_key")
    op.execute("DROP INDEX IF EXISTS ix_customers_document")
    op.create_index(op.f("ix_customers_document"), "customers", ["document"], unique=False)
    op.create_unique_constraint(
        "uq_customers_company_document", "customers", ["company_id", "document"]
    )

    # suppliers
    add_company_id("suppliers")
    op.execute("ALTER TABLE suppliers DROP CONSTRAINT IF EXISTS suppliers_document_key")
    op.execute("DROP INDEX IF EXISTS ix_suppliers_document")
    op.create_index(op.f("ix_suppliers_document"), "suppliers", ["document"], unique=False)
    op.create_unique_constraint(
        "uq_suppliers_company_document", "suppliers", ["company_id", "document"]
    )

    add_company_and_store("sales")
    add_company_and_store("stock_movements")
    add_company_and_store("purchase_orders")

    # audit_log company_id (nullable for system rows)
    op.add_column("audit_log", sa.Column("company_id", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE audit_log SET company_id = (SELECT id FROM companies WHERE document = :cnpj)
            """
        ).bindparams(cnpj=SEED_CNPJ)
    )
    op.create_foreign_key(
        "fk_audit_log_company_id", "audit_log", "companies", ["company_id"], ["id"]
    )
    op.create_index(op.f("ix_audit_log_company_id"), "audit_log", ["company_id"], unique=False)


def downgrade() -> None:
    op.drop_constraint("fk_audit_log_company_id", "audit_log", type_="foreignkey")
    op.drop_index(op.f("ix_audit_log_company_id"), table_name="audit_log")
    op.drop_column("audit_log", "company_id")

    for table in ("purchase_orders", "stock_movements", "sales"):
        op.drop_constraint(f"fk_{table}_store_id", table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_store_id"), table_name=table)
        op.drop_column(table, "store_id")
        op.drop_constraint(f"fk_{table}_company_id", table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_company_id"), table_name=table)
        op.drop_column(table, "company_id")

    op.drop_constraint("uq_suppliers_company_document", "suppliers", type_="unique")
    op.drop_constraint("fk_suppliers_company_id", "suppliers", type_="foreignkey")
    op.drop_index(op.f("ix_suppliers_company_id"), table_name="suppliers")
    op.drop_column("suppliers", "company_id")
    op.create_unique_constraint("suppliers_document_key", "suppliers", ["document"])

    op.drop_constraint("uq_customers_company_document", "customers", type_="unique")
    op.drop_constraint("fk_customers_company_id", "customers", type_="foreignkey")
    op.drop_index(op.f("ix_customers_company_id"), table_name="customers")
    op.drop_column("customers", "company_id")
    op.create_unique_constraint("customers_document_key", "customers", ["document"])

    op.drop_constraint("uq_products_company_sku", "products", type_="unique")
    op.drop_constraint("fk_products_company_id", "products", type_="foreignkey")
    op.drop_index(op.f("ix_products_company_id"), table_name="products")
    op.drop_column("products", "company_id")
    op.create_unique_constraint("products_sku_key", "products", ["sku"])

    op.drop_constraint("fk_brands_company_id", "brands", type_="foreignkey")
    op.drop_index(op.f("ix_brands_company_id"), table_name="brands")
    op.drop_column("brands", "company_id")

    op.drop_constraint("uq_categories_company_slug", "categories", type_="unique")
    op.drop_constraint("fk_categories_company_id", "categories", type_="foreignkey")
    op.drop_index(op.f("ix_categories_company_id"), table_name="categories")
    op.drop_column("categories", "company_id")
    op.create_unique_constraint("categories_slug_key", "categories", ["slug"])

    op.drop_constraint("uq_users_company_username", "users", type_="unique")
    op.drop_constraint("uq_users_company_email", "users", type_="unique")
    op.drop_constraint("uq_users_company_cpf", "users", type_="unique")
    op.drop_constraint("fk_users_default_store_id", "users", type_="foreignkey")
    op.drop_constraint("fk_users_default_branch_id", "users", type_="foreignkey")
    op.drop_constraint("fk_users_company_id", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_company_id"), table_name="users")
    op.drop_column("users", "default_store_id")
    op.drop_column("users", "default_branch_id")
    op.drop_column("users", "company_id")
    op.create_unique_constraint("users_cpf_key", "users", ["cpf"])
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.create_unique_constraint("users_username_key", "users", ["username"])

    op.drop_table("stores")
    op.drop_table("branches")
    op.drop_table("companies")
