"""Postgres JobStore (SC6 — the production persistence path).

Implements the JobStore protocol over async SQLAlchemy. This is the single
chosen datastore; Prisma / Firebase Data Connect / Supabase paths in the legacy
repo are residue and are not used here.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..api.v1.schemas import Artifacts, JobStatus
from ..domain.events import Event
from .base import JobRecord
from .models import Base, EventRow, Job


class SqlAlchemyJobStore:
    def __init__(self, dsn: str) -> None:
        """
        Create an async SQLAlchemy engine and an async session factory bound to it for the given database DSN.
        
        The engine is created with connection pool pre-ping enabled and the session factory is configured with expire_on_commit=False.
        
        Parameters:
            dsn (str): Database connection string (DSN) used to connect to Postgres.
        """
        self._engine = create_async_engine(dsn, pool_pre_ping=True)
        self._session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine, expire_on_commit=False
        )

    async def init_models(self) -> None:
        """Create tables. Production uses Alembic migrations instead; this is a
        convenience for local Postgres bring-up."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @staticmethod
    def _to_record(job: Job) -> JobRecord:
        """
        Convert a Job ORM instance into a domain JobRecord.
        
        Parameters:
            job (Job): ORM Job instance to convert; must include associated event rows and optional artifact data.
        
        Returns:
            JobRecord: Domain representation with fields mapped from the ORM model. `events` is a list of Event objects; `artifacts` is an Artifacts instance when artifact data is present, otherwise None.
        """
        return JobRecord(
            job_id=job.id,
            video_url=job.video_url,
            status=JobStatus(job.status),
            idempotency_key=job.idempotency_key,
            created_at=job.created_at,
            updated_at=job.updated_at,
            error=job.error,
            transcript=job.transcript,
            events=[Event(type=e.type, ts=e.ts, payload=e.payload) for e in job.events],
            artifacts=Artifacts(**job.artifacts) if job.artifacts else None,
        )

    async def create_or_get(self, video_url: str, idempotency_key: str) -> tuple[JobRecord, bool]:
        """
        Create a new job for the given video or return an existing job that matches the idempotency key.
        
        Parameters:
            video_url (str): The video's URL to associate with the job.
            idempotency_key (str): Key used to identify an existing job and ensure idempotent creation.
        
        Returns:
            tuple[JobRecord, bool]: A tuple containing the job record and a boolean that is `True` if a new job was created, `False` if an existing job was returned.
        """
        async with self._session() as s:
            existing = (
                await s.execute(select(Job).where(Job.idempotency_key == idempotency_key))
            ).scalar_one_or_none()
            if existing is not None:
                return self._to_record(existing), False
            job = Job(
                id=str(uuid.uuid4()),
                video_url=video_url,
                status=JobStatus.queued.value,
                idempotency_key=idempotency_key,
            )
            s.add(job)
            await s.commit()
            await s.refresh(job)
            return self._to_record(job), True

    async def get(self, job_id: str) -> JobRecord | None:
        """
        Fetches a job by its identifier and returns the corresponding domain record.
        
        Returns:
            JobRecord if a job with the given ID exists, `None` otherwise.
        """
        async with self._session() as s:
            job = (
                await s.execute(select(Job).where(Job.id == job_id))
            ).scalar_one_or_none()
            return self._to_record(job) if job else None

    async def update_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None:
        """
        Update a job's status and optional error message in persistent storage.
        
        Parameters:
        	job_id (str): The job's unique identifier.
        	status (JobStatus): New status to apply to the job.
        	error (str | None): Error message to store for the job, or `None` to clear it.
        
        Raises:
        	KeyError: If no job exists with the given `job_id`.
        """
        async with self._session() as s:
            job = await s.get(Job, job_id)
            if job is None:
                raise KeyError(job_id)
            job.status = status.value
            job.error = error
            await s.commit()

    async def save_results(
        self,
        job_id: str,
        *,
        transcript: str,
        events: list[Event],
        artifacts: Artifacts,
    ) -> None:
        """
        Persist the transcript, events, and artifacts for the job identified by job_id.
        
        Updates the job's transcript, stores artifacts using the model's serialized form, and replaces the job's events with the provided list (each converted into an EventRow), then commits the changes to the database.
        
        Parameters:
            job_id (str): Identifier of the job to update.
            transcript (str): Transcribed text to store on the job.
            events (list[Event]): Domain events to persist; each event is converted into an EventRow with `type`, `ts`, and `payload`.
            artifacts (Artifacts): Artifacts to store; the artifact model is serialized via `model_dump()` before persistence.
        
        Raises:
            KeyError: If no job exists with the given `job_id`.
        """
        async with self._session() as s:
            job = await s.get(Job, job_id)
            if job is None:
                raise KeyError(job_id)
            job.transcript = transcript
            job.artifacts = artifacts.model_dump()
            job.events = [EventRow(type=e.type, ts=e.ts, payload=e.payload) for e in events]
            await s.commit()
