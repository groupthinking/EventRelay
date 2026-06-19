"""Smoke tests for the clean spine skeleton.

Covers what the skeleton actually implements: SC1 validation, SC5 contract
wiring, and the SC6 job lifecycle up to the first unimplemented stage. The
SC2/SC3/SC4 stages are intentionally NotImplementedError until ported, and the
runner is expected to record that as a failed job — which is asserted here.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from service.app.container import Container, get_container
from service.app.main import create_app
from service.app.pipeline.ingest import InvalidInput, extract_video_id


@pytest.fixture
def client() -> TestClient:
    # Fresh in-memory store per test.
    """
    Create a TestClient for the application with a fresh in-memory container store.
    
    Resets the application's in-memory container store to None before creating the client to ensure each test runs with a fresh store.
    
    Returns:
        TestClient: A TestClient instance created from create_app().
    """
    get_container()._store = None  # type: ignore[attr-defined]
    return TestClient(create_app())


# --- SC1: input ingest & validation ---

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_extract_video_id_valid(url: str, expected: str) -> None:
    assert extract_video_id(url) == expected


@pytest.mark.parametrize(
    "url",
    ["", "ftp://youtube.com/watch?v=x", "https://vimeo.com/123", "https://youtube.com/watch?v=short"],
)
def test_extract_video_id_invalid(url: str) -> None:
    """
    Asserts that `extract_video_id` raises `InvalidInput` when given an unsupported or malformed video URL.
    
    Parameters:
        url (str): A URL string expected to be invalid for video ID extraction.
    """
    with pytest.raises(InvalidInput):
        extract_video_id(url)


def test_submit_rejects_bad_url(client: TestClient) -> None:
    resp = client.post("/api/v1/jobs", json={"video_url": "https://vimeo.com/123"})
    assert resp.status_code == 422


# --- SC6: idempotent job lifecycle ---

def test_submit_is_idempotent(client: TestClient) -> None:
    body = {"video_url": "https://youtu.be/dQw4w9WgXcQ"}
    first = client.post("/api/v1/jobs", json=body).json()
    second = client.post("/api/v1/jobs", json=body).json()
    assert first["job_id"] == second["job_id"]


def test_job_fails_until_pipeline_ported(client: TestClient) -> None:
    # The background task runs synchronously under TestClient; SC2 is not yet
    # ported, so the job must terminate as 'failed', not hang or fake success.
    """
    Verify that a submitted job terminates with a failed status while the SC2 pipeline stage is unimplemented.
    
    Submits a job for a known YouTube URL, retrieves the job, and asserts the job's "status" is "failed" and its "error" field contains "SC2".
    """
    submit = client.post("/api/v1/jobs", json={"video_url": "https://youtu.be/dQw4w9WgXcQ"})
    job_id = submit.json()["job_id"]
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "SC2" in (job["error"] or "")


# --- SC5: contract is generated from the app ---

def test_openapi_exposes_clean_surface(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/jobs" in paths
    assert "/api/v1/jobs/{job_id}" in paths
    # Residue from the legacy contract must NOT appear.
    assert "/mcp" not in paths
    assert not any("a2a" in p for p in paths)
