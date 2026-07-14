import os

from sqlmodel import Session, create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://erp_user:erp_password@localhost:5432/erp_vendas",
)

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)


def init_db() -> None:
    from sqlalchemy.exc import ProgrammingError

    from database.migrate import upgrade_head
    from database.seed import seed_admin_user

    try:
        upgrade_head()
    except ProgrammingError as exc:
        if exc.orig and getattr(exc.orig, "pgcode", None) == "42P07":
            raise RuntimeError(
                "Conflito de schema: o banco já tem tabelas, mas o Alembic não foi "
                "aplicado (falta alembic_version). Para ambiente de desenvolvimento, "
                "recrie o banco com: docker compose down -v && docker compose up -d"
            ) from exc
        raise
    with Session(engine) as session:
        seed_admin_user(session)


def get_db():
    """Dependency para os Routers do FastAPI."""
    with Session(engine) as session:
        yield session
