"""API request/response schemas (SC5).

These define the *clean* contract surface — the job-centric subset that traces
to SC1-SC7. FastAPI generates the OpenAPI document from these models; that
generated document replaces the legacy 40-path openapi/eventrelay.openapi.json
as the source of truth for SDK generation.

Field names are aligned with the legacy contract where they carry over
(`video_url`, `language`, `options`) so the SDK delta stays small.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from ...domain.events import Event


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class SubmitJobRequest(BaseModel):
    """SC1 — input ingest."""

    video_url: str
    language: str | None = None
    options: dict | None = None


class SubmitJobResponse(BaseModel):
    job_id: str
    status: JobStatus


class Artifacts(BaseModel):
    """SC4 — derived artifacts."""

    summary: str
    tasks: list[str] = Field(default_factory=list)
    insights: dict = Field(default_factory=dict)


class JobView(BaseModel):
    """SC6 — observable job state."""

    job_id: str
    status: JobStatus
    video_url: str
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class TranscriptView(BaseModel):
    job_id: str
    transcript: str


class EventsView(BaseModel):
    job_id: str
    events: list[Event] = Field(default_factory=list)


class ArtifactsView(BaseModel):
    job_id: str
    artifacts: Artifacts


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
