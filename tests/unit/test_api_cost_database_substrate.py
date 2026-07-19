"""Production-safety tests for the API-cost runtime database substrate."""

from __future__ import annotations

import asyncio
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

from youtube_extension.backend.config.database import Base
from youtube_extension.backend.services import api_cost_monitor as monitor_module
from youtube_extension.backend.services.api_cost_monitor import (
    APICostMonitor,
    APIUsage,
    DailyBudget,
    WebhookOutbox,
)

PRODUCTION_ENV_KEYS = (
    "ENVIRONMENT",
    "VERCEL_ENV",
    "DATABASE_URL",
    "API_COST_DATABASE_URL",
    "API_COST_MONITOR_DB_PATH",
    "API_COST_TRACKING",
    "API_COST_DELIVERY_ENABLED",
    "API_COST_WEBHOOK_URL",
    "API_COST_RUNTIME_DB_ROLE",
    "CLOUD_SQL_INSTANCE_CONNECTION_NAME",
)


@pytest.fixture(autouse=True)
def clean_runtime_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in PRODUCTION_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_api_cost_models_use_canonical_base() -> None:
    assert APIUsage.metadata is Base.metadata
    assert DailyBudget.metadata is Base.metadata
    assert WebhookOutbox.metadata is Base.metadata


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("ENVIRONMENT", "staging"),
        ("ENVIRONMENT", "prod"),
        ("ENVIRONMENT", "production"),
        ("VERCEL_ENV", "production"),
    ),
)
def test_production_tracking_fails_closed_without_database_url(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    monkeypatch.setenv(key, value)
    monkeypatch.setenv("API_COST_TRACKING", "true")

    with pytest.raises(RuntimeError, match="PostgreSQL.*required"):
        APICostMonitor()


def test_production_delivery_fails_closed_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_COST_TRACKING", "false")
    monkeypatch.setenv("API_COST_DELIVERY_ENABLED", "true")

    with pytest.raises(RuntimeError, match="tracking or delivery"):
        APICostMonitor()


@pytest.mark.parametrize("url", ("sqlite://", "sqlite:////tmp/api-cost.db"))
def test_production_rejects_sqlite(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="PostgreSQL.*required"):
        APICostMonitor(database_url=url)


def test_production_rejects_database_url_outside_attached_cloud_sql_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_COST_RUNTIME_DB_ROLE", "api_cost_runtime")
    monkeypatch.setenv(
        "CLOUD_SQL_INSTANCE_CONNECTION_NAME", "project:us-central1:eventrelay"
    )

    with pytest.raises(RuntimeError, match="Cloud SQL Unix socket"):
        APICostMonitor(database_url="postgresql://user:pass@10.0.0.2/costs")


def test_production_tracking_requires_cloud_sql_attachment_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_COST_TRACKING", "true")
    monkeypatch.setenv("API_COST_RUNTIME_DB_ROLE", "api_cost_runtime")

    with pytest.raises(RuntimeError, match="CLOUD_SQL_INSTANCE_CONNECTION_NAME"):
        APICostMonitor(database_url="postgresql://user:pass@10.0.0.2/costs")


def test_production_accepts_attached_cloud_sql_socket_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_COST_RUNTIME_DB_ROLE", "api_cost_runtime")
    monkeypatch.setenv(
        "CLOUD_SQL_INSTANCE_CONNECTION_NAME", "project:us-central1:eventrelay"
    )
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    monkeypatch.setattr(monitor_module, "create_engine", lambda *args, **kwargs: engine)

    monitor = APICostMonitor(
        database_url=(
            "postgresql://user:pass@/costs"
            "?host=/cloudsql/project:us-central1:eventrelay"
        )
    )

    assert monitor.engine is engine


def test_production_tracking_requires_expected_runtime_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv(
        "CLOUD_SQL_INSTANCE_CONNECTION_NAME", "project:us-central1:eventrelay"
    )

    with pytest.raises(RuntimeError, match="API_COST_RUNTIME_DB_ROLE"):
        APICostMonitor(
            database_url=(
                "postgresql://user:pass@/costs"
                "?host=/cloudsql/project:us-central1:eventrelay"
            )
        )


def test_tracking_disabled_can_import_without_a_production_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("API_COST_TRACKING", "false")

    monitor = APICostMonitor()

    assert monitor.engine is None


def test_nonproduction_sqlite_requires_explicit_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_database = tmp_path / "default-costs.db"
    monkeypatch.setattr(monitor_module, "DEFAULT_DB_PATH", str(local_database))

    monitor = APICostMonitor()

    assert monitor.engine is None
    assert not local_database.exists()

    explicit = APICostMonitor(db_path=str(local_database))

    assert explicit.engine is not None
    assert local_database.exists()
    explicit.engine.dispose()


def test_invalid_tracking_flag_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_COST_TRACKING", "treu")

    with pytest.raises(RuntimeError, match="API_COST_TRACKING.*true or false"):
        APICostMonitor()


@pytest.mark.parametrize(
    ("incoming", "normalized"),
    (
        ("postgres://user:pass@db/costs", "postgresql+psycopg://user:***@db/costs"),
        ("postgresql://user:pass@db/costs", "postgresql+psycopg://user:***@db/costs"),
        (
            "postgresql+asyncpg://user:pass@db/costs",
            "postgresql+psycopg://user:***@db/costs",
        ),
    ),
)
def test_postgres_urls_use_psycopg(
    monkeypatch: pytest.MonkeyPatch, incoming: str, normalized: str
) -> None:
    captured: dict[str, object] = {}

    def fake_create_engine(url: object, **kwargs: object) -> MagicMock:
        captured["url"] = url
        captured["kwargs"] = kwargs
        engine = MagicMock()
        engine.url = url
        engine.dialect.name = "postgresql"
        return engine

    monkeypatch.setattr(monitor_module, "create_engine", fake_create_engine)

    monitor = APICostMonitor(database_url=incoming)

    assert monitor.database_url.render_as_string(hide_password=True) == normalized
    assert captured["url"].drivername == "postgresql+psycopg"


def test_postgres_pool_is_bounded_and_has_connection_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_create_engine(url: object, **kwargs: object) -> MagicMock:
        captured.update(kwargs)
        engine = MagicMock()
        engine.url = url
        engine.dialect.name = "postgresql"
        return engine

    monkeypatch.setattr(monitor_module, "create_engine", fake_create_engine)
    monkeypatch.setenv("API_COST_DB_POOL_SIZE", "3")
    monkeypatch.setenv("API_COST_DB_MAX_OVERFLOW", "1")

    APICostMonitor(database_url="postgresql://user:pass@db/costs")

    assert captured["pool_size"] == 3
    assert captured["max_overflow"] == 1
    assert captured["pool_pre_ping"] is True
    assert captured["pool_timeout"] > 0
    assert captured["connect_args"]["connect_timeout"] > 0
    assert "statement_timeout" in captured["connect_args"]["options"]
    assert "timezone=UTC" in captured["connect_args"]["options"]
    assert "search_path=public" in captured["connect_args"]["options"]


def test_postgres_runtime_never_creates_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_all = MagicMock()
    monkeypatch.setattr(Base.metadata, "create_all", create_all)
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    monkeypatch.setattr(monitor_module, "create_engine", lambda *a, **k: engine)

    APICostMonitor(database_url="postgresql://user:pass@db/costs")

    create_all.assert_not_called()


def test_postgres_schema_readiness_validates_constraints_and_worker_indexes() -> None:
    statements: list[str] = []
    checks = {
        "column_contract": True,
        "api_usage_primary_key": True,
        "daily_budgets_primary_key": True,
        "webhook_outbox_primary_key": True,
        "outbox_alert_uniqueness": True,
        "check_definitions": True,
        "outbox_due_index": True,
        "outbox_stale_claims_index": True,
    }

    class Result:
        def mappings(self) -> Result:
            return self

        def one(self) -> dict[str, bool]:
            return checks

    class Connection:
        def execute(self, statement: object) -> Result:
            statements.append(str(statement))
            return Result()

    @contextmanager
    def connect() -> object:
        yield Connection()

    monitor = object.__new__(APICostMonitor)
    monitor.engine = MagicMock()
    monitor.engine.connect = connect
    monitor._is_postgres = True

    monitor._validate_database_schema()

    sql = "\n".join(statements).lower()
    assert "public.api_usage" in sql
    assert "public.daily_budgets" in sql
    assert "public.webhook_outbox" in sql
    assert "pg_constraint" in sql
    assert "pg_attribute" in sql
    assert "pg_attrdef" in sql
    assert "format_type" in sql
    assert "pg_get_expr" in sql
    assert "pg_get_constraintdef" in sql
    assert "pg_index" in sql
    assert "uq_utc_date_alert_type" in sql
    assert "ix_webhook_outbox_due" in sql
    assert "ix_webhook_outbox_stale_claims" in sql


def test_postgres_schema_readiness_rejects_malformed_contract() -> None:
    class Result:
        def mappings(self) -> Result:
            return self

        def one(self) -> dict[str, bool]:
            return {
                "column_contract": True,
                "api_usage_primary_key": True,
                "daily_budgets_primary_key": True,
                "webhook_outbox_primary_key": True,
                "outbox_alert_uniqueness": True,
                "check_definitions": True,
                "outbox_due_index": False,
                "outbox_stale_claims_index": True,
            }

    class Connection:
        def execute(self, _statement: object) -> Result:
            return Result()

    @contextmanager
    def connect() -> object:
        yield Connection()

    monitor = object.__new__(APICostMonitor)
    monitor.engine = MagicMock()
    monitor.engine.connect = connect
    monitor._is_postgres = True

    with pytest.raises(RuntimeError, match="outbox_due_index"):
        monitor._validate_database_schema()


@pytest.mark.parametrize("failed_check", ["column_contract", "check_definitions"])
def test_postgres_schema_readiness_rejects_column_or_check_drift(
    failed_check: str,
) -> None:
    checks = {
        "column_contract": True,
        "api_usage_primary_key": True,
        "daily_budgets_primary_key": True,
        "webhook_outbox_primary_key": True,
        "outbox_alert_uniqueness": True,
        "check_definitions": True,
        "outbox_due_index": True,
        "outbox_stale_claims_index": True,
    }
    checks[failed_check] = False

    class Result:
        def mappings(self) -> Result:
            return self

        def one(self) -> dict[str, bool]:
            return checks

    class Connection:
        def execute(self, _statement: object) -> Result:
            return Result()

    @contextmanager
    def connect() -> object:
        yield Connection()

    monitor = object.__new__(APICostMonitor)
    monitor.engine = MagicMock()
    monitor.engine.connect = connect
    monitor._is_postgres = True

    with pytest.raises(RuntimeError, match=failed_check):
        monitor._validate_database_schema()


def test_local_sqlite_only_creates_api_cost_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_all = MagicMock()
    monkeypatch.setattr(Base.metadata, "create_all", create_all)
    monkeypatch.setattr(APICostMonitor, "_validate_database_schema", lambda self: None)

    monitor = APICostMonitor(db_path=str(tmp_path / "costs.db"))

    create_all.assert_called_once_with(
        monitor.engine,
        tables=[APIUsage.__table__, DailyBudget.__table__, WebhookOutbox.__table__],
    )


def test_in_memory_sqlite_uses_one_shared_connection() -> None:
    monitor = APICostMonitor(db_path=":memory:")

    assert isinstance(monitor.engine.pool, StaticPool)


def test_legacy_sqlite_outbox_fails_with_recovery_instruction(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute("""
            CREATE TABLE webhook_outbox (
                id INTEGER PRIMARY KEY,
                utc_date VARCHAR NOT NULL,
                alert_type VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                retry_count INTEGER NOT NULL,
                last_attempt DATETIME,
                error_message VARCHAR,
                current_cost FLOAT NOT NULL,
                payload VARCHAR
            )
            """)

    with pytest.raises(RuntimeError, match="back up and recreate"):
        APICostMonitor(db_path=str(database))


def test_postgres_readiness_checks_schema_and_effective_runtime_privileges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[str] = []
    parameters: list[dict[str, object]] = []

    checks = {
        "expected_role_member": True,
        "login_role": True,
        "inherits_privileges": True,
        "non_elevated": True,
        "only_expected_parent_role": True,
        "group_nologin": True,
        "group_non_elevated": True,
        "group_no_parent_roles": True,
        "schema_usage": True,
        "no_schema_create": True,
        "no_database_create": True,
        "no_database_ownership": True,
        "no_target_ownership": True,
        "no_unexpected_schema_access": True,
        "no_unexpected_table_access": True,
        "no_unexpected_sequence_access": True,
        "required_table_dml": True,
        "no_unsafe_table_privileges": True,
        "required_sequence_access": True,
        "no_unsafe_sequence_privileges": True,
        "no_alembic_access": True,
    }

    class Result:
        def mappings(self) -> Result:
            return self

        def one(self) -> dict[str, bool]:
            return checks

    class Connection:
        def execute(
            self, statement: object, values: dict[str, object] | None = None
        ) -> Result:
            statements.append(str(statement))
            parameters.append(values or {})
            return Result()

    @contextmanager
    def connect() -> object:
        yield Connection()

    engine = MagicMock()
    engine.dialect.name = "postgresql"
    engine.connect = connect
    monkeypatch.setattr(monitor_module, "create_engine", lambda *a, **k: engine)
    monkeypatch.setenv("API_COST_RUNTIME_DB_ROLE", "api_cost_runtime")
    monitor = APICostMonitor(database_url="postgresql://user:pass@db/costs")
    monkeypatch.setattr(monitor, "_validate_database_schema", lambda: None)

    monitor.ensure_database_ready()

    sql = "\n".join(statements).lower()
    assert "api_usage" in sql
    assert "daily_budgets" in sql
    assert "webhook_outbox" in sql
    assert "pg_has_role" in sql
    assert "pg_auth_members" in sql
    assert "rolsuper" in sql
    assert "rolbypassrls" in sql
    assert "runtime_group.rolcanlogin" in sql
    assert "has_database_privilege" in sql
    assert "relowner" in sql
    assert "has_table_privilege" in sql
    assert "has_sequence_privilege" in sql
    assert "no_unexpected_schema_access" in sql
    assert "no_unexpected_table_access" in sql
    assert "no_unexpected_sequence_access" in sql
    assert all(
        operation in sql
        for operation in (
            "select",
            "insert",
            "update",
            "delete",
            "truncate",
            "references",
            "trigger",
        )
    )
    assert "alembic_version" in sql
    assert parameters == [{"runtime_role": "api_cost_runtime"}]


def test_postgres_readiness_fails_when_any_effective_privilege_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = {
        "expected_role_member": True,
        "login_role": True,
        "inherits_privileges": True,
        "non_elevated": True,
        "only_expected_parent_role": True,
        "group_nologin": True,
        "group_non_elevated": True,
        "group_no_parent_roles": True,
        "schema_usage": True,
        "no_schema_create": True,
        "no_database_create": True,
        "no_database_ownership": True,
        "no_target_ownership": True,
        "no_unexpected_schema_access": True,
        "no_unexpected_table_access": True,
        "no_unexpected_sequence_access": True,
        "required_table_dml": False,
        "no_unsafe_table_privileges": True,
        "required_sequence_access": True,
        "no_unsafe_sequence_privileges": True,
        "no_alembic_access": True,
    }

    class Result:
        def mappings(self) -> Result:
            return self

        def one(self) -> dict[str, bool]:
            return checks

    class Connection:
        def execute(
            self, statement: object, values: dict[str, object] | None = None
        ) -> Result:
            return Result()

    @contextmanager
    def connect() -> object:
        yield Connection()

    engine = MagicMock()
    engine.dialect.name = "postgresql"
    engine.connect = connect
    monkeypatch.setattr(monitor_module, "create_engine", lambda *a, **k: engine)
    monkeypatch.setenv("API_COST_RUNTIME_DB_ROLE", "api_cost_runtime")
    monitor = APICostMonitor(database_url="postgresql://user:pass@db/costs")
    monkeypatch.setattr(monitor, "_validate_database_schema", lambda: None)

    with pytest.raises(RuntimeError, match="required_table_dml"):
        monitor.ensure_database_ready()


def test_daily_cost_uses_indexable_utc_timestamp_bounds(tmp_path: Path) -> None:
    monitor = APICostMonitor(db_path=str(tmp_path / "costs.db"))
    statements: list[str] = []
    bound_values: list[object] = []

    def capture_sql(
        _connection: object,
        _cursor: object,
        statement: str,
        parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)
        if isinstance(parameters, tuple):
            bound_values.extend(parameters)

    event.listen(monitor.engine, "before_cursor_execute", capture_sql)
    try:
        assert monitor._get_daily_cost_sync("2026-07-18") == 0.0
    finally:
        event.remove(monitor.engine, "before_cursor_execute", capture_sql)

    sql = "\n".join(statements).lower()
    assert "date(" not in sql
    assert "timestamp >=" in sql
    assert "timestamp <" in sql
    assert len(bound_values) == 2
    start_at, end_at = monitor._utc_day_bounds("2026-07-18")
    assert isinstance(start_at, datetime)
    assert isinstance(end_at, datetime)
    assert start_at.tzinfo is not None
    assert end_at.tzinfo is not None
    assert (end_at - start_at).total_seconds() == 86400


async def test_record_usage_offloads_sync_database_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monitor = APICostMonitor(db_path=str(tmp_path / "costs.db"))
    original_to_thread = asyncio.to_thread
    calls: list[str] = []

    async def tracking_to_thread(
        function: object, *args: object, **kwargs: object
    ) -> object:
        calls.append(function.__name__)
        return await original_to_thread(function, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", tracking_to_thread)

    await monitor.record_usage("openai", "/chat", 100, model="gpt-4o")

    assert "_record_usage_sync" in calls
    assert "_get_daily_cost_sync" in calls


async def test_telemetry_database_failure_does_not_fail_paid_api_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monitor = APICostMonitor(db_path=str(tmp_path / "costs.db"))

    def fail_recording(*args: object, **kwargs: object) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(monitor, "_record_usage_sync", fail_recording)

    record = await monitor.record_usage("openai", "/chat", 100, model="gpt-4o")

    assert record.service == "openai"
    assert record.tokens_used == 100


async def test_outbox_processing_respects_requested_batch_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monitor = APICostMonitor(db_path=str(tmp_path / "costs.db"))
    monitor.webhook_url = "https://example.test/webhook"
    for day in ("2026-07-18", "2026-07-19", "2026-07-20"):
        assert monitor._claim_alert(day, "threshold", 9.0)

    async def successful_delivery(message: str) -> bool:
        return True

    monkeypatch.setattr(monitor, "_send_webhook_notification", successful_delivery)

    await monitor.process_outbox(max_items=2)

    with monitor._session_scope() as session:
        statuses = [
            row[0]
            for row in session.query(WebhookOutbox.status)
            .order_by(WebhookOutbox.id)
            .all()
        ]
    assert statuses == ["sent", "sent", "pending"]


async def test_api_alert_trigger_never_starts_in_process_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monitor = APICostMonitor(db_path=str(tmp_path / "costs.db"))
    process_outbox = MagicMock()
    monkeypatch.setattr(monitor, "process_outbox", process_outbox)

    monitor._trigger_delivery()
    await asyncio.sleep(0)

    process_outbox.assert_not_called()


async def test_missing_webhook_does_not_claim_or_consume_outbox_attempt(
    tmp_path: Path,
) -> None:
    monitor = APICostMonitor(db_path=str(tmp_path / "costs.db"))
    assert monitor.webhook_url is None
    assert monitor._claim_alert("2026-07-18", "threshold", 9.0)

    await monitor.process_outbox(max_items=1)

    with monitor._session_scope() as session:
        item = session.query(WebhookOutbox).one()
        assert item.status == "pending"
        assert item.retry_count == 0


async def test_disabled_delivery_never_claims_even_with_stale_webhook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("API_COST_DELIVERY_ENABLED", "false")
    monkeypatch.setenv("API_COST_WEBHOOK_URL", "https://stale.example.test/webhook")
    monitor = APICostMonitor(db_path=str(tmp_path / "costs.db"))
    assert monitor._claim_alert("2026-07-18", "threshold", 9.0)

    await monitor.process_outbox(max_items=1)

    with monitor._session_scope() as session:
        item = session.query(WebhookOutbox).one()
        assert item.status == "pending"
        assert item.retry_count == 0


async def test_public_readiness_helper_offloads_sync_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = MagicMock()
    monkeypatch.setattr(monitor_module, "get_cost_monitor", lambda: monitor)
    calls: list[object] = []

    async def fake_to_thread(function: object, *args: object, **kwargs: object) -> None:
        calls.append(function)
        function(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    await monitor_module.ensure_api_cost_database_ready()

    assert calls == [monitor.ensure_database_ready]
    monitor.ensure_database_ready.assert_called_once_with()


async def test_delivery_only_readiness_still_checks_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = MagicMock()
    monitor.cost_tracking_enabled = False
    monitor.delivery_enabled = True
    monkeypatch.setattr(monitor_module, "get_cost_monitor", lambda: monitor)

    await monitor_module.ensure_api_cost_database_ready()

    monitor.ensure_database_ready.assert_called_once_with()
