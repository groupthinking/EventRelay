"""Regression tests for the AI event-extraction path in /api/v1/events/extract.

These lock in the fix for a latent bug where the endpoint called
``HybridProcessorService.process(prompt=...)`` -- omitting the required
``input_data`` positional argument and parsing the result as a dict
(``.get("text")``) instead of the ``HybridResult.response`` field. The result
was that the AI path raised ``TypeError`` on every request and silently fell
back to the heuristic extractor, even when a real Gemini key was configured.

The tests use a lightweight duck-typed stand-in for ``HybridResult`` so they
do not require any API key or network access (REAL_MODE_ONLY compliant: no
mocked *successes* are asserted against real providers -- we assert the
router's own wiring).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from youtube_extension.main import app

client = TestClient(app)


def _patch_process(monkeypatch, *, response: str, backend: str, success: bool = True):
    """Patch HybridProcessorService.process and capture how it was called."""
    from youtube_extension.backend.api.v1 import router as router_mod

    calls: dict = {}

    async def fake_process(self, *args, **kwargs):  # noqa: ANN001
        calls["args"] = args
        calls["kwargs"] = kwargs
        return SimpleNamespace(
            success=success,
            response=response,
            cloud_result=SimpleNamespace(backend=backend),
        )

    monkeypatch.setattr(
        router_mod.HybridProcessorService, "process", fake_process, raising=True
    )
    return calls


def test_ai_path_passes_input_data_and_parses_response(monkeypatch):
    """A real (non-mock) Gemini response must be parsed from `.response`."""
    calls = _patch_process(
        monkeypatch,
        response="- Build the agent\n- Deploy to the cloud",
        backend="gemini",
    )

    resp = client.post(
        "/api/v1/events/extract",
        json={"transcript": "Today we build an agent and then deploy it."},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    # The AI response (two lines) was used, not the heuristic.
    titles = [e["title"] for e in data["events"]]
    assert "Build the agent" in titles
    assert "Deploy to the cloud" in titles

    # The signature bug is fixed: input_data was supplied (positionally or by kw).
    assert ("input_data" in calls["kwargs"]) or (len(calls["args"]) >= 1)


def test_mock_backend_falls_back_to_heuristic(monkeypatch):
    """REAL_MODE_ONLY: a mocked AI response must NOT become extracted events."""
    _patch_process(
        monkeypatch,
        response="- This should be ignored because it is mock output",
        backend="mock",
    )

    transcript = "Build the workflow. Configure the trigger. Deploy the automation."
    resp = client.post("/api/v1/events/extract", json={"transcript": transcript})
    assert resp.status_code == 200
    titles = [e["title"] for e in resp.json()["data"]["events"]]

    # None of the events come from the mock response; they come from the
    # deterministic heuristic splitting the real transcript instead.
    assert not any("mock output" in t for t in titles)
    assert any("Build the workflow" in t for t in titles)


def test_empty_transcript_rejected():
    resp = client.post("/api/v1/events/extract", json={"transcript": ""})
    assert resp.status_code == 400


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
