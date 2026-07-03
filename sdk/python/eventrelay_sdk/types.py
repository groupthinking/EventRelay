"""
Pydantic models mirroring the EventRelay API request/response schemas.

These are derived from openapi/eventrelay.openapi.json and kept in sync
with the backend models defined in:
  src/youtube_extension/backend/api/v1/models.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    pending = "pending"
    downloading = "downloading"
    transcribing = "transcribing"
    extracting = "extracting"
    complete = "complete"
    failed = "failed"


class AgentStatus(str, Enum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


# ---------------------------------------------------------------------------
# Video Processing
# ---------------------------------------------------------------------------


class VideoProcessJobRequest(BaseModel):
    """Start async video processing for a YouTube video."""

    video_url: str = Field(..., description="YouTube video URL")
    language: Optional[str] = Field("en", description="Transcript language")
    options: Optional[dict[str, Any]] = Field(default_factory=dict)


class VideoProcessJobResponse(BaseModel):
    """Returned when a video processing job is created."""

    job_id: str
    video_url: str
    status: JobStatus = JobStatus.pending


class VideoJobStatusResponse(BaseModel):
    """Returned when polling a video job's status."""

    job_id: str
    status: JobStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    video_url: Optional[str] = None
    transcript: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    error_reason: Optional[str] = Field(
        None,
        description="Machine-readable slug describing why a job failed (e.g. 'gemini_api_timeout')",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp; used by job-store retention (expire_before).",
    )


# ---------------------------------------------------------------------------
# Event Extraction
# ---------------------------------------------------------------------------


class EventExtractRequest(BaseModel):
    """Request to extract events from a transcript."""

    job_id: Optional[str] = Field(None, description="Job ID from video processing")
    transcript: Optional[str] = Field(None, description="Raw transcript text")
    video_url: Optional[str] = None


class ExtractedEvent(BaseModel):
    """A single event extracted from a transcript."""

    id: str
    type: str = Field(..., description="action | mention | topic | insight")
    title: str
    description: Optional[str] = None
    timestamp: Optional[str] = Field(None, description="Time in video, e.g. '02:15'")
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class EventExtractResponse(BaseModel):
    """Response containing extracted events."""

    job_id: Optional[str] = None
    events: list[ExtractedEvent] = Field(default_factory=list)
    event_count: int = 0


# ---------------------------------------------------------------------------
# Agent Dispatch
# ---------------------------------------------------------------------------


class AgentDispatchRequest(BaseModel):
    """Request to dispatch AI agents for a set of events."""

    job_id: Optional[str] = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    transcript: Optional[str] = Field(
        None,
        description="Transcript text — events will be auto-extracted when events list is empty",
    )
    agent_types: Optional[list[str]] = Field(
        None, description="Specific agent types to dispatch"
    )


class AgentExecution(BaseModel):
    """Status of a single dispatched agent execution."""

    agent_id: str
    agent_type: str
    status: AgentStatus = AgentStatus.queued
    progress: float = Field(0.0, ge=0.0, le=100.0)
    event_id: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class AgentDispatchResponse(BaseModel):
    """Response after dispatching agents."""

    dispatch_id: str
    executions: list[AgentExecution] = Field(default_factory=list)


class AgentStatusResponse(BaseModel):
    """Status of a single agent execution."""

    agent_id: str
    agent_type: str
    status: AgentStatus
    progress: float = 0.0
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Transcript Action
# ---------------------------------------------------------------------------


class TranscriptActionRequest(BaseModel):
    """Request body for the /api/v1/transcript-action endpoint."""

    video_url: str = Field(..., description="YouTube video URL to process")
    language: Optional[str] = Field(
        "en",
        description="Optional language code for transcript processing",
    )
    transcript_text: Optional[str] = Field(
        None,
        description="Raw transcript text to process",
    )
    video_options: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional options for video/transcript processing",
    )


class TranscriptActionResponse(BaseModel):
    """Response body from the /api/v1/transcript-action endpoint."""

    success: bool
    video_url: str
    metadata: dict[str, Any]
    transcript: dict[str, Any]
    outputs: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
    orchestration_meta: dict[str, Any]
    async_processing: bool = False
    job_id: Optional[str] = None
    job_status: Optional[JobStatus] = None
    status_url: Optional[str] = None
    processing_transport: Optional[str] = None


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Request to the conversational AI assistant."""

    query: str = Field(..., min_length=1, max_length=2000, description="User message")
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    context: Optional[str] = "tooltip-assistant"
    session_id: Optional[str] = "default"
    history: Optional[list[dict[str, str]]] = None


class ChatResponse(BaseModel):
    """Response from the conversational AI assistant."""

    response: str
    status: str
    session_id: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: Optional[str] = None
    components: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Generic API wrapper
# ---------------------------------------------------------------------------


class ApiResponse(BaseModel):
    """Standardized API response envelope returned by some endpoints."""

    status: str
    data: Optional[Any] = None
    error: Optional[str] = None
    detail: Optional[str] = None
    timestamp: Optional[datetime] = None
    request_id: Optional[str] = None
