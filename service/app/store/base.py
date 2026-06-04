"""Persistence interface (SC6).

One store interface. Two implementations live behind it: the Postgres store
(production) and an in-memory store (tests/local). They are not competing
designs — the Protocol is the single contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from ..api.v1.schemas import Artifacts, JobStatus
from ..domain.events import Event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobRecord:
    """The durable unit of work (SC6)."""

    job_id: str
    video_url: str
    status: JobStatus
    idempotency_key: str
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    error: str | None = None
    transcript: str | None = None
    events: list[Event] = field(default_factory=list)
    artifacts: Artifacts | None = None


class JobStore(Protocol):
    """Durable, idempotent job + event store."""

    async def create_or_get(self, video_url: str, idempotency_key: str) -> tuple[JobRecord, bool]:
        """Return (record, created). If a job with the same idempotency_key
        exists, return it with created=False (SC6 replay-by-key)."""
        ...

    async def get(self, job_id: str) -> JobRecord | None: ...

    async def update_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None: ...

    async def save_results(
        self,
        job_id: str,
        *,
        transcript: str,
        events: list[Event],
        artifacts: Artifacts,
    ) -> None: ...
