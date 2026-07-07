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


def test_audit_store_records_token_counts(tmp_path):
    """append() should persist input_tokens and output_tokens when supplied."""
    store = PipelineAuditStore(tmp_path)
    store.append(
        "run_token_test",
        agent_id="gemini-agent",
        action="analyze",
        success=True,
        duration_ms=150.0,
        input_tokens=500,
        output_tokens=250,
    )
    entries = store.get_run("run_token_test")
    assert len(entries) == 1
    assert entries[0]["input_tokens"] == 500
    assert entries[0]["output_tokens"] == 250


def test_audit_store_token_counts_default_to_none(tmp_path):
    """Token counts should be None when not supplied (backward-compatible)."""
    store = PipelineAuditStore(tmp_path)
    store.append(
        "run_no_tokens",
        agent_id="video-ingest",
        action="ingest",
        success=True,
        duration_ms=20.0,
    )
    entries = store.get_run("run_no_tokens")
    assert entries[0]["input_tokens"] is None
    assert entries[0]["output_tokens"] is None


def test_audit_store_token_counts_persist_to_disk(tmp_path):
    """Token counts survive a reload from the JSONL file, not just the in-memory buffer."""
    store = PipelineAuditStore(tmp_path)
    store.append(
        "run_disk_test",
        agent_id="gemini-agent",
        action="analyze",
        success=True,
        duration_ms=42.0,
        input_tokens=10,
        output_tokens=20,
    )

    # A brand-new instance has an empty in-memory buffer, forcing get_run() to
    # read the persisted JSONL file from disk.
    fresh_store = PipelineAuditStore(tmp_path)
    entries = fresh_store.get_run("run_disk_test")

    assert len(entries) == 1
    assert entries[0]["input_tokens"] == 10
    assert entries[0]["output_tokens"] == 20


def test_job_store_expire_before_removes_old_jobs(tmp_path):
    """expire_before() should delete jobs whose created_at is before the cutoff."""
    from datetime import datetime, timedelta, timezone

    store = PipelineJobStore(tmp_path)
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    new_ts = datetime.now(timezone.utc).isoformat()
    store.save("old_job", {"job_id": "old_job", "status": "complete", "created_at": old_ts})
    store.save("new_job", {"job_id": "new_job", "status": "pending", "created_at": new_ts})

    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    removed = store.expire_before(cutoff)

    assert removed == 1
    assert store.load("old_job") is None
    assert store.load("new_job") is not None


def test_job_store_expire_before_skips_missing_created_at(tmp_path):
    """Jobs without a created_at field are left untouched by expire_before()."""
    from datetime import datetime, timezone

    store = PipelineJobStore(tmp_path)
    store.save("no_ts_job", {"job_id": "no_ts_job", "status": "pending"})

    removed = store.expire_before(datetime.now(timezone.utc))

    assert removed == 0
    assert store.load("no_ts_job") is not None


def test_job_store_expire_before_skips_empty_created_at(tmp_path):
    """An empty-string created_at is treated the same as a missing field."""
    from datetime import datetime, timezone

    store = PipelineJobStore(tmp_path)
    store.save("blank_ts_job", {"job_id": "blank_ts_job", "status": "pending", "created_at": ""})

    removed = store.expire_before(datetime.now(timezone.utc))

    assert removed == 0
    assert store.load("blank_ts_job") is not None


def test_job_store_expire_before_skips_unparseable_created_at(tmp_path):
    """A created_at value that isn't a valid ISO timestamp is left alone rather than raising."""
    from datetime import datetime, timezone

    store = PipelineJobStore(tmp_path)
    store.save(
        "bad_ts_job",
        {"job_id": "bad_ts_job", "status": "pending", "created_at": "not-a-timestamp"},
    )

    removed = store.expire_before(datetime.now(timezone.utc))

    assert removed == 0
    assert store.load("bad_ts_job") is not None


def test_job_store_expire_before_ignores_corrupt_json_file(tmp_path):
    """A job file with invalid JSON is skipped instead of raising."""
    from datetime import datetime, timezone

    store = PipelineJobStore(tmp_path)
    corrupt_path = tmp_path / "corrupt_job.json"
    corrupt_path.write_text("{not valid json", encoding="utf-8")

    removed = store.expire_before(datetime.now(timezone.utc))

    assert removed == 0
    assert corrupt_path.exists()


