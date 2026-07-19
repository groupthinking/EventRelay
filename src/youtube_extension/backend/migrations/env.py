"""Canonical Alembic environment for EventRelay PostgreSQL migrations."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from youtube_extension.backend.config.database import Base, DatabaseSettings
from youtube_extension.backend.models import (
    APIUsage,
    DailyBudget,
    WebhookOutbox,
)

# Keep imports explicit: importing these classes registers the migration-owned
# tables on the canonical metadata without making an accidental wildcard part
# of the migration contract.
_API_COST_MODELS = (APIUsage, DailyBudget, WebhookOutbox)
API_COST_TABLES = frozenset(model.__tablename__ for model in _API_COST_MODELS)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """Prefer a caller-provided Alembic URL, then the process environment."""
    configured = config.get_main_option("sqlalchemy.url")
    if configured and not configured.startswith("driver://"):
        return configured
    return DatabaseSettings().database_url


def _sync_psycopg_url(url: str) -> str:
    """Return a synchronous Psycopg 3 URL for Alembic."""
    replacements = (
        ("postgresql+asyncpg://", "postgresql+psycopg://"),
        ("postgresql+psycopg2://", "postgresql+psycopg://"),
        ("postgresql://", "postgresql+psycopg://"),
        ("postgres://", "postgresql+psycopg://"),
    )
    for prefix, replacement in replacements:
        if url.startswith(prefix):
            return replacement + url[len(prefix) :]
    if url.startswith("postgresql+psycopg://"):
        return url
    raise ValueError("Alembic migrations require a PostgreSQL DATABASE_URL")


def _table_name_for_object(object_: object, type_: str) -> str | None:
    if type_ == "table":
        return getattr(object_, "name", None)
    table = getattr(object_, "table", None)
    return getattr(table, "name", None)


def include_object(
    object_: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Scope autogeneration to the API-cost tables owned by this substrate."""
    del name, reflected, compare_to
    table_name = _table_name_for_object(object_, type_)
    return table_name in API_COST_TABLES


def _configure(**kwargs: object) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
        transaction_per_migration=True,
        include_object=include_object,
        **kwargs,
    )


def run_migrations_offline() -> None:
    database_url = _sync_psycopg_url(_database_url())
    _configure(
        url=database_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    database_url = _sync_psycopg_url(_database_url())
    engine = create_engine(
        database_url,
        poolclass=pool.NullPool,
        connect_args={"options": "-c search_path=public -c timezone=UTC"},
        future=True,
    )
    try:
        with engine.connect() as connection:
            _run_migrations(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
