"""add users audit and audit columns

Revision ID: a1b2c3d4e5f6
Revises: e9a45e47d010
Create Date: 2026-07-10 01:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e9a45e47d010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

userprofile_enum = postgresql.ENUM(
    "admin",
    "gerente",
    "supervisor",
    "operador",
    "conferente",
    "colaborador",
    name="userprofile",
    create_type=False,
)
auditaction_enum = postgresql.ENUM(
    "CREATE",
    "UPDATE",
    "DELETE",
    "STOCK_MOVE",
    "ROLE_CHANGE",
    "PASSWORD_CHANGE",
    name="auditaction",
    create_type=False,
)


def upgrade() -> None:
    userprofile_enum.create(op.get_bind(), checkfirst=True)
    auditaction_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("cpf", sqlmodel.sql.sqltypes.AutoString(length=11), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=True),
        sa.Column("username", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("password_hash", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("profile", userprofile_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpf"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_cpf"), "users", ["cpf"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "audit_log",
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", auditaction_enum, nullable=False),
        sa.Column("entity_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_log_created_at"), "audit_log", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_log_entity_type"), "audit_log", ["entity_type"], unique=False)
    op.create_index(op.f("ix_audit_log_user_id"), "audit_log", ["user_id"], unique=False)

    audit_tables = [
        "categories",
        "brands",
        "products",
        "customers",
        "customer_addresses",
        "sales",
        "stock_movements",
    ]
    for table in audit_tables:
        op.add_column(table, sa.Column("created_by", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("updated_by", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_created_by_users", table, "users", ["created_by"], ["id"]
        )
        op.create_foreign_key(
            f"fk_{table}_updated_by_users", table, "users", ["updated_by"], ["id"]
        )

    op.create_foreign_key("fk_sales_user_id_users", "sales", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_sales_user_id_users", "sales", type_="foreignkey")

    audit_tables = [
        "stock_movements",
        "sales",
        "customer_addresses",
        "customers",
        "products",
        "brands",
        "categories",
    ]
    for table in audit_tables:
        op.drop_constraint(f"fk_{table}_updated_by_users", table, type_="foreignkey")
        op.drop_constraint(f"fk_{table}_created_by_users", table, type_="foreignkey")
        op.drop_column(table, "updated_by")
        op.drop_column(table, "created_by")

    op.drop_index(op.f("ix_audit_log_user_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_entity_type"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_created_at"), table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_cpf"), table_name="users")
    op.drop_table("users")

    auditaction_enum.drop(op.get_bind(), checkfirst=True)
    userprofile_enum.drop(op.get_bind(), checkfirst=True)
