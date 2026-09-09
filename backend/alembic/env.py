import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Imported for their side effect of registering tables on SQLModel.metadata.
import categories.models  # noqa: F401
import company_registration.models  # noqa: F401
import customers.models  # noqa: F401
import organization.models  # noqa: F401
import products.models  # noqa: F401
import purchases.models  # noqa: F401
import sales.models  # noqa: F401
import shared.audit  # noqa: F401
import stock.models  # noqa: F401
import suppliers.models  # noqa: F401
import users.models  # noqa: F401
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

if not config.get_main_option("sqlalchemy.url"):
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://erp_user:erp_password@localhost:5432/erp_vendas",
    )
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
