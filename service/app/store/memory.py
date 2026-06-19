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
        """
        Initialize the in-memory job store and its internal indexes.
        
        Creates two empty dictionaries used for storage and lookup:
        - _by_id: maps job_id (str) to JobRecord
        - _by_key: maps idempotency_key (str) to job_id
        """
        self._by_id: dict[str, JobRecord] = {}
        self._by_key: dict[str, str] = {}

    async def create_or_get(self, video_url: str, idempotency_key: str) -> tuple[JobRecord, bool]:
        """
        Create a new job record for the given video URL or return the existing record for the provided idempotency key.
        
        Parameters:
            video_url (str): URL of the video to create a job for.
            idempotency_key (str): Key used to ensure idempotent creation; if a record with this key already exists, that record is returned.
        
        Returns:
            tuple[JobRecord, bool]: The job record and a boolean flag that is `True` when a new record was created, `False` when an existing record was returned.
        """
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
        """
        Retrieve a job record by its job ID.
        
        Returns:
            JobRecord for the given job ID, or `None` if no record exists.
        """
        return self._by_id.get(job_id)

    async def update_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None:
        """
        Update the stored job's status and optional error message.
        
        Parameters:
            job_id (str): Identifier of the job to update.
            status (JobStatus): New status to set on the job record.
            error (str | None): Error message to attach to the job, or None to clear it.
        
        Raises:
            KeyError: If no job with `job_id` exists in the store.
        """
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
        """
        Persist transcript, domain events, and artifact metadata for the job identified by `job_id`.
        
        Parameters:
        	job_id (str): Identifier of the job whose record will be updated.
        	transcript (str): Final transcript text produced for the job.
        	events (list[Event]): Domain events generated during processing.
        	artifacts (Artifacts): Metadata about produced artifacts (e.g., file locations, checksums).
        
        Raises:
        	KeyError: If no job with `job_id` exists in the store.
        """
        rec = self._by_id[job_id]
        rec.transcript = transcript
        rec.events = events
        rec.artifacts = artifacts
