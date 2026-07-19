"""Tests for the deployment-only API-cost migration/grant runner."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest


def test_normalize_database_url_requires_postgres_and_psycopg() -> None:
    from youtube_extension.backend.api_cost_migrate import normalize_database_url

    assert (
        normalize_database_url("postgres://user:pass@db/app")
        == "postgresql+psycopg://user:pass@db/app"
    )
    assert (
        normalize_database_url("postgresql+asyncpg://user:pass@db/app")
        == "postgresql+psycopg://user:pass@db/app"
    )
    assert (
        normalize_database_url("postgresql+psycopg2://user:pass@db/app")
        == "postgresql+psycopg://user:pass@db/app"
    )
    with pytest.raises(ValueError, match="PostgreSQL"):
        normalize_database_url("sqlite:///tmp.db")


@pytest.mark.parametrize(
    "role",
    ["", "has-dash", "has space", "1starts_with_digit", "a" * 64],
)
def test_runtime_role_must_be_a_plain_postgres_identifier(role: str) -> None:
    from youtube_extension.backend.api_cost_migrate import validate_runtime_role

    with pytest.raises(ValueError, match="runtime database role"):
        validate_runtime_role(role)


def test_runtime_grants_revoke_public_schema_create_and_limit_dml() -> None:
    from youtube_extension.backend import api_cost_migrate

    statements = api_cost_migrate.runtime_grant_statements("eventrelay_api_runtime")
    rendered = "\n".join(statements)

    assert "REVOKE CREATE ON SCHEMA public FROM PUBLIC" in rendered
    assert 'REVOKE CREATE ON SCHEMA public FROM "eventrelay_api_runtime"' in rendered
    assert (
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
        "public.api_usage, public.daily_budgets, public.webhook_outbox "
        'TO "eventrelay_api_runtime"'
    ) in rendered
    assert (
        "GRANT USAGE, SELECT ON SEQUENCE public.api_usage_id_seq, "
        'public.webhook_outbox_id_seq TO "eventrelay_api_runtime"'
    ) in rendered
    assert (
        'REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM "eventrelay_api_runtime"'
        in rendered
    )
    assert "ALL TABLES" not in rendered
    assert "ALL SEQUENCES" not in rendered

    source = Path(api_cost_migrate.__file__).read_text(encoding="utf-8")
    assert '("TRUNCATE", "REFERENCES", "TRIGGER")' in source
    assert '_UNSAFE_SEQUENCE_PRIVILEGES = ("UPDATE",)' in source
    assert "ANY(:tables)" not in source


def test_database_create_revoke_quotes_database_and_role() -> None:
    from youtube_extension.backend.api_cost_migrate import (
        database_create_revoke_statement,
    )

    assert (
        database_create_revoke_statement('event"relay', "eventrelay_api_runtime")
        == 'REVOKE CREATE ON DATABASE "event""relay" FROM "eventrelay_api_runtime"'
    )


def test_migration_database_url_must_match_attached_cloud_sql_socket() -> None:
    from youtube_extension.backend.api_cost_migrate import (
        validate_cloud_sql_database_url,
    )

    instance = "project:us-central1:eventrelay"
    validate_cloud_sql_database_url(
        "postgresql://ddl:secret@/eventrelay"
        "?host=/cloudsql/project:us-central1:eventrelay",
        instance,
    )

    with pytest.raises(RuntimeError, match="attached Cloud SQL Unix socket"):
        validate_cloud_sql_database_url(
            "postgresql://ddl:secret@10.0.0.2/eventrelay", instance
        )
    with pytest.raises(RuntimeError, match="attached Cloud SQL Unix socket"):
        validate_cloud_sql_database_url(
            "postgresql://ddl:secret@/eventrelay"
            "?host=/cloudsql/project:us-central1:other",
            instance,
        )
    with pytest.raises(RuntimeError, match="attached Cloud SQL Unix socket"):
        validate_cloud_sql_database_url(
            "postgresql://ddl:secret@unexpected/eventrelay"
            "?host=/cloudsql/project:us-central1:eventrelay",
            instance,
        )


def test_migrations_finish_before_runtime_grants(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from youtube_extension.backend import api_cost_migrate

    events: list[str] = []

    class FakeConnection:
        pass

    class FakeEngine:
        @contextmanager
        def begin(self):
            events.append("begin-grants")
            yield FakeConnection()

        def dispose(self) -> None:
            events.append("dispose")

    monkeypatch.setattr(
        api_cost_migrate.command,
        "upgrade",
        lambda _config, revision: events.append(f"upgrade-{revision}"),
    )
    monkeypatch.setattr(
        api_cost_migrate,
        "create_engine",
        lambda *_args, **_kwargs: FakeEngine(),
    )
    monkeypatch.setattr(
        api_cost_migrate,
        "apply_runtime_grants",
        lambda _connection, role: events.append(f"grant-{role}"),
    )

    api_cost_migrate.migrate_and_grant(
        "postgresql://ddl:secret@db/app",
        "eventrelay_api_runtime",
        config_path=tmp_path / "alembic.ini",
    )

    assert events == [
        "upgrade-head",
        "begin-grants",
        "grant-eventrelay_api_runtime",
        "dispose",
    ]


def test_migration_grants_pin_public_search_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from youtube_extension.backend import api_cost_migrate

    captured: dict[str, object] = {}

    class FakeEngine:
        @contextmanager
        def begin(self):
            yield object()

        def dispose(self) -> None:
            pass

    monkeypatch.setattr(api_cost_migrate.command, "upgrade", lambda *_: None)

    def fake_create_engine(*_args: object, **kwargs: object) -> FakeEngine:
        captured.update(kwargs)
        return FakeEngine()

    monkeypatch.setattr(api_cost_migrate, "create_engine", fake_create_engine)
    monkeypatch.setattr(api_cost_migrate, "apply_runtime_grants", lambda *_: None)

    api_cost_migrate.migrate_and_grant(
        "postgresql://ddl:secret@db/app",
        "eventrelay_api_runtime",
        config_path=tmp_path / "alembic.ini",
    )

    assert "search_path=public" in captured["connect_args"]["options"]


def test_apply_runtime_grants_fails_for_elevated_or_missing_role() -> None:
    from youtube_extension.backend.api_cost_migrate import apply_runtime_grants

    missing = Mock()
    missing.execute.return_value.mappings.return_value.one_or_none.return_value = None
    with pytest.raises(RuntimeError, match="does not exist"):
        apply_runtime_grants(missing, "eventrelay_api_runtime")

    elevated = Mock()
    elevated.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "rolname": "eventrelay_api_runtime",
        "rolsuper": True,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolreplication": False,
        "rolbypassrls": False,
    }
    with pytest.raises(RuntimeError, match="elevated"):
        apply_runtime_grants(elevated, "eventrelay_api_runtime")


def test_apply_runtime_grants_requires_a_stable_nologin_group() -> None:
    from youtube_extension.backend.api_cost_migrate import apply_runtime_grants

    login_role = Mock()
    login_role.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "rolname": "eventrelay_api_runtime",
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolreplication": False,
        "rolbypassrls": False,
        "rolcanlogin": True,
    }

    with pytest.raises(RuntimeError, match="NOLOGIN group"):
        apply_runtime_grants(login_role, "eventrelay_api_runtime")


def test_apply_runtime_grants_rejects_parent_role_memberships() -> None:
    from youtube_extension.backend.api_cost_migrate import apply_runtime_grants

    role_result = Mock()
    role_result.mappings.return_value.one_or_none.return_value = {
        "rolname": "eventrelay_api_runtime",
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolreplication": False,
        "rolbypassrls": False,
        "rolcanlogin": False,
    }
    parent_result = Mock()
    parent_result.scalar_one.return_value = True
    connection = Mock()
    connection.execute.side_effect = [role_result, parent_result]

    with pytest.raises(RuntimeError, match="must not inherit from parent roles"):
        apply_runtime_grants(connection, "eventrelay_api_runtime")


def test_apply_runtime_grants_verifies_every_required_dml_privilege() -> None:
    from youtube_extension.backend.api_cost_migrate import apply_runtime_grants

    class Result:
        def __init__(self, scalar=None, row=None):
            self._scalar = scalar
            self._row = row

        def mappings(self):
            return self

        def one_or_none(self):
            return self._row

        def scalar_one(self):
            return self._scalar

    class Connection:
        def execute(self, statement, params=None):
            sql = str(statement)
            params = params or {}
            if "FROM pg_roles" in sql:
                return Result(
                    row={
                        "rolname": "eventrelay_api_runtime",
                        "rolsuper": False,
                        "rolcreatedb": False,
                        "rolcreaterole": False,
                        "rolreplication": False,
                        "rolbypassrls": False,
                        "rolcanlogin": False,
                    }
                )
            if sql == "SELECT current_user":
                return Result(scalar="api_cost_ddl")
            if sql == "SELECT current_database()":
                return Result(scalar="eventrelay")
            if "has_database_privilege" in sql:
                return Result(scalar=False)
            if "has_schema_privilege" in sql or "SELECT EXISTS" in sql:
                return Result(scalar=False)
            if "has_table_privilege" in sql:
                if params.get("privilege") == "DELETE":
                    return Result(scalar=False)
                return Result(scalar=True)
            if "has_sequence_privilege" in sql:
                return Result(scalar=True)
            return Result()

    with pytest.raises(RuntimeError, match="lacks DELETE"):
        apply_runtime_grants(Connection(), "eventrelay_api_runtime")


def test_main_requires_both_deployment_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    from youtube_extension.backend.api_cost_migrate import main

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_COST_RUNTIME_DB_ROLE", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        main()


def test_main_requires_cloud_sql_attachment_in_deployed_environments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from youtube_extension.backend.api_cost_migrate import main

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://ddl:secret@/eventrelay"
        "?host=/cloudsql/project:us-central1:eventrelay",
    )
    monkeypatch.setenv("API_COST_RUNTIME_DB_ROLE", "eventrelay_api_runtime")
    monkeypatch.delenv("CLOUD_SQL_INSTANCE_CONNECTION_NAME", raising=False)

    with pytest.raises(RuntimeError, match="CLOUD_SQL_INSTANCE_CONNECTION_NAME"):
        main()
