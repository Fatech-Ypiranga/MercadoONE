import os

from sqlmodel import Session, create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://erp_user:erp_password@localhost:5432/erp_vendas",
)

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
)


def init_db() -> None:
    """Seed only. Migrations run via entrypoint / Railway pre-deploy / alembic CLI."""
    from database.seed import seed_admin_user

    with Session(engine) as session:
        seed_admin_user(session)


def get_db():
    """Dependency para os Routers do FastAPI."""
    with Session(engine) as session:
        yield session
