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
    """
    Get the current UTC time as a timezone-aware datetime.
    
    Returns:
        datetime: Current time with UTC timezone (tzinfo=timezone.utc).
    """
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
        """
        Create a new job record for the given video or return an existing record with the same idempotency key.
        
        Parameters:
            video_url (str): Source video URL for the job.
            idempotency_key (str): Key that ensures repeated requests produce the same job (replay-by-key).
        
        Returns:
            tuple[JobRecord, bool]: `(record, created)` where `created` is `True` if a new record was created, `False` if an existing record was returned.
        """
        ...

    async def get(self, job_id: str) -> JobRecord | None: """
Retrieve a stored JobRecord by its job identifier.

Returns:
    JobRecord if a record with the given job_id exists, `None` otherwise.
"""
...

    async def update_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None: """
Update the stored job's status and optionally set or clear its error message.

Parameters:
    job_id (str): Identifier of the job to update.
    status (JobStatus): New status to assign to the job.
    error (str | None): Error message to set; pass `None` to clear any existing error.
"""
...

    async def save_results(
        self,
        job_id: str,
        *,
        transcript: str,
        events: list[Event],
        artifacts: Artifacts,
    ) -> None: """
        Persist completion results for the specified job.
        
        Parameters:
            job_id (str): Identifier of the job to update.
            transcript (str): Final transcript text to store for the job.
            events (list[Event]): Domain events produced by the job to persist alongside the record.
            artifacts (Artifacts): Artifacts payload (e.g., generated files, metadata) to attach to the job.
        """
        ...
