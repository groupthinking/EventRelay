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
    """
    Run the linear pipeline for a queued job and persist its outputs while updating job status.
    
    Executes the pipeline stages for the given video and saves the resulting transcript, extracted events, and derived artifacts to `store`. Updates the job status to `running` before execution, to `succeeded` after results are saved, and to `failed` with an error message if any exception occurs. Idempotency is handled at submit time by the store's `create_or_get`; this runner advances an existing job.
    
    Parameters:
        job_id (str): Identifier of the job to run and update in `store`.
        video_id (str): Identifier of the video to process.
        store (JobStore): Persistent store used to update status and save results.
        language (str | None): Optional language hint for transcript fetching; pass `None` to use defaults.
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
