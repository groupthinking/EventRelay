"""Postgres JobStore (SC6 — the production persistence path).

Implements the JobStore protocol over async SQLAlchemy. This is the single
chosen datastore; Prisma / Firebase Data Connect / Supabase paths in the legacy
repo are residue and are not used here.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from ..api.v1.schemas import Artifacts, JobStatus
from ..domain.events import Event
from .base import JobRecord
from .models import Base, EventRow, Job


class SqlAlchemyJobStore:
    def __init__(self, dsn: str) -> None:
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

    async def create_or_get(
        self, video_url: str, idempotency_key: str
    ) -> tuple[JobRecord, bool]:
        async with self._session() as s:
            existing = (
                await s.execute(
                    select(Job)
                    .where(Job.idempotency_key == idempotency_key)
                    .options(selectinload(Job.events))
                )
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
            # Eager-load `events` so _to_record does not trigger an async lazy load.
            await s.refresh(job, attribute_names=["events"])
            return self._to_record(job), True

    async def get(self, job_id: str) -> JobRecord | None:
        async with self._session() as s:
            job = (
                await s.execute(
                    select(Job)
                    .where(Job.id == job_id)
                    .options(selectinload(Job.events))
                )
            ).scalar_one_or_none()
            return self._to_record(job) if job else None

    async def update_status(
        self, job_id: str, status: JobStatus, error: str | None = None
    ) -> None:
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
        async with self._session() as s:
            # Eager-load existing events so the delete-orphan cascade can mark
            # them for removal when the collection is reassigned (an async lazy
            # load here would raise MissingGreenlet).
            job = (
                await s.execute(
                    select(Job)
                    .where(Job.id == job_id)
                    .options(selectinload(Job.events))
                )
            ).scalar_one_or_none()
            if job is None:
                raise KeyError(job_id)
            job.transcript = transcript
            job.artifacts = artifacts.model_dump()
            job.events = [
                EventRow(type=e.type, ts=e.ts, payload=e.payload) for e in events
            ]
            await s.commit()