def test_job_store_expire_before_boundary_not_removed(tmp_path):
    """A job created exactly at the cutoff instant is not removed (strict less-than)."""
    from datetime import datetime, timezone

    store = PipelineJobStore(tmp_path)
    cutoff = datetime.now(timezone.utc)
    store.save(
        "boundary_job",
        {"job_id": "boundary_job", "status": "complete", "created_at": cutoff.isoformat()},
    )

    removed = store.expire_before(cutoff)

    assert removed == 0
    assert store.load("boundary_job") is not None


def test_job_store_expire_before_accepts_naive_cutoff(tmp_path):
    """A naive (tzinfo-less) cutoff is coerced to UTC instead of raising."""
    from datetime import datetime, timedelta, timezone

    store = PipelineJobStore(tmp_path)
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    store.save("old_job_naive_cutoff", {"job_id": "old_job_naive_cutoff", "status": "complete", "created_at": old_ts})

    # Anchor the naive cutoff to a UTC base so the test is timezone-independent:
    # expire_before() reinterprets a naive cutoff as UTC, so building it from a
    # local now() would drift the cutoff earlier than old_ts west of UTC.
    naive_cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
    removed = store.expire_before(naive_cutoff)

    assert removed == 1
    assert store.load("old_job_naive_cutoff") is None


def test_job_store_expire_before_removes_multiple_matching_jobs(tmp_path):
    """expire_before() removes every job older than the cutoff, not just the first match."""
    from datetime import datetime, timedelta, timezone

    store = PipelineJobStore(tmp_path)
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    for job_id in ("old_a", "old_b", "old_c"):
        store.save(job_id, {"job_id": job_id, "status": "complete", "created_at": old_ts})
    new_ts = datetime.now(timezone.utc).isoformat()
    store.save("new_job", {"job_id": "new_job", "status": "pending", "created_at": new_ts})

    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    removed = store.expire_before(cutoff)

    assert removed == 3
    for job_id in ("old_a", "old_b", "old_c"):
        assert store.load(job_id) is None
    assert store.load("new_job") is not None


def test_persisted_video_job_is_expirable(tmp_path):
    """A real VideoJobStatusResponse persisted like production must be expirable.

    Regression for the CodeRabbit/Copilot finding on #479: expire_before() was a
    no-op because VideoJobStatusResponse carried no created_at, so its persisted
    model_dump() never matched. The model now supplies a UTC created_at at
    construction, and persistence uses model_dump(mode="json") so it serialises to
    an ISO string that expire_before() can parse.
    """
    from datetime import datetime, timedelta, timezone

    from youtube_extension.backend.api.v1.models import (
        JobStatus,
        VideoJobStatusResponse,
    )

    job = VideoJobStatusResponse(job_id="real_job", status=JobStatus.pending)
    assert job.created_at.tzinfo is not None  # tz-aware UTC by default

    payload = job.model_dump(mode="json")
    assert isinstance(payload["created_at"], str)  # JSON-serialisable

    store = PipelineJobStore(tmp_path)
    store.save("real_job", payload)

    cutoff = datetime.now(timezone.utc) + timedelta(hours=1)
    assert store.expire_before(cutoff) == 1
    assert store.load("real_job") is None


def test_persist_video_job_stamps_stable_created_at(tmp_path, monkeypatch):
    """Persisted job records carry a created_at (so expire_before() works on real
    data), and it stays stable across the many status-transition re-persists."""
    from youtube_extension.backend.api.v1 import router as router_module
    from youtube_extension.backend.api.v1.models import (
        JobStatus,
        VideoJobStatusResponse,
    )
    from youtube_extension.services.pipeline_job_store import PipelineJobStore

    store = PipelineJobStore(tmp_path)
    monkeypatch.setattr(router_module, "get_job_store", lambda: store)

    job = VideoJobStatusResponse(job_id="job_persist_1", status=JobStatus.pending)
    router_module._persist_video_job(job)
    first = store.load("job_persist_1")
    assert isinstance(first, dict)
    assert isinstance(first.get("created_at"), str) and first["created_at"]

    # A later status update must not overwrite the original created_at.
    job.status = JobStatus.complete
    router_module._persist_video_job(job)
    second = store.load("job_persist_1")
    assert second["created_at"] == first["created_at"]


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


def test_sentry_smoke_endpoint_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from youtube_extension.main import app

    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "1")
    client = TestClient(app, raise_server_exceptions=False)
    monkeypatch.delenv("ALLOW_SENTRY_SMOKE", raising=False)
    assert client.post("/test-sentry").status_code == 404

    monkeypatch.setenv("ALLOW_SENTRY_SMOKE", "1")
    response = client.post("/test-sentry")
    assert response.status_code == 500
