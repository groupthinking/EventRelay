"""Unit tests for youtube_extension/services/shared_sql_state.py schema ownership."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, inspect

from youtube_extension.services import shared_sql_state
from youtube_extension.services.shared_sql_state import (
    SHARED_STATE_MIGRATION,
    SharedSQLStateStore,
    SharedStateSchemaError,
)

SHARED_TABLES = {"shared_sessions", "shared_timeline_events", "shared_a2a_messages"}


def _fake_postgres_engine() -> MagicMock:
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    return engine


def _fake_inspector(columns_by_table: dict[str, list[str]]) -> MagicMock:
    inspector = MagicMock()
    inspector.has_table.side_effect = lambda name: name in columns_by_table
    inspector.get_columns.side_effect = lambda name: [
        {"name": column} for column in columns_by_table[name]
    ]
    return inspector


def _full_columns() -> dict[str, list[str]]:
    store = SharedSQLStateStore("sqlite://")
    columns = {table.name: [c.name for c in table.columns] for table in store.metadata.sorted_tables}
    store.engine.dispose()
    return columns


def test_sqlite_default_creates_tables_and_round_trips(tmp_path) -> None:
    db_path = tmp_path / "shared.db"
    store = SharedSQLStateStore(f"sqlite:///{db_path}")

    assert SHARED_TABLES <= set(inspect(store.engine).get_table_names())
    store.save_session({"id": "s1", "title": "first"})
    store.append_timeline_event("s1", {"timestamp": "t1", "summary": "sum", "content": "c"})
    store.append_a2a_message(
        {
            "sender": "a",
            "recipient": "b",
            "conversation_id": "conv",
            "timestamp": "t1",
            "content": {"k": "v"},
        }
    )

    reopened = SharedSQLStateStore(f"sqlite:///{db_path}")
    session = reopened.get_session("s1")
    assert session is not None and session["title"] == "first"
    assert session["timeline"] == [{"timestamp": "t1", "summary": "sum", "content": "c"}]
    assert reopened.get_a2a_messages(conversation_id="conv")[0]["content"] == {"k": "v"}


def test_sqlite_path_default_used_without_database_url(tmp_path) -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("EVENTRELAY_SHARED_STATE_DATABASE_URL", None)
        os.environ.pop("DATABASE_URL", None)
        store = SharedSQLStateStore(sqlite_path=tmp_path / "local.db")
    assert store.engine.dialect.name == "sqlite"
    assert (tmp_path / "local.db").exists()
    assert SHARED_TABLES <= set(inspect(store.engine).get_table_names())


def test_postgres_never_runs_create_all_when_schema_is_migrated() -> None:
    columns = _full_columns()
    with (
        patch.object(SharedSQLStateStore, "_create_engine", return_value=_fake_postgres_engine()),
        patch.object(shared_sql_state, "sa_inspect", return_value=_fake_inspector(columns)),
        patch("sqlalchemy.MetaData.create_all") as create_all,
    ):
        SharedSQLStateStore("postgresql+psycopg://user:pw@db.example.com/app")
    create_all.assert_not_called()


def test_postgres_missing_table_raises_and_names_migration(caplog) -> None:
    columns = _full_columns()
    columns.pop("shared_a2a_messages")
    with (
        patch.object(SharedSQLStateStore, "_create_engine", return_value=_fake_postgres_engine()),
        patch.object(shared_sql_state, "sa_inspect", return_value=_fake_inspector(columns)),
        patch("sqlalchemy.MetaData.create_all") as create_all,
        caplog.at_level("ERROR"),
        pytest.raises(SharedStateSchemaError) as excinfo,
    ):
        SharedSQLStateStore("postgresql+psycopg://user:pw@db.example.com/app")
    create_all.assert_not_called()
    assert "missing table shared_a2a_messages" in str(excinfo.value)
    assert SHARED_STATE_MIGRATION in str(excinfo.value)
    assert SHARED_STATE_MIGRATION in caplog.text


def test_postgres_missing_column_raises() -> None:
    columns = _full_columns()
    columns["shared_sessions"].remove("version")
    with (
        patch.object(SharedSQLStateStore, "_create_engine", return_value=_fake_postgres_engine()),
        patch.object(shared_sql_state, "sa_inspect", return_value=_fake_inspector(columns)),
        pytest.raises(SharedStateSchemaError, match="shared_sessions missing columns version"),
    ):
        SharedSQLStateStore("postgresql+psycopg://user:pw@db.example.com/app")


@pytest.mark.skipif(
    not os.getenv("EVENTRELAY_TEST_POSTGRES_URL"),
    reason=(
        "set EVENTRELAY_TEST_POSTGRES_URL to a throwaway Postgres (superuser, with "
        "anon, authenticated and service_role roles) to run"
    ),
)
def test_real_postgres_requires_migration_then_works() -> None:
    from pathlib import Path

    url = shared_sql_state.normalize_shared_storage_url(os.environ["EVENTRELAY_TEST_POSTGRES_URL"])
    engine = create_engine(url)
    with engine.begin() as conn:
        for table in SHARED_TABLES:
            conn.exec_driver_sql(f"drop table if exists public.{table} cascade")
    with pytest.raises(SharedStateSchemaError):
        SharedSQLStateStore(url)

    migration = Path(__file__).resolve().parents[2] / SHARED_STATE_MIGRATION
    with engine.begin() as conn:
        conn.exec_driver_sql(migration.read_text(encoding="utf-8"))
    store = SharedSQLStateStore(url)
    store.save_session({"id": "pg1"})
    assert store.get_session("pg1") == {"id": "pg1", "timeline": []}
    engine.dispose()
    store.engine.dispose()
