"""The linear pipeline (SC1 -> SC2 -> SC3 -> SC4) with job lifecycle (SC6).

This is the single orchestration path. There is no agent mesh, no MCP
coordinator, no workflow engine — the product is a linear transform and the
runner reflects that.
"""
from __future__ import annotations

from ..api.v1.schemas import JobStatus
from ..store.base import JobStore
from . import artifacts, extract, transcript


async def run_job(job_id: str, video_id: str, store: JobStore, language: str | None = None) -> None:
    """Execute the pipeline for a queued job, updating status as it goes.

    Idempotency (SC6) is handled at submit time by the store's create_or_get;
    this runner only advances an existing job.
    """
    await store.update_status(job_id, JobStatus.running)
    try:
        text = await transcript.fetch_transcript(video_id, language)  # SC2
        events = await extract.extract_events(text)                   # SC3
        derived = await artifacts.derive_artifacts(text, events)      # SC4
        await store.save_results(job_id, transcript=text, events=events, artifacts=derived)
        await store.update_status(job_id, JobStatus.succeeded)
    except Exception as exc:  # noqa: BLE001 — terminal stage records the failure
        await store.update_status(job_id, JobStatus.failed, error=str(exc))
