"""Deployment-only Alembic upgrade and API-cost privilege reconciliation.

Run this module with the DDL ``DATABASE_URL``.  The API and worker must use a
separate login that inherits ``API_COST_RUNTIME_DB_ROLE``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

_ROLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_TARGET_TABLES = (
    "public.api_usage",
    "public.daily_budgets",
    "public.webhook_outbox",
)
_TARGET_SEQUENCES = (
    "public.api_usage_id_seq",
    "public.webhook_outbox_id_seq",
)
_REQUIRED_DML_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")
_UNSAFE_TABLE_PRIVILEGES = ("TRUNCATE", "REFERENCES", "TRIGGER")
_REQUIRED_SEQUENCE_PRIVILEGES = ("USAGE", "SELECT")
_UNSAFE_SEQUENCE_PRIVILEGES = ("UPDATE",)
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "alembic.ini"
_DEPLOYED_ENVIRONMENTS = {"staging", "prod", "production"}
_POSTGRES_CONNECT_OPTIONS = "-c search_path=public -c timezone=UTC"


def normalize_database_url(database_url: str) -> str:
    """Normalize supported PostgreSQL URLs to the required Psycopg 3 driver."""
    replacements = (
        ("postgresql+asyncpg://", "postgresql+psycopg://"),
        ("postgresql+psycopg2://", "postgresql+psycopg://"),
        ("postgresql://", "postgresql+psycopg://"),
        ("postgres://", "postgresql+psycopg://"),
    )
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    for prefix, replacement in replacements:
        if database_url.startswith(prefix):
            return replacement + database_url[len(prefix) :]
    raise ValueError("API-cost migrations require a PostgreSQL DATABASE_URL")


def validate_cloud_sql_database_url(database_url: str, instance: str) -> None:
    """Require the DDL URL to target the Cloud SQL socket attached to the job."""
    normalized_url = normalize_database_url(database_url)
    try:
        url = make_url(normalized_url)
    except Exception as exc:
        raise RuntimeError("Migration DATABASE_URL is invalid") from exc
    expected_host = f"/cloudsql/{instance}"
    if url.host not in {None, ""} or url.query.get("host") != expected_host:
        raise RuntimeError(
            "Migration DATABASE_URL must use the attached Cloud SQL Unix socket "
            f"(host={expected_host})"
        )


def validate_runtime_role(runtime_role: str) -> str:
    """Reject ambiguous or injectable PostgreSQL role identifiers."""
    if not _ROLE_PATTERN.fullmatch(runtime_role):
        raise ValueError(
            "API_COST_RUNTIME_DB_ROLE must be a plain runtime database role "
            "identifier (1-63 ASCII letters, digits, or underscores)"
        )
    return runtime_role


def _quote_postgres_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def database_create_revoke_statement(database_name: str, runtime_role: str) -> str:
    """Return an injection-safe revoke for the connected database."""
    role = validate_runtime_role(runtime_role)
    return (
        "REVOKE CREATE ON DATABASE "
        f"{_quote_postgres_identifier(database_name)} FROM "
        f"{_quote_postgres_identifier(role)}"
    )


def runtime_grant_statements(runtime_role: str) -> tuple[str, ...]:
    """Return the deliberately narrow, idempotent runtime privilege policy."""
    role = validate_runtime_role(runtime_role)
    quoted_role = f'"{role}"'
    tables = ", ".join(_TARGET_TABLES)
    sequences = ", ".join(_TARGET_SEQUENCES)
    return (
        "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
        f"REVOKE CREATE ON SCHEMA public FROM {quoted_role}",
        f"REVOKE ALL PRIVILEGES ON TABLE {tables} FROM {quoted_role}",
        f"REVOKE ALL PRIVILEGES ON SEQUENCE {sequences} FROM {quoted_role}",
        f"GRANT USAGE ON SCHEMA public TO {quoted_role}",
        (
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {tables} "
            f"TO {quoted_role}"
        ),
        f"GRANT USAGE, SELECT ON SEQUENCE {sequences} TO {quoted_role}",
        (
            "REVOKE ALL PRIVILEGES ON TABLE public.alembic_version "
            f"FROM {quoted_role}"
        ),
    )


def _role_record(connection: Connection, runtime_role: str):
    return (
        connection.execute(
            text("""
                SELECT rolname, rolsuper, rolcreatedb, rolcreaterole,
                       rolreplication, rolbypassrls, rolcanlogin
                FROM pg_roles
                WHERE rolname = :role
                """),
            {"role": runtime_role},
        )
        .mappings()
        .one_or_none()
    )


def _assert_runtime_privileges(connection: Connection, runtime_role: str) -> None:
    can_create_database_objects = connection.execute(
        text("SELECT has_database_privilege(" ":role, current_database(), 'CREATE')"),
        {"role": runtime_role},
    ).scalar_one()
    if can_create_database_objects:
        raise RuntimeError(
            f"Runtime role {runtime_role!r} still has effective database CREATE"
        )

    can_create = connection.execute(
        text("SELECT has_schema_privilege(:role, 'public', 'CREATE')"),
        {"role": runtime_role},
    ).scalar_one()
    if can_create:
        raise RuntimeError(
            f"Runtime role {runtime_role!r} still has effective schema CREATE"
        )

    unexpected_schema_access = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_namespace AS namespace
                WHERE namespace.nspname <> 'public'
                  AND namespace.nspname <> 'information_schema'
                  AND namespace.nspname !~ '^pg_'
                  AND (
                    has_schema_privilege(:role, namespace.oid, 'USAGE')
                    OR has_schema_privilege(:role, namespace.oid, 'CREATE')
                  )
            )
            """),
        {"role": runtime_role},
    ).scalar_one()
    if unexpected_schema_access:
        raise RuntimeError(
            f"Runtime role {runtime_role!r} can access an unrelated schema"
        )

    unexpected_table_access = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                CROSS JOIN (
                    VALUES
                      ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'),
                      ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')
                ) AS candidate(privilege_name)
                WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f')
                  AND namespace.nspname <> 'information_schema'
                  AND namespace.nspname !~ '^pg_'
                  AND NOT (
                    namespace.nspname = 'public'
                    AND relation.relname IN (
                      'api_usage', 'daily_budgets', 'webhook_outbox'
                    )
                    AND candidate.privilege_name IN (
                      'SELECT', 'INSERT', 'UPDATE', 'DELETE'
                    )
                  )
                  AND has_table_privilege(
                    :role, relation.oid, candidate.privilege_name
                  )
            )
            """),
        {"role": runtime_role},
    ).scalar_one()
    if unexpected_table_access:
        raise RuntimeError(
            f"Runtime role {runtime_role!r} can access an unrelated table"
        )

    unexpected_sequence_access = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                CROSS JOIN (
                    VALUES ('USAGE'), ('SELECT'), ('UPDATE')
                ) AS candidate(privilege_name)
                WHERE relation.relkind = 'S'
                  AND namespace.nspname <> 'information_schema'
                  AND namespace.nspname !~ '^pg_'
                  AND NOT (
                    namespace.nspname = 'public'
                    AND relation.relname IN (
                      'api_usage_id_seq', 'webhook_outbox_id_seq'
                    )
                    AND candidate.privilege_name IN ('USAGE', 'SELECT')
                  )
                  AND has_sequence_privilege(
                    :role, relation.oid, candidate.privilege_name
                  )
            )
            """),
        {"role": runtime_role},
    ).scalar_one()
    if unexpected_sequence_access:
        raise RuntimeError(
            f"Runtime role {runtime_role!r} can access an unrelated sequence"
        )

    owns_target = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                JOIN pg_roles AS owner ON owner.oid = relation.relowner
                WHERE namespace.nspname = 'public'
                  AND relation.relname IN (
                      'api_usage', 'daily_budgets', 'webhook_outbox'
                  )
                  AND owner.rolname = :role
            )
            """),
        {"role": runtime_role},
    ).scalar_one()
    if owns_target:
        raise RuntimeError(
            f"Runtime role {runtime_role!r} owns an API-cost table and can alter it"
        )

    for relation in _TARGET_TABLES:
        for privilege in _REQUIRED_DML_PRIVILEGES:
            has_privilege = connection.execute(
                text("SELECT has_table_privilege(" ":role, :relation, :privilege)"),
                {
                    "role": runtime_role,
                    "relation": relation,
                    "privilege": privilege,
                },
            ).scalar_one()
            if not has_privilege:
                raise RuntimeError(
                    f"Runtime role {runtime_role!r} lacks {privilege} on {relation}"
                )
        for privilege in _UNSAFE_TABLE_PRIVILEGES:
            has_privilege = connection.execute(
                text("SELECT has_table_privilege(" ":role, :relation, :privilege)"),
                {
                    "role": runtime_role,
                    "relation": relation,
                    "privilege": privilege,
                },
            ).scalar_one()
            if has_privilege:
                raise RuntimeError(
                    f"Runtime role {runtime_role!r} has unsafe {privilege} "
                    f"on {relation}"
                )

    for sequence in _TARGET_SEQUENCES:
        for privilege in _REQUIRED_SEQUENCE_PRIVILEGES:
            has_sequence_access = connection.execute(
                text("SELECT has_sequence_privilege(" ":role, :sequence, :privilege)"),
                {
                    "role": runtime_role,
                    "sequence": sequence,
                    "privilege": privilege,
                },
            ).scalar_one()
            if not has_sequence_access:
                raise RuntimeError(
                    f"Runtime role {runtime_role!r} lacks {privilege} on {sequence}"
                )
        for privilege in _UNSAFE_SEQUENCE_PRIVILEGES:
            has_sequence_access = connection.execute(
                text("SELECT has_sequence_privilege(" ":role, :sequence, :privilege)"),
                {
                    "role": runtime_role,
                    "sequence": sequence,
                    "privilege": privilege,
                },
            ).scalar_one()
            if has_sequence_access:
                raise RuntimeError(
                    f"Runtime role {runtime_role!r} has unsafe {privilege} "
                    f"on {sequence}"
                )

    can_read_version = connection.execute(
        text(
            "SELECT has_table_privilege(" ":role, 'public.alembic_version', 'SELECT')"
        ),
        {"role": runtime_role},
    ).scalar_one()
    if can_read_version:
        raise RuntimeError(
            f"Runtime role {runtime_role!r} can read public.alembic_version"
        )


def apply_runtime_grants(connection: Connection, runtime_role: str) -> None:
    """Reconcile and verify the runtime role after every migration run."""
    role = validate_runtime_role(runtime_role)
    record = _role_record(connection, role)
    if record is None:
        raise RuntimeError(f"Runtime database role {role!r} does not exist")
    if (
        record["rolsuper"]
        or record["rolcreatedb"]
        or record["rolcreaterole"]
        or record["rolreplication"]
        or record["rolbypassrls"]
    ):
        raise RuntimeError(f"Runtime database role {role!r} is elevated")
    if record["rolcanlogin"]:
        raise RuntimeError(
            f"Runtime database role {role!r} must be a stable NOLOGIN group role"
        )
    has_parent_roles = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_auth_members AS membership
                JOIN pg_roles AS child ON child.oid = membership.member
                WHERE child.rolname = :role
            )
            """),
        {"role": role},
    ).scalar_one()
    if has_parent_roles:
        raise RuntimeError(
            f"Runtime database role {role!r} must not inherit from parent roles"
        )

    migration_role = connection.execute(text("SELECT current_user")).scalar_one()
    if migration_role == role:
        raise RuntimeError("DDL and runtime database roles must be separate")

    database_name = connection.execute(text("SELECT current_database()"))
    database_name = database_name.scalar_one()
    connection.execute(text(database_create_revoke_statement(database_name, role)))

    for statement in runtime_grant_statements(role):
        connection.execute(text(statement))

    _assert_runtime_privileges(connection, role)


