from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from alembic import command
from alembic.config import Config
from sqlmodel import Session, SQLModel, create_engine

from carms.core.config import Settings

settings = Settings()
engine = create_engine(settings.db_url, echo=False)


def get_engine():
    return engine


@asynccontextmanager
async def session_scope() -> AsyncIterator[Session]:
    """Async-friendly context manager for explicit transactional scopes."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_session() -> AsyncIterator[Session]:
    """FastAPI dependency that yields a database session."""
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def run_migrations() -> None:
    """Apply Alembic migrations up to head."""
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"Missing Alembic config: {alembic_ini}")

    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", settings.db_url)
    command.upgrade(config, "head")


def init_db() -> None:
    """Initialize database schema using Alembic migrations."""
    # Import model modules so metadata stays discoverable for autogenerate workflows.
    import carms.models.bronze  # noqa: F401
    import carms.models.silver  # noqa: F401
    import carms.models.gold  # noqa: F401

    run_migrations()
