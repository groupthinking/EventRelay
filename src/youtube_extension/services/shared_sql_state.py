from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    bindparam,
    create_engine,
    insert,
    select,
    text,
    update,
)
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import StaticPool

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SHARED_STATE_PATH = _PROJECT_ROOT / ".runtime" / "shared_state.db"

# The Supabase migration is the schema source of truth for non-SQLite databases.
SHARED_STATE_MIGRATION = (
    "apps/web/supabase/migrations/"
    "20261109062000_create_service_role_shared_state_tables.sql"
)

logger = logging.getLogger(__name__)


class SharedStateSchemaError(SQLAlchemyError):
    """Raised when a non-SQLite shared-state database lacks the migrated schema."""


def normalize_shared_storage_url(database_url: str) -> str:
    """Normalize supported PostgreSQL URLs onto the Psycopg sync driver."""

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
    return database_url


def resolve_shared_storage_url(
    database_url: str | None = None,
    *,
    sqlite_path: Path | None = None,
) -> str:
    """Resolve the shared state database URL from explicit, env, or local config."""

    raw_url = (
        database_url
        or os.getenv("EVENTRELAY_SHARED_STATE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    if raw_url:
        return normalize_shared_storage_url(raw_url)

    path = (sqlite_path or DEFAULT_SHARED_STATE_PATH).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:////{path.as_posix().lstrip('/')}"


class SharedSQLStateStore:
    """Persist session timelines and A2A messages in shared SQL storage."""

    def __init__(
        self,
        database_url: str | None = None,
        *,
        sqlite_path: Path | None = None,
    ) -> None:
        self.database_url = resolve_shared_storage_url(
            database_url, sqlite_path=sqlite_path
        )
        self.engine = self._create_engine(self.database_url)
        # Validate and use the same schema even with a non-public search_path.
        self.metadata = MetaData(schema="public" if self.engine.dialect.name == "postgresql" else None)
        self.sessions = Table(
            "shared_sessions",
            self.metadata,
            Column("session_id", String(255), primary_key=True),
            Column("payload", Text, nullable=False),
            Column("version", Integer, nullable=False, default=1),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
        )
        self.timeline_events = Table(
            "shared_timeline_events",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("session_id", String(255), nullable=False, index=True),
            Column("timestamp", String(64), nullable=False),
            Column("summary", Text, nullable=False),
            Column("content", Text, nullable=False),
        )
        self.a2a_messages = Table(
            "shared_a2a_messages",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("sender", String(255), nullable=False),
            Column("recipient", String(255), nullable=False),
            Column("conversation_id", String(255), nullable=False, index=True),
            Column("timestamp", String(64), nullable=False),
            Column("content", Text, nullable=False),
        )
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables for local SQLite; verify migrated tables everywhere else.

        SQLite is the local/test default, so the tables are created on demand.
        For PostgreSQL/Supabase the checked-in migration owns the schema (and its
        row-level security), so this never issues DDL there: it only confirms the
        tables, columns, forced RLS and role privileges match the migration.
        """

        if self.engine.dialect.name == "sqlite":
            self.metadata.create_all(self.engine)
            return

        inspector = sa_inspect(self.engine)
        problems: list[str] = []
        for table in self.metadata.sorted_tables:
            if not inspector.has_table(table.name, schema="public"):
                problems.append(f"missing table {table.name}")
                continue
            present = {column["name"] for column in inspector.get_columns(table.name, schema="public")}
            missing = [column.name for column in table.columns if column.name not in present]
            if missing:
                problems.append(f"{table.name} missing columns {', '.join(missing)}")
        if not problems and self.engine.dialect.name == "postgresql":
            problems.extend(self._postgres_security_problems())
        if problems:
            message = (
                "Shared state schema is not migrated on "
                f"{self.engine.dialect.name} ({'; '.join(problems)}). "
                f"Apply {SHARED_STATE_MIGRATION}; the service does not create "
                "these tables outside SQLite."
            )
            logger.error(message)
            raise SharedStateSchemaError(message)

    def _postgres_security_problems(self) -> list[str]:
        """Reject legacy create_all tables that have columns but no hardening."""
        tables = {table.name for table in self.metadata.sorted_tables}
        sequences = {"shared_timeline_events_id_seq", "shared_a2a_messages_id_seq"}
        query = text("""
            SELECT c.relname, c.relkind, c.relrowsecurity, c.relforcerowsecurity,
                   (EXISTS (
                       SELECT 1 FROM aclexplode(coalesce(c.relacl, acldefault(
                           CASE WHEN c.relkind = 'S' THEN 'S'::\"char\" ELSE 'r'::\"char\" END,
                           c.relowner))) a
                       WHERE a.grantee = 0 OR a.grantee IN (
                           SELECT oid FROM pg_roles WHERE rolname IN ('anon', 'authenticated')
                       )
                   ) OR EXISTS (
                       SELECT 1 FROM pg_roles r
                       WHERE r.rolname IN ('anon', 'authenticated') AND (
                           r.rolsuper OR r.rolbypassrls OR
                           CASE WHEN c.relkind = 'S'
                               THEN has_sequence_privilege(r.oid, c.oid, 'SELECT,USAGE,UPDATE')
                               ELSE has_table_privilege(r.oid, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                           END
                       )
                   )) AS untrusted_acl,
                   (SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user)
                       AS server_bypasses_rls,
                   CASE WHEN c.relkind = 'S'
                       THEN has_sequence_privilege(current_user, c.oid, 'USAGE')
                            AND has_sequence_privilege(current_user, c.oid, 'SELECT')
                       ELSE has_table_privilege(current_user, c.oid, 'SELECT')
                            AND has_table_privilege(current_user, c.oid, 'INSERT')
                            AND has_table_privilege(current_user, c.oid, 'UPDATE')
                            AND has_table_privilege(current_user, c.oid, 'DELETE')
                   END AS server_privileges,
                   ARRAY(
                       SELECT privilege_type FROM aclexplode(coalesce(c.relacl, acldefault(
                           CASE WHEN c.relkind = 'S' THEN 'S'::\"char\" ELSE 'r'::\"char\" END,
                           c.relowner))) a
                       WHERE a.grantee = (SELECT oid FROM pg_roles WHERE rolname = 'service_role')
                   ) AS service_privileges
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname IN :relations
        """).bindparams(bindparam("relations", expanding=True))
        with self.engine.connect() as connection:
            rows = connection.execute(query, {"relations": sorted(tables | sequences)}).mappings().all()
        states = {row["relname"]: row for row in rows}
        problems = []
        for name in sorted(tables | sequences):
            state = states.get(name)
            if state is None:
                problems.append(f"security state missing for {name}")
                continue
            if name in tables and not (state["relrowsecurity"] and state["relforcerowsecurity"]):
                problems.append(f"security: {name} must enable and force RLS")
            if state["untrusted_acl"]:
                problems.append(f"security: {name} grants privileges to public or client roles")
            if state["relkind"] != ("r" if name in tables else "S"):
                problems.append(f"security: unexpected relation type for {name}")
            if not state["server_bypasses_rls"]:
                problems.append(f"security: server role cannot bypass forced RLS for {name}")
            if not state["server_privileges"]:
                problems.append(f"security: server role lacks required privileges for {name}")
            required = {"SELECT", "INSERT", "UPDATE", "DELETE"} if name in tables else {"USAGE", "SELECT"}
            if not required <= set(state["service_privileges"]):
                problems.append(f"security: {name} lacks required service_role privileges")
        return problems

    @staticmethod
    def _create_engine(database_url: str) -> Engine:
        url = make_url(database_url)
        if url.get_backend_name() == "sqlite":
            kwargs: dict[str, Any] = {
                "connect_args": {"check_same_thread": False, "timeout": 30},
                "future": True,
            }
            if not url.database:
                kwargs["poolclass"] = StaticPool
            return create_engine(database_url, **kwargs)
        return create_engine(database_url, future=True, pool_pre_ping=True)

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _serialize(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _deserialize(value: str) -> dict[str, Any]:
        return json.loads(value)

    def save_session(self, session: dict[str, Any]) -> dict[str, Any]:
        """Create or update a session row with optimistic retries."""

        session_id = session["id"]
        payload = dict(session)
        payload.pop("timeline", None)

        for _ in range(5):
            now = self._utcnow()
            with self.engine.begin() as conn:
                current = conn.execute(
                    select(
                        self.sessions.c.payload,
                        self.sessions.c.version,
                        self.sessions.c.created_at,
                    ).where(self.sessions.c.session_id == session_id)
                ).mappings().first()
                if current is None:
                    try:
                        conn.execute(
                            insert(self.sessions).values(
                                session_id=session_id,
                                payload=self._serialize(payload),
                                version=1,
                                created_at=now,
                                updated_at=now,
                            )
                        )
                        return payload
                    except IntegrityError:
                        continue

                merged = self._deserialize(current["payload"])
                merged.update(payload)
                result = conn.execute(
                    update(self.sessions)
                    .where(
                        self.sessions.c.session_id == session_id,
                        self.sessions.c.version == current["version"],
                    )
                    .values(
                        payload=self._serialize(merged),
                        version=current["version"] + 1,
                        updated_at=now,
                    )
                )
                if result.rowcount == 1:
                    return merged

        raise RuntimeError(f"Failed to persist shared session state for {session_id}")

    def import_legacy_sessions(self, sessions: dict[str, dict[str, Any]]) -> None:
        """Import JSON-backed sessions on first run without duplicating rows."""

        for session in sessions.values():
            if self.get_session(session["id"]) is not None:
                continue
            self.save_session(session)
            for event in session.get("timeline", []):
                self.append_timeline_event(session["id"], event)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(self.sessions.c.payload).where(self.sessions.c.session_id == session_id)
            ).scalar_one_or_none()
        if row is None:
            return None
        session = self._deserialize(row)
        session["timeline"] = self.list_timeline(session_id)
        return session

    def list_sessions(self) -> dict[str, dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(select(self.sessions.c.payload)).scalars().all()
        sessions = {}
        for payload in rows:
            session = self._deserialize(payload)
            session["timeline"] = self.list_timeline(session["id"])
            sessions[session["id"]] = session
        return sessions

    def append_timeline_event(self, session_id: str, event: dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.timeline_events).values(
                    session_id=session_id,
                    timestamp=event["timestamp"],
                    summary=event["summary"],
                    content=event["content"],
                )
            )

    def list_timeline(self, session_id: str) -> list[dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(
                    self.timeline_events.c.timestamp,
                    self.timeline_events.c.summary,
                    self.timeline_events.c.content,
                )
                .where(self.timeline_events.c.session_id == session_id)
                .order_by(self.timeline_events.c.id)
            ).mappings()
            return [dict(row) for row in rows]

    def append_a2a_message(self, message: dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.a2a_messages).values(
                    sender=message["sender"],
                    recipient=message["recipient"],
                    conversation_id=message["conversation_id"],
                    timestamp=message["timestamp"],
                    content=self._serialize(message["content"]),
                )
            )

    def get_a2a_messages(
        self,
        *,
        conversation_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        statement = (
            select(
                self.a2a_messages.c.sender,
                self.a2a_messages.c.recipient,
                self.a2a_messages.c.content,
                self.a2a_messages.c.conversation_id,
                self.a2a_messages.c.timestamp,
            )
            .order_by(self.a2a_messages.c.id.desc())
            .limit(limit)
        )
        if conversation_id:
            statement = statement.where(
                self.a2a_messages.c.conversation_id == conversation_id
            )
        with self.engine.begin() as conn:
            rows = conn.execute(statement).mappings().all()
        messages = []
        for row in reversed(rows):
            messages.append(
                {
                    "sender": row["sender"],
                    "recipient": row["recipient"],
                    "content": self._deserialize(row["content"]),
                    "conversation_id": row["conversation_id"],
                    "timestamp": row["timestamp"],
                }
            )
        return messages
