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
        Initialize the in-memory job store's internal maps.
        
        Creates two dictionaries used for non-production, in-memory persistence:
        - _by_id: maps a job_id (str) to its JobRecord.
        - _by_key: maps an idempotency_key (str) to a job_id (str).
        """
        self._by_id: dict[str, JobRecord] = {}
        self._by_key: dict[str, str] = {}

    async def create_or_get(self, video_url: str, idempotency_key: str) -> tuple[JobRecord, bool]:
        """
        Create a new job record for the given video URL unless a record already exists for the provided idempotency key.
        
        Parameters:
            video_url (str): URL of the video to process.
            idempotency_key (str): Key used to ensure idempotent creation across repeated requests.
        
        Returns:
            tuple[JobRecord, bool]: The job record and `True` if a new record was created, `False` if an existing record was returned.
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
        Retrieve a job record by its identifier.
        
        Parameters:
            job_id (str): The job's identifier to look up.
        
        Returns:
            JobRecord | None: The matching job record if present, otherwise `None`.
        """
        return self._by_id.get(job_id)

    async def update_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None:
        """
        Update the status and optional error message of an existing job record.
        
        Parameters:
        	job_id (str): Identifier of the job to update.
        	status (JobStatus): New status to assign to the job.
        	error (str | None): Optional error message to store; set to None to clear any existing error.
        
        Raises:
        	KeyError: If no job exists for the given `job_id`.
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
        Persist final job outputs (transcript, domain events, and artifacts) onto an existing job record.
        
        Parameters:
            job_id (str): Identifier of the job whose record will be updated. Must exist in the store.
            transcript (str): Final transcript text produced for the job.
            events (list[Event]): Domain events emitted during processing to be stored with the job.
            artifacts (Artifacts): Generated artifacts metadata to attach to the job record.
        
        Raises:
            KeyError: If no job with `job_id` exists in the store.
        """
        rec = self._by_id[job_id]
        rec.transcript = transcript
        rec.events = events
        rec.artifacts = artifacts
