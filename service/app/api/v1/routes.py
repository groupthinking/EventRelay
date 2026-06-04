"""v1 routes — the clean, job-centric contract surface (SC5).

Thin handlers: validate, enqueue, read. No business logic lives here — it is in
the pipeline. The legacy 40-path contract (including /mcp, agents/a2a,
video-to-software, and the duplicate legacy /api/* routes) is not reproduced.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from ...config import get_settings
from ...container import get_store
from ...pipeline.ingest import InvalidInput, extract_video_id
from ...pipeline.runner import run_job
from ...store.base import JobStore
from .schemas import (
    ArtifactsView,
    EventsView,
    HealthResponse,
    JobView,
    SubmitJobRequest,
    SubmitJobResponse,
    TranscriptView,
)

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    """
    Return service health information including the application version.
    
    Returns:
        HealthResponse: Object containing the `version` field set to the application's version.
    """
    return HealthResponse(version=get_settings().app_version)


@router.post(
    "/jobs",
    response_model=SubmitJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
async def submit_job(
    req: SubmitJobRequest,
    background: BackgroundTasks,
    store: JobStore = Depends(get_store),
) -> SubmitJobResponse:
    """
    Validate the provided video URL, create or retrieve an idempotent job record, and schedule pipeline execution for newly created jobs.
    
    Parameters:
    	req (SubmitJobRequest): Request payload containing `video_url` (validated) and `language` forwarded to the pipeline.
    
    Returns:
    	SubmitJobResponse: Response containing the created or existing `job_id` and its current `status`.
    
    Raises:
    	HTTPException: With status 422 when `video_url` validation fails.
    """
    try:
        video_id = extract_video_id(req.video_url)
    except InvalidInput as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    idempotency_key = f"{video_id}:{get_settings().pipeline_version}"
    record, created = await store.create_or_get(req.video_url, idempotency_key)
    if created:
        background.add_task(run_job, record.job_id, video_id, store, req.language)
    return SubmitJobResponse(job_id=record.job_id, status=record.status)


@router.get("/jobs/{job_id}", response_model=JobView, tags=["jobs"])
async def get_job(job_id: str, store: JobStore = Depends(get_store)) -> JobView:
    """
    Retrieve a job record by its identifier and return its public view.
    
    Returns:
        JobView: An object containing `job_id`, `status`, `video_url`, `created_at`, `updated_at`, and `error` from the stored record.
    
    Raises:
        HTTPException: with status code 404 when the job is not found.
    """
    rec = await store.get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobView(
        job_id=rec.job_id,
        status=rec.status,
        video_url=rec.video_url,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        error=rec.error,
    )


@router.get("/jobs/{job_id}/transcript", response_model=TranscriptView, tags=["jobs"])
async def get_transcript(job_id: str, store: JobStore = Depends(get_store)) -> TranscriptView:
    """
    Fetches the transcript for the specified job.
    
    Returns:
        TranscriptView: The transcript view containing the job's id and transcript text.
    
    Raises:
        HTTPException: 404 if the job does not exist or the transcript is not available.
    """
    rec = await store.get(job_id)
    if rec is None or rec.transcript is None:
        raise HTTPException(status_code=404, detail="transcript not available")
    return TranscriptView(job_id=rec.job_id, transcript=rec.transcript)


@router.get("/jobs/{job_id}/events", response_model=EventsView, tags=["jobs"])
async def get_events(job_id: str, store: JobStore = Depends(get_store)) -> EventsView:
    """
    Retrieve a job's event stream.
    
    Returns:
        EventsView: An object containing the job's `job_id` and its stored `events`.
    
    Raises:
        HTTPException: 404 if the job does not exist.
    """
    rec = await store.get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="job not found")
    return EventsView(job_id=rec.job_id, events=rec.events)


@router.get("/jobs/{job_id}/artifacts", response_model=ArtifactsView, tags=["jobs"])
async def get_artifacts(job_id: str, store: JobStore = Depends(get_store)) -> ArtifactsView:
    """
    Return the stored artifacts for the specified job.
    
    Returns:
        ArtifactsView: View containing `job_id` and the job's stored `artifacts`.
    
    Raises:
        HTTPException: with status 404 and detail "artifacts not available" if the job is missing or has no artifacts.
    """
    rec = await store.get(job_id)
    if rec is None or rec.artifacts is None:
        raise HTTPException(status_code=404, detail="artifacts not available")
    return ArtifactsView(job_id=rec.job_id, artifacts=rec.artifacts)
