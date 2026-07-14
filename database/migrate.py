from pathlib import Path

from alembic.config import Config

from alembic import command
from database.connection import DATABASE_URL

ROOT_DIR = Path(__file__).resolve().parents[1]


def get_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url or DATABASE_URL)
    return config


def upgrade_head(database_url: str | None = None) -> None:
    command.upgrade(get_alembic_config(database_url), "head")


def downgrade_base(database_url: str | None = None) -> None:
    command.downgrade(get_alembic_config(database_url), "base")
