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
    Get the current UTC datetime as a timezone-aware `datetime`.
    
    Returns:
        datetime: A timezone-aware `datetime` set to UTC representing the current time.
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
        Create a new job record for the given video or retrieve an existing record that matches the provided idempotency key.
        
        Parameters:
            video_url (str): Source URL for the job.
            idempotency_key (str): Key used to ensure idempotent creation; requests with the same key return the same existing job rather than creating a duplicate.
        
        Returns:
            tuple[JobRecord, bool]: A tuple of the job record and a boolean `created` flag — `True` if a new record was created, `False` if an existing record was returned.
        """
        ...

    async def get(self, job_id: str) -> JobRecord | None: """
Fetches the stored JobRecord for the specified job identifier.

Returns:
    JobRecord | None: The JobRecord matching job_id, or `None` if no record exists.
"""
...

    async def update_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None: """
Set the stored status for a job and optionally set or clear its error message.

Parameters:
    job_id (str): Identifier of the job to update.
    status (JobStatus): New status to persist for the job.
    error (str | None): Error message to record for the job; pass None to clear any existing error.
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
        Persist job completion outputs (transcript, events, and artifacts) to the stored job record identified by `job_id`.
        
        Parameters:
            job_id (str): Identifier of the job record to update.
            transcript (str): Final transcript text produced by the job.
            events (list[Event]): Domain events associated with the job's processing results.
            artifacts (Artifacts): Resulting artifacts (e.g., files, metadata) to store alongside the job.
        """
        ...