def migrate_and_grant(
    database_url: str,
    runtime_role: str,
    *,
    config_path: Path = _DEFAULT_CONFIG_PATH,
    cloud_sql_instance: str | None = None,
) -> None:
    """Upgrade to head, then atomically reconcile the runtime role's grants."""
    normalized_url = normalize_database_url(database_url)
    role = validate_runtime_role(runtime_role)
    if cloud_sql_instance:
        validate_cloud_sql_database_url(normalized_url, cloud_sql_instance)

    alembic_config = Config(str(config_path))
    # ConfigParser treats percent signs as interpolation markers. Doubling them
    # preserves percent-encoded credentials without logging their value.
    alembic_config.set_main_option("sqlalchemy.url", normalized_url.replace("%", "%%"))
    command.upgrade(alembic_config, "head")

    engine = create_engine(
        normalized_url,
        poolclass=NullPool,
        future=True,
        connect_args={"options": _POSTGRES_CONNECT_OPTIONS},
    )
    try:
        with engine.begin() as connection:
            apply_runtime_grants(connection, role)
    finally:
        engine.dispose()


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for the migration job")
    runtime_role = os.getenv("API_COST_RUNTIME_DB_ROLE")
    if not runtime_role:
        raise RuntimeError("API_COST_RUNTIME_DB_ROLE is required for the migration job")
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    cloud_sql_instance = os.getenv("CLOUD_SQL_INSTANCE_CONNECTION_NAME", "").strip()
    if environment in _DEPLOYED_ENVIRONMENTS and not cloud_sql_instance:
        raise RuntimeError(
            "CLOUD_SQL_INSTANCE_CONNECTION_NAME is required for deployed migrations"
        )
    migrate_and_grant(
        database_url,
        runtime_role,
        cloud_sql_instance=cloud_sql_instance or None,
    )


if __name__ == "__main__":
    main()
