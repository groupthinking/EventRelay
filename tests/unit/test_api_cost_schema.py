"""Contract tests for the shared API-cost PostgreSQL schema."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, DateTime, UniqueConstraint

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS = REPO_ROOT / "src/youtube_extension/backend/migrations/versions"


def _load_revision(filename: str, module_name: str):
    path = VERSIONS / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_api_cost_models_share_the_canonical_base() -> None:
    from youtube_extension.backend.config.database import Base as DatabaseBase
    from youtube_extension.backend.models.api_cost import (
        APIUsage,
        DailyBudget,
        WebhookOutbox,
    )
    from youtube_extension.backend.models.base import Base as ModelBase

    assert DatabaseBase is ModelBase
    assert APIUsage.metadata is DatabaseBase.metadata
    assert DailyBudget.metadata is DatabaseBase.metadata
    assert WebhookOutbox.metadata is DatabaseBase.metadata


def test_api_cost_models_define_durable_outbox_contract() -> None:
    from youtube_extension.backend.models.api_cost import APIUsage, WebhookOutbox

    assert APIUsage.__table__.columns.timestamp.nullable is False

    columns = WebhookOutbox.__table__.columns
    assert set(columns.keys()) == {
        "id",
        "utc_date",
        "alert_type",
        "status",
        "retry_count",
        "last_attempt",
        "next_attempt_at",
        "claimed_at",
        "claim_token",
        "last_recovered_at",
        "sent_at",
        "error_message",
        "current_cost",
        "payload",
    }

    for name in (
        "last_attempt",
        "next_attempt_at",
        "claimed_at",
        "last_recovered_at",
        "sent_at",
    ):
        assert isinstance(columns[name].type, DateTime)
        assert columns[name].type.timezone is True

    assert columns.status.server_default is not None
    assert columns.retry_count.server_default is not None
    assert columns.next_attempt_at.default is None
    assert columns.next_attempt_at.server_default is None
    assert columns.next_attempt_at.nullable is True

    constraints = WebhookOutbox.__table__.constraints
    assert any(
        isinstance(item, UniqueConstraint)
        and tuple(column.name for column in item.columns) == ("utc_date", "alert_type")
        for item in constraints
    )
    constraint_names = {
        item.name for item in constraints if isinstance(item, CheckConstraint)
    }
    assert constraint_names >= {
        "ck_webhook_outbox_status",
        "ck_webhook_outbox_retry_count_nonnegative",
    }

    indexes = {
        item.name: tuple(column.name for column in item.columns)
        for item in WebhookOutbox.__table__.indexes
    }
    assert indexes["ix_webhook_outbox_due"] == (
        "status",
        "next_attempt_at",
        "retry_count",
        "id",
    )
    assert indexes["ix_webhook_outbox_stale_claims"] == (
        "status",
        "claimed_at",
        "id",
    )


def test_root_alembic_config_is_the_only_entrypoint() -> None:
    config = (REPO_ROOT / "alembic.ini").read_text(encoding="utf-8")

    assert "script_location = src/youtube_extension/backend/migrations" in config
    assert "prepend_sys_path = src" in config
    assert not (REPO_ROOT / "src/youtube_extension/backend/alembic.ini").exists()


def test_alembic_environment_uses_sync_psycopg_and_scoped_metadata() -> None:
    source = (REPO_ROOT / "src/youtube_extension/backend/migrations/env.py").read_text(
        encoding="utf-8"
    )

    assert "create_async_engine" not in source
    assert "asyncio.run" not in source
    assert "postgresql+psycopg" in source
    assert "from youtube_extension.backend.models import *" not in source
    assert "API_COST_TABLES" in source
    assert "include_object=include_object" in source
    assert 'config.get_main_option("sqlalchemy.url")' in source
    assert "search_path=public" in source


def test_psycopg_is_a_required_runtime_dependency() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert '"psycopg[binary]>=3.2,<4"' in pyproject
    assert "psycopg[binary]>=3.2,<4" in requirements


def test_canonical_sync_database_url_uses_psycopg3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from youtube_extension.backend.config.database import DatabaseSettings

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:secret@db/eventrelay")
    settings = DatabaseSettings()

    assert (
        settings.sync_database_url == "postgresql+psycopg://user:secret@db/eventrelay"
    )


def test_postgres_ci_exercises_the_full_migration_matrix() -> None:
    workflow = (REPO_ROOT / ".github/workflows/api-cost-postgres.yml").read_text(
        encoding="utf-8"
    )

    assert "postgres:16" in workflow
    assert "fresh" in workflow
    assert "from-002" in workflow
    assert "round-trip" in workflow
    assert workflow.count("python -m youtube_extension.backend.api_cost_migrate") >= 2
    assert "alembic check" in workflow
    assert "tests/integration/test_api_cost_postgres.py" in workflow


def test_revision_002_handles_optional_roles_on_vanilla_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = _load_revision(
        "20260107_0057_002_secure_alembic_secure_alembic_version_table.py",
        "api_cost_revision_002",
    )
    statements: list[str] = []
    monkeypatch.setattr(revision.op, "execute", statements.append)

    revision.upgrade()

    rendered = "\n".join(statements)
    assert "REVOKE ALL ON public.alembic_version FROM PUBLIC" in rendered
    assert "IF EXISTS" in rendered
    assert "rolname = 'anon'" in rendered
    assert "rolname = 'authenticated'" in rendered
    assert "FROM PUBLIC, anon, authenticated" not in rendered


def test_revision_003_creates_the_compatible_api_cost_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = _load_revision(
        "20260718_0001_003_api_cost_postgres_substrate.py",
        "api_cost_revision_003",
    )
    tables: dict[str, tuple[object, ...]] = {}
    indexes: dict[str, tuple[str, tuple[str, ...], bool]] = {}

    def create_table(name: str, *items: object, **_: object) -> None:
        tables[name] = items

    def create_index(
        name: str,
        table: str,
        columns: list[str],
        unique: bool = False,
        **_: object,
    ) -> None:
        indexes[name] = (table, tuple(columns), unique)

    monkeypatch.setattr(revision.op, "create_table", create_table)
    monkeypatch.setattr(revision.op, "create_index", create_index)

    revision.upgrade()

    assert set(tables) == {"api_usage", "daily_budgets", "webhook_outbox"}
    outbox_columns = {
        item.name: item for item in tables["webhook_outbox"] if hasattr(item, "type")
    }
    assert set(outbox_columns) == {
        "id",
        "utc_date",
        "alert_type",
        "status",
        "retry_count",
        "last_attempt",
        "next_attempt_at",
        "claimed_at",
        "claim_token",
        "last_recovered_at",
        "sent_at",
        "error_message",
        "current_cost",
        "payload",
    }
    usage_columns = {
        item.name: item for item in tables["api_usage"] if hasattr(item, "type")
    }
    assert usage_columns["timestamp"].nullable is False
    # ``NULL`` means immediately due for pending rows and no future attempt for
    # terminal rows, matching the delivery state-machine contract in #869.
    assert outbox_columns["next_attempt_at"].nullable is True
    assert outbox_columns["next_attempt_at"].server_default is None
    assert outbox_columns["next_attempt_at"].type.timezone is True
    assert indexes["ix_webhook_outbox_due"] == (
        "webhook_outbox",
        ("status", "next_attempt_at", "retry_count", "id"),
        False,
    )
    assert indexes["ix_webhook_outbox_stale_claims"] == (
        "webhook_outbox",
        ("status", "claimed_at", "id"),
        False,
    )


def test_revision_003_is_deterministic_and_has_no_environment_grants() -> None:
    source = (VERSIONS / "20260718_0001_003_api_cost_postgres_substrate.py").read_text(
        encoding="utf-8"
    )

    assert "os.getenv" not in source
    assert "API_COST_RUNTIME_DB_ROLE" not in source
    assert "GRANT " not in source
