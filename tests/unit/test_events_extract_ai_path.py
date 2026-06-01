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


def _disable_gateway(monkeypatch):
    """Force the Vercel AI Gateway off so a test exercises only the local path."""
    from youtube_extension.services.ai import vercel_gateway_provider as gw

    monkeypatch.setattr(gw, "gateway_available", lambda: False)


def test_ai_path_passes_input_data_and_parses_response(monkeypatch):
    """A real (non-mock) Gemini response must be parsed from `.response`."""
    _disable_gateway(monkeypatch)
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
    _disable_gateway(monkeypatch)
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


def test_vercel_gateway_events_flow_through(monkeypatch):
    """When direct Gemini is unavailable, gateway-extracted events are used."""
    # Direct Gemini returns mock -> rejected, so the gateway path engages.
    _patch_process(
        monkeypatch,
        response="ignored mock",
        backend="mock",
    )
    from youtube_extension.services.ai import vercel_gateway_provider as gw

    monkeypatch.setattr(gw, "gateway_available", lambda: True)
    monkeypatch.setattr(
        gw,
        "extract_events",
        lambda transcript, *a, **k: [
            {
                "type": "action",
                "title": "Install n8n",
                "description": None,
                "timestamp": "00:10",
            },
            {
                "type": "insight",
                "title": "Agents need tools",
                "description": "d",
                "timestamp": None,
            },
        ],
    )

    resp = client.post(
        "/api/v1/events/extract",
        json={"transcript": "Some real transcript about building agents."},
    )
    assert resp.status_code == 200
    events = resp.json()["data"]["events"]
    titles = [e["title"] for e in events]
    assert "Install n8n" in titles and "Agents need tools" in titles
    # Gateway-provided type and timestamp are preserved.
    install = next(e for e in events if e["title"] == "Install n8n")
    assert install["type"] == "action"
    assert install["timestamp"] == "00:10"


def test_empty_transcript_rejected():
    resp = client.post("/api/v1/events/extract", json={"transcript": ""})
    assert resp.status_code == 400


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
