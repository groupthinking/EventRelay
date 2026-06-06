"""End-to-end smoke tests for the clean spine, using injected fakes.

The live YouTube/LLM calls cannot run in CI; the transcript provider and model
seam are replaced with fakes via the container. This exercises SC1 validation,
SC5 contract wiring, and the full SC2->SC3->SC4->SC6 lifecycle.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from service.app.container import Container, get_container
from service.app.llm.fake import FakeLLMClient
from service.app.main import create_app
from service.app.pipeline.ingest import InvalidInput, extract_video_id

GOOD_URL = "https://youtu.be/dQw4w9WgXcQ"


class FakeTranscriptProvider:
    def __init__(self, text: str) -> None:
        self._text = text

    async def fetch(self, video_id: str, language: str | None = None) -> str:
        return self._text


@pytest.fixture
def container() -> Container:
    c = get_container()
    c._store = None  # type: ignore[attr-defined]
    c._transcript_provider = None  # type: ignore[attr-defined]
    c._llm = None  # type: ignore[attr-defined]
    return c


@pytest.fixture
def client(container: Container) -> TestClient:
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
    with pytest.raises(InvalidInput):
        extract_video_id(url)


def test_submit_rejects_bad_url(client: TestClient) -> None:
    assert client.post("/api/v1/jobs", json={"video_url": "https://vimeo.com/123"}).status_code == 422


# --- SC6: idempotent job lifecycle ---

def test_submit_is_idempotent(container: Container, client: TestClient) -> None:
    container._transcript_provider = FakeTranscriptProvider("t")  # type: ignore[attr-defined]
    container._llm = FakeLLMClient([{"events": []}, {"summary": "s"}])  # type: ignore[attr-defined]
    first = client.post("/api/v1/jobs", json={"video_url": GOOD_URL}).json()
    second = client.post("/api/v1/jobs", json={"video_url": GOOD_URL}).json()
    assert first["job_id"] == second["job_id"]


# --- SC2 -> SC3 -> SC4 happy path through the seam ---

def test_full_pipeline_success(container: Container, client: TestClient) -> None:
    container._transcript_provider = FakeTranscriptProvider(  # type: ignore[attr-defined]
        "In this video we capture events and ship software."
    )
    container._llm = FakeLLMClient(  # type: ignore[attr-defined]
        [
            {"events": [{"type": "youtube.video.captured", "payload": {"k": "v"}}]},
            {"summary": "A summary", "tasks": ["do x"], "insights": {"topic": "events"}},
        ]
    )
    job_id = client.post("/api/v1/jobs", json={"video_url": GOOD_URL}).json()["job_id"]

    assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "succeeded"
    events = client.get(f"/api/v1/jobs/{job_id}/events").json()["events"]
    assert events[0]["type"] == "youtube.video.captured"
    artifacts = client.get(f"/api/v1/jobs/{job_id}/artifacts").json()["artifacts"]
    assert artifacts["summary"] == "A summary"
    assert "capture" in client.get(f"/api/v1/jobs/{job_id}/transcript").json()["transcript"]


def test_untyped_event_fails_job(container: Container, client: TestClient) -> None:
    # A model returning an off-taxonomy event name must fail the job, not leak
    # an untyped event (SC3).
    container._transcript_provider = FakeTranscriptProvider("text")  # type: ignore[attr-defined]
    container._llm = FakeLLMClient([{"events": [{"type": "NOT-valid"}]}])  # type: ignore[attr-defined]
    job_id = client.post("/api/v1/jobs", json={"video_url": GOOD_URL}).json()["job_id"]
    assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "failed"


# --- SC5: contract generated from the app, residue-free ---

def test_openapi_exposes_clean_surface(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/jobs" in paths
    assert "/api/v1/jobs/{job_id}" in paths
    assert "/mcp" not in paths
    assert not any("a2a" in p for p in paths)
