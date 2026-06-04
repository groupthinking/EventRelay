"""In-memory JobStore — tests and local dev only.

NOT a production path. Selected by the container only when no database_url is
configured. Exists so the skeleton is runnable and testable without Postgres;
it does not satisfy SC6's durability requirement on its own.
"""
from __future__ import annotations

import uuid

from ..api.v1.schemas import Artifacts, JobStatus
from ..domain.events import Event
from .base import JobRecord


class InMemoryJobStore:
    def __init__(self) -> None:
        self._by_id: dict[str, JobRecord] = {}
        self._by_key: dict[str, str] = {}

    async def create_or_get(self, video_url: str, idempotency_key: str) -> tuple[JobRecord, bool]:
        existing_id = self._by_key.get(idempotency_key)
        if existing_id is not None:
            return self._by_id[existing_id], False
        record = JobRecord(
            job_id=str(uuid.uuid4()),
            video_url=video_url,
            status=JobStatus.queued,
            idempotency_key=idempotency_key,
        )
        self._by_id[record.job_id] = record
        self._by_key[idempotency_key] = record.job_id
        return record, True

    async def get(self, job_id: str) -> JobRecord | None:
        return self._by_id.get(job_id)

    async def update_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None:
        rec = self._by_id[job_id]
        rec.status = status
        rec.error = error

    async def save_results(
        self,
        job_id: str,
        *,
        transcript: str,
        events: list[Event],
        artifacts: Artifacts,
    ) -> None:
        rec = self._by_id[job_id]
        rec.transcript = transcript
        rec.events = events
        rec.artifacts = artifacts
