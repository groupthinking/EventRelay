"""Tests for long-video background processing path.

Verifies that POST /api/v1/process-video with background=True returns a job_id
immediately without blocking the HTTP connection, and that the job can be
polled for status.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.api.v1.models import (  # noqa: E402
    JobStatus,
    VideoProcessingRequest,
)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_video_processing_request_background_defaults_to_false() -> None:
    """background field must default to False for backward compatibility."""
    req = VideoProcessingRequest(
        video_url="https://www.youtube.com/watch?v=auJzb1D-fag"
    )
    assert req.background is False


def test_video_processing_request_background_can_be_set() -> None:
    """background=True must be accepted."""
    req = VideoProcessingRequest(
        video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        background=True,
    )
    assert req.background is True


# ---------------------------------------------------------------------------
# Endpoint tests – use TestClient so we can exercise the real router logic
# ---------------------------------------------------------------------------


def _make_app() -> Any:
    """Build a minimal FastAPI app with the v1 router mounted."""
    from fastapi import FastAPI
    from youtube_extension.backend.api.v1.router import router

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.asyncio
async def test_background_true_returns_job_id_immediately() -> None:
    """When background=True, the endpoint returns a job_id without waiting."""
    from httpx import ASGITransport, AsyncClient

    # Patch the slow workflow so the asyncio task never actually runs
    mock_workflow = AsyncMock(return_value={"success": True, "transcript": {}, "outputs": {}})

    with patch(
        "youtube_extension.services.workflows.transcript_action_workflow.TranscriptActionWorkflow.run",
        mock_workflow,
    ):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/process-video",
                json={
                    "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "background": True,
                },
            )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "job_id" in data, f"Expected job_id in response, got: {data}"
    assert data["status"] == JobStatus.pending
    assert data["video_url"] == "https://www.youtube.com/watch?v=auJzb1D-fag"


@pytest.mark.asyncio
async def test_background_false_uses_synchronous_path() -> None:
    """When background=False (default), the endpoint awaits the result."""
    from httpx import ASGITransport, AsyncClient

    # Patch VideoProcessingService.process_video_basic so the service container
    # path is short-circuited at the method level.
    with patch(
        "youtube_extension.backend.services.video_processing_service.VideoProcessingService.process_video_basic",
        new=AsyncMock(return_value={"video_id": "auJzb1D-fag", "status": "ok"}),
    ):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/process-video",
                json={"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"},
            )

    assert response.status_code == 200, response.text
    data = response.json()
    # Synchronous path returns the raw result dict, not a job object
    assert "job_id" not in data


@pytest.mark.asyncio
async def test_background_job_status_polling() -> None:
    """A created background job can be polled at GET /api/v1/videos/{job_id}/status."""
    from httpx import ASGITransport, AsyncClient

    never_completes = asyncio.Event()

    async def slow_workflow(*_args: Any, **_kwargs: Any) -> dict:
        await never_completes.wait()  # blocks indefinitely
        return {}

    with patch(
        "youtube_extension.services.workflows.transcript_action_workflow.TranscriptActionWorkflow.run",
        side_effect=slow_workflow,
    ):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Start background job
            start_resp = await client.post(
                "/api/v1/process-video",
                json={
                    "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "background": True,
                },
            )
            assert start_resp.status_code == 200
            job_id = start_resp.json()["job_id"]

            # Poll status – job should be in pending/downloading/transcribing state
            status_resp = await client.get(f"/api/v1/videos/{job_id}/status")

    assert status_resp.status_code == 200, status_resp.text
    status_data = status_resp.json()
    # ApiResponse wraps the job under "data"; verify the job is in an
    # in-progress state (not completed/failed) because processing is blocked.
    assert status_data.get("status") == "success"
    job_data = status_data.get("data", {})
    assert job_data.get("status") in (
        JobStatus.pending,
        JobStatus.downloading,
        JobStatus.transcribing,
    ), f"Unexpected job status: {job_data.get('status')}"
