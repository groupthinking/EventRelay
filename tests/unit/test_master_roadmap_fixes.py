"""Regression tests for master roadmap phase fixes."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

# Agents import chain calls load_dotenv(override=True); accept kwargs on any stub.
_dotenv = sys.modules.get("dotenv") or types.ModuleType("dotenv")
_dotenv.load_dotenv = lambda *args, **kwargs: None
sys.modules["dotenv"] = _dotenv

import pytest

from youtube_extension.services.pipeline_audit_store import PipelineAuditStore
from youtube_extension.services.pipeline_job_store import PipelineJobStore


def test_job_store_roundtrip(tmp_path):
    store = PipelineJobStore(tmp_path)
    payload = {"job_id": "job_test123", "status": "pending", "progress": 0.0}
    store.save("job_test123", payload)
    loaded = store.load("job_test123")
    assert loaded == payload


def test_audit_store_append_and_read(tmp_path):
    store = PipelineAuditStore(tmp_path)
    store.append(
        "run_001",
        agent_id="video-ingest",
        action="ingest",
        success=True,
        duration_ms=12.5,
    )
    entries = store.get_run("run_001")
    assert len(entries) == 1
    assert entries[0]["agent_id"] == "video-ingest"


def test_vera_pre_check_gateway_exception_does_not_crash():
    from agents.pipeline_orchestrator import VideoPipelineOrchestrator

    orchestrator = VideoPipelineOrchestrator()
    fake_vera = {
        "breakers": MagicMock(),
        "gateway": MagicMock(),
        "firewall": MagicMock(),
        "enforcer": MagicMock(),
        "identity": MagicMock(),
        "maturity": MagicMock(),
    }
    fake_vera["breakers"].get_breaker.return_value.allow_action.return_value = True
    fake_vera["gateway"].check_permission.side_effect = RuntimeError("gateway down")
    fake_vera["firewall"].scan_input.return_value = MagicMock(
        action=MagicMock(value="allow")
    )

    with patch.object(orchestrator, "_vera", fake_vera):
        with patch.object(
            orchestrator, "_vera_credentials", {"agent-x": (None, None)}
        ):
            result = orchestrator._vera_pre_check(
                "agent-x", "Agent X", "test_action", {"k": "v"}
            )

    assert result is None


@pytest.mark.asyncio
async def test_run_pipeline_resets_results_between_runs():
    from agents.pipeline_orchestrator import PipelineResult, VideoPipelineOrchestrator

    orchestrator = VideoPipelineOrchestrator()
    orchestrator.results = {
        "stale": PipelineResult("stale", True, {}, 1.0, None)
    }

    with patch.object(
        orchestrator,
        "_run_sequential_pipeline",
        return_value={"success": True},
    ):
        await orchestrator.run_pipeline("https://youtu.be/jNQXAC9IVRw")

    assert orchestrator.results == {}


def test_sentry_smoke_endpoint_gated(monkeypatch):
    from fastapi.testclient import TestClient

    from youtube_extension.main import app

    client = TestClient(app)
    monkeypatch.delenv("ALLOW_SENTRY_SMOKE", raising=False)
    assert client.post("/test-sentry").status_code == 404

    monkeypatch.setenv("ALLOW_SENTRY_SMOKE", "1")
    gated_client = TestClient(app, raise_server_exceptions=False)
    response = gated_client.post("/test-sentry")
    assert response.status_code == 500
