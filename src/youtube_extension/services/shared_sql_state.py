from __future__ import annotations

import json
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
    create_engine,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SHARED_STATE_PATH = _PROJECT_ROOT / ".runtime" / "shared_state.db"


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
        self.metadata = MetaData()
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
        self.metadata.create_all(self.engine)

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
