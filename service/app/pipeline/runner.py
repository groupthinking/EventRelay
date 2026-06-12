"""The linear pipeline (SC1 -> SC2 -> SC3 -> SC4) with job lifecycle (SC6).

One orchestration path. Dependencies (transcript provider, model seam) are
resolved from the container *inside* the job so that a misconfiguration (e.g. no
LLM key) lands on the job's status as `failed` instead of failing the request.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..api.v1.schemas import JobStatus
from .artifacts import derive_artifacts
from .extract import extract_events

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..container import Container


async def run_job(
    job_id: str, video_id: str, container: Container, language: str | None = None
) -> None:
    """
    Orchestrates a single pipeline job: fetches the transcript, derives events and artifacts, persists results, and records job status.
    
    Parameters:
        job_id (str): Identifier of the job to run.
        video_id (str): Identifier of the video to process.
        container (Container): Dependency container providing `store`, `transcript_provider`, and `llm`.
        language (str | None): Optional language hint passed to the transcript provider.
    
    Notes:
        - Sets the job status to `running` at start, `succeeded` on successful completion, and `failed` if any exception occurs.
        - Persists `transcript`, `events`, and `artifacts` to the store.
    """
    store = container.store
    await store.update_status(job_id, JobStatus.running)
    try:
        transcript = await container.transcript_provider.fetch(video_id, language)  # SC2
        llm = container.llm
        events = await extract_events(transcript, llm)                              # SC3
        artifacts = await derive_artifacts(transcript, events, llm)                 # SC4
        await store.save_results(
            job_id, transcript=transcript, events=events, artifacts=artifacts
        )
        await store.update_status(job_id, JobStatus.succeeded)
    except Exception as exc:  # noqa: BLE001 — terminal stage records the failure
        logger.error(
            "run_job: pipeline failed",
            extra={"job_id": job_id, "video_id": video_id},
            exc_info=True,
        )
        await store.update_status(job_id, JobStatus.failed, error="Pipeline failed")
