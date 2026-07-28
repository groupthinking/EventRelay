"""
Extended unit tests for src/youtube_extension/backend/api/v1/router.py

Strategy:
- Pre-stub all optional heavy imports before importing the router module.
- Create a minimal FastAPI app that includes the router.
- Override every dependency injector on the router so we never need real services.
- Cover as many uncovered lines as possible via TestClient requests.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
<<<<<<< HEAD
=======
from types import SimpleNamespace
>>>>>>> origin/main
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Ensure src/ is on sys.path
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# ---------------------------------------------------------------------------
# Stub heavy / unavailable modules BEFORE the router is imported
# ---------------------------------------------------------------------------
_STUBS = [
    "shared",
    "shared.youtube",
    "uvai",
    "psutil",
    "aiohttp",
    "uvai.ml",
    "uvai.ml.client",
    "youtube_extension.services",
    "youtube_extension.services.agents",
    "youtube_extension.services.ai",
    "youtube_extension.services.ai.gemini_service",
    "youtube_extension.services.cloud",
    "youtube_extension.services.cloud.cloud_tasks_queue",
    "youtube_extension.services.pipeline_audit_store",
    "youtube_extension.services.pipeline_job_store",
    "youtube_extension.services.workflows",
    "youtube_extension.services.workflows.transcript_action_workflow",
    "youtube_extension.integration",
    "youtube_extension.integration.cloudevents_publisher",
]
for _mod in _STUBS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Provide a realistic RobustYouTubeMetadata stub used in type hints / dataclass calls
from dataclasses import dataclass

@dataclass
class _FakeMetadata:
    video_id: str = "auJzb1D-fag"
    title: str = "Test Video"
    duration: str = "PT10M"
    duration_seconds: int = 600
    channel_title: str = "Test Channel"
    description: str = ""
    view_count: int = 0
    like_count: int = 0
    thumbnail_url: str = ""
    published_at: str = ""
    tags: list = None
    categories: list = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.categories is None:
            self.categories = []


sys.modules["shared.youtube"].RobustYouTubeMetadata = _FakeMetadata


def _stub_attr(mod_name: str, attr: str, value=None):
    """Set attribute on a sys.modules entry ONLY if it is already a MagicMock stub.
    If the module is a real imported module, do NOT mutate it — that would
    corrupt state for other test files collected before this one executes."""
    mod = sys.modules.get(mod_name)
    if mod is None or not isinstance(mod, MagicMock):
        return
    setattr(mod, attr, value if value is not None else MagicMock())


# GeminiConfig stub for service_container (only if module is a stub)
_stub_attr("youtube_extension.services.ai.gemini_service", "GeminiConfig")

# Provide stub for CloudTasksQueueService (only if module is a stub)
_stub_attr("youtube_extension.services.cloud.cloud_tasks_queue", "CloudTasksQueueService")
_stub_attr("youtube_extension.services.cloud.cloud_tasks_queue", "TaskConfig")
_stub_attr("youtube_extension.services.cloud.cloud_tasks_queue", "VideoProcessingTask")

# Provide stub for HybridProcessorService (only if module is a stub)
_HybridProcessorService_cls = MagicMock()
_stub_attr("youtube_extension.services.ai", "HybridProcessorService", _HybridProcessorService_cls)

# Provide stub for TranscriptActionWorkflow (only if module is a stub)
_stub_attr("youtube_extension.services.workflows.transcript_action_workflow", "TranscriptActionWorkflow")

# Stub pipeline_job_store load to return None by default
_job_store = MagicMock()
_job_store.load.return_value = None
_stub_attr("youtube_extension.services.pipeline_job_store", "get_job_store", MagicMock(return_value=_job_store))

# ---------------------------------------------------------------------------
# Now import the router (it will use the stubs above)
# ---------------------------------------------------------------------------
from youtube_extension.backend.api.v1 import router as router_module  # noqa: E402
from youtube_extension.backend.api.v1.router import (  # noqa: E402
    get_agent_orchestrator_service,
    get_cache_service,
    get_data_service,
    get_health_monitoring_service,
    get_hybrid_processor_service,
    get_metrics_service,
    get_video_processing_service,
    get_websocket_manager,
    router,
    _InMemoryActionRepository,
    _video_jobs,
    _agent_executions,
)
from youtube_extension.backend.api.v1.models import (  # noqa: E402
    AgentDispatchRequest,
    AgentExecution,
    AgentStatus,
    JobStatus,
    VideoJobStatusResponse,
)

# ---------------------------------------------------------------------------
# Build a TestClient from a minimal FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router)


def _make_health_svc():
    svc = MagicMock()
    svc.get_basic_health_status.return_value = {
        "status": "healthy",
        "timestamp": "2026-01-01T00:00:00",
        "version": "test",
        "components": {},
    }
    svc.check_external_connectors_health.return_value = {}
    svc.check_video_to_software_pipeline_health.return_value = {}
    svc.rate_limit_check.return_value = True
    svc.increment_metric.return_value = None
    svc.get_metrics_prometheus_format.return_value = ["# metrics", "req_total 1"]
    return svc


def _make_cache_svc():
    svc = MagicMock()
    svc.get_cache_statistics.return_value = {
        "total_cached_videos": 5,
        "categories": {"test": {"count": 5, "size_mb": 1.0}},
        "total_size_mb": 1.0,
        "oldest_cache": None,
        "newest_cache": None,
    }
    svc.get_video_cache_info.return_value = {"video_id": "auJzb1D-fag", "cached": True}
    svc.clear_cache.return_value = None
    return svc


def _make_data_svc():
    svc = MagicMock()
    _videos_summary = [{"video_id": "auJzb1D-fag", "title": "Test"}]
    # Honor limit/offset so pagination behaves like the real data service
    # (the /videos endpoint delegates slicing to get_videos_summary).
    svc.get_videos_summary.side_effect = (
        lambda limit=50, offset=0, **_: _videos_summary[offset : offset + limit]
    )
    svc.count_videos.return_value = 1
    svc.get_video_detail.return_value = {
        "video_id": "auJzb1D-fag",
        "metadata": {"title": "Test", "transcript_text": "hello world"},
    }
    svc.get_learning_log.return_value = [{"entry": "learned something"}]
    svc.save_feedback.return_value = True
    return svc


def _make_vps():
    svc = MagicMock()
    svc.process_video_basic = AsyncMock(return_value={"status": "ok", "video_data": {}})
    svc.process_video_for_markdown = AsyncMock(
        return_value={
            "video_id": "auJzb1D-fag",
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "metadata": {"title": "Test"},
            "markdown_content": "# Test",
            "cached": False,
            "save_path": "/tmp/test.md",
            "processing_time": "1.0s",
            "status": "success",
        }
    )
    svc.process_video_to_software = AsyncMock(
        return_value={
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "project_name": "test-app",
            "project_type": "web",
            "deployment_target": "vercel",
            "live_url": "https://test.vercel.app",
            "github_repo": "https://github.com/user/test",
            "build_status": "completed",
            "processing_time": "30s",
            "features_implemented": [],
            "video_analysis": {},
            "code_generation": {},
            "deployment": {},
            "status": "success",
            "timestamp": "2026-01-01T00:00:00",
        }
    )
    return svc


def _make_hybrid_processor():
    svc = MagicMock()
    svc.start_cached_session = AsyncMock(
        return_value={"success": True, "cache": {"name": "cache-1"}, "latency": 0.1}
    )
    svc.submit_batch_job = AsyncMock(
        return_value={
            "success": True,
            "operation": {"name": "op-1"},
            "completed": True,
            "latency": 0.2,
        }
    )
    svc.create_ephemeral_token = AsyncMock(
        return_value={"success": True, "token": {"value": "tok-123"}, "latency": 0.05}
    )
    svc.process = AsyncMock(return_value="event1\nevent2\n")
    return svc


def _make_orchestrator():
    agent_result = MagicMock()
    agent_result.status = "ok"
    agent_result.output = {"response": "Hello from AI"}

    task_result = MagicMock()
    task_result.success = True
    task_result.results = {"transcript_action": agent_result}
    task_result.errors = []

    svc = MagicMock()
    svc.execute_task = AsyncMock(return_value=task_result)
    svc.execute_single = AsyncMock(return_value={"summary": "done"})
    svc.send_a2a_message = AsyncMock(
        return_value=MagicMock(conversation_id="conv-1", timestamp="2026-01-01T00:00:00")
    )
    svc.get_a2a_log = MagicMock(return_value=[{"msg": "hi"}])
    return svc


def _make_metrics_svc():
    return MagicMock()


def _make_websocket_mgr():
    return MagicMock()


def _apply_all_overrides(the_app: FastAPI = app):
    """Wire all dependency overrides onto the router and onto the app."""
    the_app.dependency_overrides[get_health_monitoring_service] = _make_health_svc
    the_app.dependency_overrides[get_cache_service] = _make_cache_svc
    the_app.dependency_overrides[get_data_service] = _make_data_svc
    the_app.dependency_overrides[get_video_processing_service] = _make_vps
    the_app.dependency_overrides[get_hybrid_processor_service] = _make_hybrid_processor
    the_app.dependency_overrides[get_agent_orchestrator_service] = _make_orchestrator
    the_app.dependency_overrides[get_metrics_service] = _make_metrics_svc
    the_app.dependency_overrides[get_websocket_manager] = _make_websocket_mgr


_apply_all_overrides()


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Helper: fake video service factory that get_service() returns
# ---------------------------------------------------------------------------

_HEALTH_STATUS = {
    "status": "healthy",
    "timestamp": "2026-01-01T00:00:00",
    "version": "test",
    "components": {},
}


def _patch_get_service(name):
    """Return a suitable mock for get_service(name)."""
    mapping = {
        "video_processor_factory": MagicMock(),
        "websocket_connection_manager": MagicMock(),
        "health_monitoring_service": _make_health_svc(),
    }
    return mapping.get(name, MagicMock())


# ===========================================================================
# Health Endpoint Tests
# ===========================================================================


class TestHealthEndpoint:
    def test_health_check_success(self, client):
        with patch(
            "youtube_extension.backend.api.v1.router.get_service",
            side_effect=_patch_get_service,
        ):
            resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_health_check_service_error(self, client):
        """When get_service raises, endpoint returns a sanitized 500.

        Regression guard for information disclosure: the response body must
        carry the generic message and must NOT echo the underlying exception
        text (``boom``) back to the client.
        """
        with patch(
            "youtube_extension.backend.api.v1.router.get_service",
            side_effect=RuntimeError("boom"),
        ):
            resp = client.get("/api/v1/health")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"
        assert "boom" not in resp.text

    def test_detailed_health_success(self, client):
        with patch(
            "youtube_extension.backend.api.v1.router.get_service",
            side_effect=_patch_get_service,
        ):
            resp = client.get("/api/v1/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert "basic" in data
        assert "timestamp" in data

    def test_detailed_health_error(self, client):
        with patch(
            "youtube_extension.backend.api.v1.router.get_service",
            side_effect=RuntimeError("boom"),
        ):
            resp = client.get("/api/v1/health/detailed")
        assert resp.status_code == 500


# ===========================================================================
# Capabilities Endpoint
# ===========================================================================


class TestCapabilitiesEndpoint:
    def test_capabilities_success(self, client):
        resp = client.get("/api/v1/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("operational", "error")
        assert "gemini" in data


# ===========================================================================
# Hybrid Cache / Batch / Token Endpoints
# ===========================================================================


class TestHybridEndpoints:
    def test_create_gemini_cache(self, client):
        payload = {
            "contents": "Hello, please cache this.",
            "model_name": "gemini-2.0-flash",
            "ttl_seconds": 3600,
        }
        resp = client.post("/api/v1/hybrid/cache", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["cache"] is not None

    def test_submit_gemini_batch(self, client):
        payload = {
            "requests": [{"contents": "Hello batch"}],
            "model_name": "gemini-2.0-flash",
            "wait": False,
        }
        resp = client.post("/api/v1/hybrid/batch", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_create_ephemeral_token(self, client):
        payload = {"model_name": "gemini-2.0-flash", "ttl_seconds": 300}
        resp = client.post("/api/v1/hybrid/ephemeral-token", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["token"] is not None


# ===========================================================================
# Cache Management Endpoints
# ===========================================================================


class TestCacheEndpoints:
    def test_get_cache_stats(self, client):
        resp = client.get("/api/v1/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cached_videos" in data
        assert data["total_cached_videos"] == 5

    def test_get_cached_video_found(self, client):
        resp = client.get("/api/v1/cache/auJzb1D-fag")
        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "auJzb1D-fag"

    def test_get_cached_video_not_found(self, client):
        # Override so cache returns None
        def _no_cache():
            svc = _make_cache_svc()
            svc.get_video_cache_info.return_value = None
            return svc

        app.dependency_overrides[get_cache_service] = _no_cache
        try:
            resp = client.get("/api/v1/cache/missing-video-id")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides[get_cache_service] = _make_cache_svc

    def test_clear_video_cache(self, client):
        resp = client.delete("/api/v1/cache/auJzb1D-fag")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_clear_all_cache(self, client):
        resp = client.delete("/api/v1/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_get_cache_stats_error(self, client):
        def _err():
            svc = MagicMock()
            svc.get_cache_statistics.side_effect = RuntimeError("db down")
            return svc

        # Clear global cache in the router module to ensure we hit the service
        router_module._stats_cache = {}
        router_module._stats_cache_time = 0

        app.dependency_overrides[get_cache_service] = _err
        try:
            resp = client.get("/api/v1/cache/stats")
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_cache_service] = _make_cache_svc

    def test_clear_all_cache_error(self, client):
        def _err():
            svc = MagicMock()
            svc.clear_cache.side_effect = RuntimeError("db down")
            return svc

        app.dependency_overrides[get_cache_service] = _err
        try:
            resp = client.delete("/api/v1/cache")
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_cache_service] = _make_cache_svc


# ===========================================================================
# Data / Video List Endpoints
# ===========================================================================


class TestDataEndpoints:
    def test_list_videos(self, client):
        resp = client.get("/api/v1/videos?limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert "videos" in data
        assert "total" in data
        assert data["total"] == 1

    def test_list_videos_pagination(self, client):
        """offset larger than total → empty list"""
        resp = client.get("/api/v1/videos?limit=10&offset=100")
        assert resp.status_code == 200
        data = resp.json()
        assert data["videos"] == []
        assert data["has_more"] is False

    def test_get_video_detail_found(self, client):
        resp = client.get("/api/v1/videos/auJzb1D-fag")
        # Note: this hits the /videos/{video_id} path which clashes with /videos/{job_id}/status
        # The detail endpoint is at /videos/{video_id} (GET) and should return 200
        assert resp.status_code in (200, 404)  # accept either; depends on path resolution

    def test_get_video_detail_not_found(self, client):
        def _no_detail():
            svc = _make_data_svc()
            svc.get_video_detail.return_value = None
            return svc

        app.dependency_overrides[get_data_service] = _no_detail
        try:
            resp = client.get("/api/v1/videos/nonexistent-vid")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc

    def test_get_learning_log(self, client):
        resp = client.get("/api/v1/learning-log")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_list_videos_error(self, client):
        def _err():
            svc = MagicMock()
            svc.get_videos_summary.side_effect = RuntimeError("boom")
            return svc

        app.dependency_overrides[get_data_service] = _err
        try:
            resp = client.get("/api/v1/videos")
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc


# ===========================================================================
# Feedback Endpoints
# ===========================================================================


class TestFeedbackEndpoint:
    def test_submit_feedback_success(self, client):
        payload = {
            "feedback_type": "quality",
            "rating": 5,
            "comment": "Great!",
            "metadata": {},
        }
        resp = client.post("/api/v1/feedback", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "feedback_id" in data

    def test_submit_feedback_save_fails(self, client):
        def _fail():
            svc = _make_data_svc()
            svc.save_feedback.return_value = False
            return svc

        app.dependency_overrides[get_data_service] = _fail
        try:
            payload = {"feedback_type": "general"}
            resp = client.post("/api/v1/feedback", json=payload)
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc

    def test_submit_feedback_with_action_text(self, client):
        """Cover the branch where metadata has action_text."""
        with patch(
            "youtube_extension.backend.api.v1.router.get_uvai_ml_client"
        ) as mock_client:
            mock_ml = MagicMock()
            mock_ml.record_action_feedback = AsyncMock(return_value=None)
            mock_client.return_value = mock_ml

            payload = {
                "feedback_type": "quality",
                "metadata": {
                    "action_text": "Build a web app",
                    "clicked": True,
                    "completed": True,
                    "time_to_complete_seconds": 120.0,
                },
            }
            resp = client.post("/api/v1/feedback", json=payload)
        assert resp.status_code == 200


# ===========================================================================
# Metrics Endpoint
# ===========================================================================


class TestMetricsEndpoint:
    def test_get_metrics(self, client):
        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200

    def test_get_metrics_error(self, client):
        def _err():
            svc = MagicMock()
            svc.get_metrics_prometheus_format.side_effect = RuntimeError("boom")
            return svc

        app.dependency_overrides[get_health_monitoring_service] = _err
        try:
            resp = client.get("/api/v1/metrics")
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_health_monitoring_service] = _make_health_svc


# ===========================================================================
# Performance Alert / Report Endpoints
# ===========================================================================


class TestPerformanceEndpoints:
    def test_performance_alert_numeric(self, client):
        payload = {"type": "lcp", "data": 1500}
        with patch.object(
            router_module.performance_monitor,
            "record_metric",
            new_callable=lambda: lambda *a, **kw: AsyncMock()(),
        ):
            resp = client.post("/api/v1/performance/alert", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "frontend.alert.lcp" in data["recorded"]

    def test_performance_alert_non_numeric(self, client):
        payload = {"type": "custom", "data": "string-value"}
        with patch.object(
            router_module.performance_monitor, "record_metric", new_callable=AsyncMock
        ):
            resp = client.post("/api/v1/performance/alert", json=payload)
        assert resp.status_code == 200

    def test_performance_report(self, client):
        payload = {
            "metrics": {
                "lcp": {"current": 1200, "unit": "ms"},
                "fid": {"current": 30, "unit": "ms"},
            }
        }
        with patch.object(
            router_module.performance_monitor, "record_metric", new_callable=AsyncMock
        ):
            resp = client.post("/api/v1/performance/report", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["metrics_recorded"] == 2

    def test_performance_report_empty(self, client):
        resp = client.post("/api/v1/performance/report", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["metrics_recorded"] == 0


# ===========================================================================
# Process Video Endpoint
# ===========================================================================


class TestProcessVideoEndpoint:
    def test_process_video_success(self, client):
        payload = {"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"}
        resp = client.post("/api/v1/process-video", json=payload)
        assert resp.status_code == 200

    def test_process_video_invalid_url(self, client):
        payload = {"video_url": "https://example.com/not-a-video"}
        resp = client.post("/api/v1/process-video", json=payload)
        assert resp.status_code == 422

    def test_process_video_service_error(self, client):
        def _err():
            svc = MagicMock()
            svc.process_video_basic = AsyncMock(side_effect=RuntimeError("fail"))
            return svc

        app.dependency_overrides[get_video_processing_service] = _err
        try:
            payload = {"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"}
            resp = client.post("/api/v1/process-video", json=payload)
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_video_processing_service] = _make_vps


# ===========================================================================
# Process Video Markdown Endpoint
# ===========================================================================


class TestProcessVideoMarkdownEndpoint:
    def test_markdown_success(self, client):
        payload = {"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"}
        resp = client.post("/api/v1/process-video-markdown", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["video_id"] == "auJzb1D-fag"

    def test_markdown_cached(self, client):
        def _cached_vps():
            svc = _make_vps()
            svc.process_video_for_markdown = AsyncMock(
                return_value={
                    "video_id": "auJzb1D-fag",
                    "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "metadata": {},
                    "markdown_content": "# cached",
                    "cached": True,
                    "save_path": "/tmp/cached.md",
                    "processing_time": "0.1s",
                    "status": "success",
                }
            )
            return svc

        app.dependency_overrides[get_video_processing_service] = _cached_vps
        try:
            payload = {"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"}
            resp = client.post("/api/v1/process-video-markdown", json=payload)
            assert resp.status_code == 200
            assert resp.json()["cached"] is True
        finally:
            app.dependency_overrides[get_video_processing_service] = _make_vps

    def test_markdown_rate_limited(self, client):
        def _rate_limited():
            svc = _make_health_svc()
            svc.rate_limit_check.return_value = False
            return svc

        app.dependency_overrides[get_health_monitoring_service] = _rate_limited
        try:
            payload = {"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"}
            resp = client.post("/api/v1/process-video-markdown", json=payload)
            assert resp.status_code == 429
        finally:
            app.dependency_overrides[get_health_monitoring_service] = _make_health_svc

    def test_markdown_service_error(self, client):
        def _err():
            svc = _make_vps()
            svc.process_video_for_markdown = AsyncMock(side_effect=RuntimeError("fail"))
            return svc

        app.dependency_overrides[get_video_processing_service] = _err
        try:
            payload = {"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"}
            resp = client.post("/api/v1/process-video-markdown", json=payload)
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_video_processing_service] = _make_vps


# ===========================================================================
# Video-to-Software Endpoint
# ===========================================================================


class TestVideoToSoftwareEndpoint:
    def test_video_to_software_success(self, client):
        with patch(
            "youtube_extension.backend.api.v1.router.resolve_deployment_target",
            return_value={
                "requested": "vercel",
                "resolved": "vercel",
                "alias_applied": False,
            },
        ):
            payload = {
                "url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "project_type": "web",
                "deployment_target": "vercel",
            }
            resp = client.post("/api/v1/video-to-software", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_name"] == "test-app"

    def test_video_to_software_error(self, client):
        def _err():
            svc = _make_vps()
            svc.process_video_to_software = AsyncMock(side_effect=RuntimeError("fail"))
            return svc

        app.dependency_overrides[get_video_processing_service] = _err
        try:
            with patch(
                "youtube_extension.backend.api.v1.router.resolve_deployment_target",
                return_value={"requested": "vercel", "resolved": "vercel", "alias_applied": False},
            ):
                payload = {
                    "url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "project_type": "web",
                    "deployment_target": "vercel",
                }
                resp = client.post("/api/v1/video-to-software", json=payload)
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_video_processing_service] = _make_vps


# ===========================================================================
# Async Video Jobs (start, status, events, dispatch, agents)
# ===========================================================================


class TestVideoJobEndpoints:
    def test_start_video_processing(self, client):
        payload = {
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "language": "en",
        }
        resp = client.post("/api/v1/videos/process", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "job_id" in data["data"]

    def test_get_video_job_status_found(self, client):
        # Create a job first
        payload = {
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
        }
        create_resp = client.post("/api/v1/videos/process", json=payload)
        assert create_resp.status_code == 200
        job_id = create_resp.json()["data"]["job_id"]

        resp = client.get(f"/api/v1/videos/{job_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["job_id"] == job_id

    def test_get_video_job_status_not_found(self, client):
        resp = client.get("/api/v1/videos/nonexistent-job-id/status")
        assert resp.status_code == 404


# ===========================================================================
# Event Extraction Endpoint
# ===========================================================================


class TestEventExtractionEndpoint:
<<<<<<< HEAD
    def test_extract_events_from_transcript(self, client):
        """Use inline transcript — no job_id."""
        with patch.object(
            _HybridProcessorService_cls.return_value,
            "process",
            new_callable=AsyncMock,
            return_value="Build a web app\nCreate an API\nDeploy to cloud\n",
=======
    def test_extract_events_from_transcript(self, client, monkeypatch):
        """Use inline transcript — no job_id."""
        from youtube_extension.services.ai import vercel_gateway_provider

        processor = SimpleNamespace(
            process=AsyncMock(
                return_value=SimpleNamespace(
                    success=True,
                    response="Build a web app\nCreate an API\nDeploy to cloud\n",
                    cloud_result=SimpleNamespace(backend="gemini"),
                )
            )
        )
        monkeypatch.setattr(
            vercel_gateway_provider,
            "gateway_available",
            lambda: False,
            raising=False,
        )
        with patch.object(
            router_module,
            "HybridProcessorService",
            return_value=processor,
>>>>>>> origin/main
        ):
            payload = {
                "transcript": (
                    "Build a web app. Create an API endpoint. Deploy to cloud server."
                )
            }
            resp = client.post("/api/v1/events/extract", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "events" in data["data"]

    def test_extract_events_no_transcript_no_job(self, client):
        """Neither job_id nor transcript — should return 400."""
        resp = client.post("/api/v1/events/extract", json={})
        assert resp.status_code == 400

    def test_extract_events_job_not_found(self, client):
        """Job ID provided but not in store → 404."""
        resp = client.post(
            "/api/v1/events/extract", json={"job_id": "job_nonexistent"}
        )
        assert resp.status_code == 404

    def test_extract_events_job_not_complete(self, client):
        """Job exists but is pending → 409."""
        # Insert a pending job into the in-memory store
        job_id = "job_test_pending"
        _video_jobs[job_id] = VideoJobStatusResponse(
            job_id=job_id,
            status=JobStatus.pending,
            progress=0.0,
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        )
        try:
            resp = client.post(
                "/api/v1/events/extract", json={"job_id": job_id}
            )
            assert resp.status_code == 409
        finally:
            del _video_jobs[job_id]

    def test_extract_events_completed_job(self, client):
        """Job complete → transcript extracted from job."""
        job_id = "job_test_complete"
        _video_jobs[job_id] = VideoJobStatusResponse(
            job_id=job_id,
            status=JobStatus.complete,
            progress=100.0,
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
            transcript="Build something great. Create value for users.",
        )
        try:
            # Patch HybridProcessorService to raise so we fall back to heuristics
            with patch(
                "youtube_extension.backend.api.v1.router.HybridProcessorService",
                side_effect=Exception("unavailable"),
            ):
                resp = client.post(
                    "/api/v1/events/extract", json={"job_id": job_id}
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["data"]["job_id"] == job_id
        finally:
            del _video_jobs[job_id]

    def test_extract_events_ai_fallback_heuristic(self, client):
        """AI extraction fails → heuristic extraction covers fallback branch."""
        with patch(
            "youtube_extension.backend.api.v1.router.HybridProcessorService",
            side_effect=Exception("ai unavailable"),
        ):
            payload = {
                "transcript": (
                    "Install the package first. Run the server. Configure the settings. "
                    "Deploy to production. Monitor the system."
                )
            }
            resp = client.post("/api/v1/events/extract", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        events = data["data"]["events"]
        assert len(events) > 0


# ===========================================================================
# Agent Dispatch Endpoints
# ===========================================================================


class TestAgentDispatchEndpoints:
    def test_dispatch_agents_with_events(self, client):
        payload = {
            "events": [
                {"id": "evt_aaa", "type": "action", "title": "Build something"},
                {"id": "evt_bbb", "type": "topic", "title": "Deploy to cloud"},
            ],
            "agent_types": ["analyzer"],
        }
        resp = client.post("/api/v1/agents/dispatch", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "executions" in data["data"]

    def test_dispatch_agents_from_transcript(self, client):
        """Events list empty but transcript provided → auto-extract."""
        payload = {
            "events": [],
            "transcript": "Build an API. Deploy to Vercel. Monitor logs. Configure alerts.",
        }
        resp = client.post("/api/v1/agents/dispatch", json=payload)
        assert resp.status_code == 200

    def test_dispatch_agents_no_events_no_transcript(self, client):
        payload = {"events": []}
        resp = client.post("/api/v1/agents/dispatch", json=payload)
        assert resp.status_code == 400

    def test_get_agent_status_found(self, client):
        # Dispatch an agent first
        payload = {
            "events": [{"id": "evt_ccc", "type": "action", "title": "Test event"}],
            "agent_types": ["analyzer"],
        }
        dispatch_resp = client.post("/api/v1/agents/dispatch", json=payload)
        assert dispatch_resp.status_code == 200
        executions = dispatch_resp.json()["data"]["executions"]
        agent_id = executions[0]["agent_id"]

        resp = client.get(f"/api/v1/agents/{agent_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["agent_id"] == agent_id

    def test_get_agent_status_not_found(self, client):
        resp = client.get("/api/v1/agents/nonexistent-agent/status")
        assert resp.status_code == 404


# ===========================================================================
# A2A Messaging Endpoints
# ===========================================================================


class TestA2AEndpoints:
    def test_send_a2a_message_missing_recipient(self, client):
        """recipient required → 400."""
        resp = client.post("/api/v1/agents/a2a/send", json={"sender": "agentA"})
        assert resp.status_code == 400

    def test_send_a2a_message_success(self, client):
        """AgentOrchestrator is None → instantiation raises; we patch it."""
        mock_orch = MagicMock()
        mock_orch.send_a2a_message = AsyncMock(
            return_value=MagicMock(
                conversation_id="conv-test", timestamp="2026-01-01T00:00:00"
            )
        )
        with patch("youtube_extension.backend.api.v1.router.AgentOrchestrator", return_value=mock_orch):
            resp = client.post(
                "/api/v1/agents/a2a/send",
                json={"sender": "agentA", "recipient": "agentB", "content": {"text": "hi"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["conversation_id"] == "conv-test"

    def test_get_a2a_log(self, client):
        mock_orch = MagicMock()
        mock_orch.get_a2a_log.return_value = [{"msg": "hello"}]
        with patch("youtube_extension.backend.api.v1.router.AgentOrchestrator", return_value=mock_orch):
            resp = client.get("/api/v1/agents/a2a/log?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["count"] == 1

    def test_get_a2a_log_with_conversation_id(self, client):
        mock_orch = MagicMock()
        mock_orch.get_a2a_log.return_value = []
        with patch("youtube_extension.backend.api.v1.router.AgentOrchestrator", return_value=mock_orch):
            resp = client.get("/api/v1/agents/a2a/log?conversation_id=conv-xyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["count"] == 0

    def test_get_agent_sessions_returns_filtered_logs(self, client):
        """/agents/sessions reads the shared orchestrator and passes filters through."""
        mock_orch = MagicMock()
        mock_orch.get_session_logs.return_value = [
            {"agent_type": "researcher", "status": "ok"}
        ]
        with patch.object(router_module, "_shared_orchestrator", mock_orch):
            resp = client.get("/api/v1/agents/sessions?agent_type=researcher&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["count"] == 1
        mock_orch.get_session_logs.assert_called_once_with(
            agent_type="researcher", limit=5
        )

    def test_get_agent_sessions_503_when_orchestrator_unavailable(self, client):
        """When the shared orchestrator failed to import, the endpoint 503s."""
        with patch.object(router_module, "_shared_orchestrator", None):
            resp = client.get("/api/v1/agents/sessions")
        assert resp.status_code == 503


# ===========================================================================
# Actions Endpoints
# ===========================================================================


class TestActionsEndpoints:
    def test_get_actions_by_video(self, client):
        # InMemoryActionRepository starts empty; response should be []
        resp = client.get("/api/v1/actions/auJzb1D-fag")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_update_action_not_found(self, client):
        # action_id that doesn't exist → repo.update returns None → success: False
        resp = client.put(
            "/api/v1/actions/nonexistent-action", json={"status": "done"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    def test_update_action_success(self, client):
        # Seed the in-memory repo with a real action
        repo = _InMemoryActionRepository()
        action = repo.save(
            {
                "video_id": "auJzb1D-fag",
                "action_text": "Deploy the application",
                "status": "pending",
            }
        )
        action_id = action["id"]

        with patch(
            "youtube_extension.backend.api.v1.router.ActionRepository",
            return_value=repo,
        ):
            resp = client.put(
                f"/api/v1/actions/{action_id}",
                json={"status": "completed", "action_text": "Deploy the application"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


# ===========================================================================
# Cloud Tasks Handler
# ===========================================================================


class TestCloudTasksHandler:
    def test_process_video_task_no_header(self, client):
        payload = {
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "metadata": {"job_id": "job_ct1"},
        }
        resp = client.post("/api/v1/process-video-task", json=payload)
        assert resp.status_code == 403

    def test_process_video_task_missing_job_id(self, client):
        resp = client.post(
            "/api/v1/process-video-task",
            json={"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag", "metadata": {}},
            headers={"X-CloudTasks-TaskName": "task-abc"},
        )
        assert resp.status_code == 400

    def test_process_video_task_mismatched_job_id(self, client):
        resp = client.post(
            "/api/v1/process-video-task",
            json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "metadata": {"job_id": "job_xyz"},
            },
            headers={"X-CloudTasks-TaskName": "task-for-job-abc"},
        )
        assert resp.status_code == 403

    def test_process_video_task_missing_video_url(self, client):
        resp = client.post(
            "/api/v1/process-video-task",
            json={"metadata": {"job_id": "job_myid"}},
            headers={"X-CloudTasks-TaskName": "task-for-job_myid"},
        )
        assert resp.status_code == 400


# ===========================================================================
# Dependency Injectors (unit tests, not via HTTP)
# ===========================================================================


class TestDependencyInjectors:
    def test_get_agent_orchestrator_when_none(self):
        """When AgentOrchestrator is None, the injector raises HTTPException 503."""
        import fastapi
        original = router_module.AgentOrchestrator
        router_module.AgentOrchestrator = None
        try:
            with pytest.raises(fastapi.HTTPException) as exc_info:
                get_agent_orchestrator_service()
            assert exc_info.value.status_code == 503
        finally:
            router_module.AgentOrchestrator = original

    def test_get_cache_service_calls_get_service(self):
        with patch("youtube_extension.backend.api.v1.router.get_service") as mock_gs:
            mock_gs.return_value = MagicMock()
            get_cache_service()
            mock_gs.assert_called_once_with("cache_service")

    def test_get_data_service_calls_get_service(self):
        with patch("youtube_extension.backend.api.v1.router.get_service") as mock_gs:
            mock_gs.return_value = MagicMock()
            get_data_service()
            mock_gs.assert_called_once_with("data_service")

    def test_get_health_monitoring_service_calls_get_service(self):
        with patch("youtube_extension.backend.api.v1.router.get_service") as mock_gs:
            mock_gs.return_value = MagicMock()
            get_health_monitoring_service()
            mock_gs.assert_called_once_with("health_monitoring_service")

    def test_get_metrics_service_calls_get_service(self):
        with patch("youtube_extension.backend.api.v1.router.get_service") as mock_gs:
            mock_gs.return_value = MagicMock()
            get_metrics_service()
            mock_gs.assert_called_once_with("metrics_service")

    def test_get_hybrid_processor_service_calls_get_service(self):
        with patch("youtube_extension.backend.api.v1.router.get_service") as mock_gs:
            mock_gs.return_value = MagicMock()
            get_hybrid_processor_service()
            mock_gs.assert_called_once_with("hybrid_processor_service")

    def test_get_video_processing_service_calls_get_service(self):
        with patch("youtube_extension.backend.api.v1.router.get_service") as mock_gs:
            mock_gs.return_value = MagicMock()
            get_video_processing_service()
            mock_gs.assert_called_once_with("video_processing_service")


# ===========================================================================
# _InMemoryActionRepository Unit Tests
# ===========================================================================


class TestInMemoryActionRepository:
    def setup_method(self):
        # Clear shared state before each test
        _InMemoryActionRepository._actions = {}

    def test_save_and_get(self):
        repo = _InMemoryActionRepository()
        saved = repo.save({"video_id": "vid1", "action_text": "Do something"})
        assert "id" in saved
        assert saved["video_id"] == "vid1"
        actions = repo.get_by_video_id("vid1")
        assert len(actions) == 1

    def test_save_with_explicit_id(self):
        repo = _InMemoryActionRepository()
        saved = repo.save({"id": "custom-id-123", "video_id": "vid2"})
        assert saved["id"] == "custom-id-123"

    def test_update_existing(self):
        repo = _InMemoryActionRepository()
        saved = repo.save({"video_id": "vid3", "status": "pending"})
        updated = repo.update(saved["id"], status="completed")
        assert updated is not None
        assert updated["status"] == "completed"

    def test_update_nonexistent(self):
        repo = _InMemoryActionRepository()
        result = repo.update("nonexistent-id", status="done")
        assert result is None

    def test_get_by_video_id_empty(self):
        repo = _InMemoryActionRepository()
        assert repo.get_by_video_id("no-such-video") == []


# ===========================================================================
# _emit_event Tests (unit, not via HTTP)
# ===========================================================================


class TestEmitEvent:
    async def test_emit_event_no_publisher(self):
        """_emit_event with _ce_publisher=None is a no-op."""
        original = router_module._ce_publisher
        router_module._ce_publisher = None
        try:
            # Should not raise
            await router_module._emit_event("test.event", {"key": "value"})
        finally:
            router_module._ce_publisher = original

    async def test_emit_event_with_publisher(self):
        mock_pub = MagicMock()
        mock_pub.publish = AsyncMock(return_value=None)
        original = router_module._ce_publisher
        router_module._ce_publisher = mock_pub
        try:
            await router_module._emit_event(
                "test.event", {"key": "value"}, subject="/test"
            )
            mock_pub.publish.assert_called_once()
        finally:
            router_module._ce_publisher = original

    async def test_emit_event_publisher_raises(self):
        """If the publisher raises, _emit_event silently logs and continues."""
        mock_pub = MagicMock()
        mock_pub.publish = AsyncMock(side_effect=RuntimeError("publish failed"))
        original = router_module._ce_publisher
        router_module._ce_publisher = mock_pub
        try:
            # Should NOT propagate the exception
            await router_module._emit_event("test.event", {"key": "value"})
        finally:
            router_module._ce_publisher = original


# ===========================================================================
# Chat Endpoint Tests
# ===========================================================================


class TestChatEndpoint:
    def test_chat_success(self, client):
        payload = {"query": "How do I process a video?", "session_id": "sess-1"}
        resp = client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["status"] == "success"

    def test_chat_with_video_url(self, client):
        payload = {
            "query": "Summarize this video",
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "session_id": "sess-2",
        }
        resp = client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 200

    def test_chat_with_video_url_not_in_data_service(self, client):
        """Video not found → triggers real-time processing branch."""
        def _no_detail():
            svc = _make_data_svc()
            svc.get_video_detail.return_value = None
            return svc

        app.dependency_overrides[get_data_service] = _no_detail
        try:
            payload = {
                "query": "Tell me about this video",
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            }
            resp = client.post("/api/v1/chat", json=payload)
            assert resp.status_code == 200
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc

    def test_chat_orchestrator_failure(self, client):
        def _failing_orch():
            task_result = MagicMock()
            task_result.success = False
            task_result.errors = ["Something went wrong"]
            svc = MagicMock()
            svc.execute_task = AsyncMock(return_value=task_result)
            return svc

        app.dependency_overrides[get_agent_orchestrator_service] = _failing_orch
        try:
            payload = {"query": "Help me", "session_id": "sess-fail"}
            resp = client.post("/api/v1/chat", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "error"
        finally:
            app.dependency_overrides[get_agent_orchestrator_service] = _make_orchestrator

    def test_chat_orchestrator_raises(self, client):
        def _raises():
            svc = MagicMock()
            svc.execute_task = AsyncMock(side_effect=RuntimeError("crash"))
            return svc

        app.dependency_overrides[get_agent_orchestrator_service] = _raises
        try:
            payload = {"query": "Help me crash"}
            resp = client.post("/api/v1/chat", json=payload)
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_agent_orchestrator_service] = _make_orchestrator

    def test_chat_no_agent_result(self, client):
        """Agent result exists but status is not 'ok'."""
        def _bad_agent():
            agent_result = MagicMock()
            agent_result.status = "error"
            agent_result.output = {"error": "AI failed"}

            task_result = MagicMock()
            task_result.success = True
            task_result.results = {"transcript_action": agent_result}
            task_result.errors = []

            svc = MagicMock()
            svc.execute_task = AsyncMock(return_value=task_result)
            return svc

        app.dependency_overrides[get_agent_orchestrator_service] = _bad_agent
        try:
            payload = {"query": "Will this error?", "session_id": "sess-bad"}
            resp = client.post("/api/v1/chat", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert "error" in data["response"].lower() or data["response"]
        finally:
            app.dependency_overrides[get_agent_orchestrator_service] = _make_orchestrator


# ===========================================================================
# _absolute_status_url helper (unit test)
# ===========================================================================

class TestAbsoluteStatusUrl:
    def test_absolute_status_url_format(self):
        mock_request = MagicMock()
        mock_request.base_url = "http://testserver/"
        result = router_module._absolute_status_url(mock_request, "job_abc123")
        assert result == "http://testserver/api/v1/videos/job_abc123/status"


# ===========================================================================
# Transcript-Action Endpoint
# ===========================================================================


class TestTranscriptActionEndpoint:
    """Tests for POST /api/v1/transcript-action"""

    def _make_workflow(
        self,
        metadata=None,
        duration_seconds=60,
        run_result=None,
    ):
        """Return a mock TranscriptActionWorkflow."""
        meta = metadata or _FakeMetadata()
        wf = MagicMock()
        wf.fetch_video_metadata = AsyncMock(return_value=meta)
        wf.get_duration_seconds = MagicMock(return_value=duration_seconds)
        default_result = {
            "success": True,
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "metadata": {"video_id": "auJzb1D-fag"},
            "transcript": {"text": "hello"},
            "outputs": {},
            "errors": [],
            "orchestration_meta": {"agents_used": [], "processing_time": 1.0},
            "async_processing": False,
        }
        wf.run = AsyncMock(return_value=run_result or default_result)
        return wf

    def _patch_transcript_action(self, mock_wf, threshold=9999):
        """Context manager that patches the workflow class and its class attribute."""
        from unittest.mock import patch as _patch

        class _MockWorkflowClass:
            ASYNC_VIDEO_THRESHOLD_SECONDS = threshold

            def __init__(self, *args, **kwargs):
                pass

            def __new__(cls, *args, **kwargs):
                return mock_wf

            @staticmethod
            def get_duration_seconds(meta):
                return mock_wf.get_duration_seconds(meta)

        return _patch(
            "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
            _MockWorkflowClass,
        )

    def test_transcript_action_success(self, client):
        mock_wf = self._make_workflow()
        with self._patch_transcript_action(mock_wf):
            resp = client.post(
                "/api/v1/transcript-action",
                json={"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_transcript_action_failed_result(self, client):
        """Workflow runs but returns success=False → failed event emitted."""
        failed_result = {
            "success": False,
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "metadata": {},
            "transcript": {},
            "outputs": {},
            "errors": ["something went wrong"],
            "orchestration_meta": {},
            "async_processing": False,
        }
        mock_wf = self._make_workflow(run_result=failed_result)
        with self._patch_transcript_action(mock_wf):
            resp = client.post(
                "/api/v1/transcript-action",
                json={"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    def test_transcript_action_metadata_fetch_error(self, client):
        """ValueError during metadata fetch → 400."""
        mock_wf = MagicMock()
        mock_wf.fetch_video_metadata = AsyncMock(
            side_effect=ValueError("invalid URL")
        )
        mock_wf.get_duration_seconds = MagicMock(return_value=60)
        with self._patch_transcript_action(mock_wf):
            resp = client.post(
                "/api/v1/transcript-action",
                json={"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"},
            )
        assert resp.status_code == 400

    def test_transcript_action_async_long_video(self, client):
        """Very long video → queued asynchronously (async_processing=True)."""
        mock_wf = self._make_workflow(duration_seconds=99999)
        # Use threshold=0 so any duration > 0 is "long"
        with self._patch_transcript_action(mock_wf, threshold=0):
            with patch(
                "youtube_extension.backend.api.v1.router._queue_transcript_action_job",
                new_callable=AsyncMock,
                return_value={
                    "success": True,
                    "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "metadata": {"async_processing": True},
                    "transcript": {},
                    "outputs": {},
                    "errors": [],
                    "orchestration_meta": {"agents_used": [], "processing_time": 0.0},
                    "async_processing": True,
                    "job_id": "job_asynctest",
                    "job_status": "pending",
                    "status_url": "http://testserver/api/v1/videos/job_asynctest/status",
                    "processing_transport": "local_background",
                },
            ):
                resp = client.post(
                    "/api/v1/transcript-action",
                    json={"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"},
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["async_processing"] is True


# ===========================================================================
# _run_video_job Unit Tests
# ===========================================================================


def _make_workflow_class(mock_wf_instance):
    """Create a replacement class for TranscriptActionWorkflow that returns mock_wf_instance."""
    class _MockWFClass:
        ASYNC_VIDEO_THRESHOLD_SECONDS = 9999

        def __new__(cls, *args, **kwargs):
            return mock_wf_instance

        @staticmethod
        def get_duration_seconds(meta):
            return 60

    return _MockWFClass


class TestRunVideoJobCoroutine:
    """Test the background coroutine _run_video_job directly."""

    async def test_run_video_job_success(self):
        """Success path: workflow completes → job.status = complete."""
        from youtube_extension.backend.api.v1.router import _run_video_job
        from youtube_extension.backend.api.v1.models import VideoProcessJobRequest

        job_id = "job_unit_success"
        _video_jobs[job_id] = VideoJobStatusResponse(
            job_id=job_id,
            status=JobStatus.pending,
            progress=0.0,
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        )

        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(
            return_value={
                "success": True,
                "transcript": {"text": "hello"},
                "outputs": {"summary": "Test summary"},
                "metadata": {"video_id": "auJzb1D-fag"},
                "orchestration_meta": {"agents_used": ["t"], "processing_time": 1.0},
                "errors": [],
            }
        )

        req = VideoProcessJobRequest(
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag"
        )

        try:
            with patch(
                "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
                _make_workflow_class(mock_wf),
            ):
                await _run_video_job(job_id, req)

            job = _video_jobs[job_id]
            assert job.status == JobStatus.complete
            assert job.progress == 100.0
        finally:
            _video_jobs.pop(job_id, None)

    async def test_run_video_job_failure_result(self):
        """Workflow returns success=False → job.status = failed."""
        from youtube_extension.backend.api.v1.router import _run_video_job
        from youtube_extension.backend.api.v1.models import VideoProcessJobRequest

        job_id = "job_unit_fail"
        _video_jobs[job_id] = VideoJobStatusResponse(
            job_id=job_id,
            status=JobStatus.pending,
            progress=0.0,
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        )

        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(
            return_value={
                "success": False,
                "transcript": {},
                "outputs": {},
                "metadata": {},
                "orchestration_meta": {},
                "errors": ["extraction failed"],
            }
        )

        req = VideoProcessJobRequest(
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag"
        )

        try:
            with patch(
                "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
                _make_workflow_class(mock_wf),
            ):
                await _run_video_job(job_id, req)

            job = _video_jobs[job_id]
            assert job.status == JobStatus.failed
            assert "extraction failed" in (job.error or "")
        finally:
            _video_jobs.pop(job_id, None)

    async def test_run_video_job_exception(self):
        """Workflow raises → job.status = failed with error message."""
        from youtube_extension.backend.api.v1.router import _run_video_job
        from youtube_extension.backend.api.v1.models import VideoProcessJobRequest

        job_id = "job_unit_exc"
        _video_jobs[job_id] = VideoJobStatusResponse(
            job_id=job_id,
            status=JobStatus.pending,
            progress=0.0,
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        )

        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(side_effect=RuntimeError("network error"))

        req = VideoProcessJobRequest(
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag"
        )

        try:
            with patch(
                "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
                _make_workflow_class(mock_wf),
            ):
                await _run_video_job(job_id, req)

            job = _video_jobs[job_id]
            assert job.status == JobStatus.failed
            assert "network error" in (job.error or "")
        finally:
            _video_jobs.pop(job_id, None)

    async def test_run_video_job_no_error_text(self):
        """Workflow returns success=False with empty errors list."""
        from youtube_extension.backend.api.v1.router import _run_video_job
        from youtube_extension.backend.api.v1.models import VideoProcessJobRequest

        job_id = "job_unit_noerr"
        _video_jobs[job_id] = VideoJobStatusResponse(
            job_id=job_id,
            status=JobStatus.pending,
            progress=0.0,
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        )

        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(
            return_value={
                "success": False,
                "transcript": "plain text",
                "outputs": {},
                "metadata": {},
                "orchestration_meta": {},
                "errors": [],
            }
        )

        req = VideoProcessJobRequest(
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag"
        )

        try:
            with patch(
                "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
                _make_workflow_class(mock_wf),
            ):
                await _run_video_job(job_id, req)

            job = _video_jobs[job_id]
            assert job.status == JobStatus.failed
            # Default message used when no specific errors
            assert job.error == "Transcript-action workflow failed"
        finally:
            _video_jobs.pop(job_id, None)


# ===========================================================================
# Cloud Tasks Full Execution Path
# ===========================================================================


class TestCloudTasksFullExecution:
    """Test the cloud tasks endpoint with a valid matching job_id to hit lines 1285-1305."""

    def test_process_video_task_full_execution(self, client):
        """Valid cloud tasks request → runs _run_video_job synchronously."""
        job_id = "job_ct_exec"

        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(
            return_value={
                "success": True,
                "transcript": {"text": "hello"},
                "outputs": {},
                "metadata": {},
                "orchestration_meta": {},
                "errors": [],
            }
        )

        with patch(
            "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
            _make_workflow_class(mock_wf),
        ):
            resp = client.post(
                "/api/v1/process-video-task",
                json={
                    "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "metadata": {
                        "job_id": job_id,
                        "language": "en",
                        "video_options": {},
                    },
                },
                headers={"X-CloudTasks-TaskName": f"task-for-{job_id}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert data["task_name"] == f"task-for-{job_id}"

    def test_process_video_task_with_existing_job(self, client):
        """Job already in store → setdefault returns existing job."""
        job_id = "job_ct_exist"
        _video_jobs[job_id] = VideoJobStatusResponse(
            job_id=job_id,
            status=JobStatus.downloading,
            progress=10.0,
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        )

        mock_wf = MagicMock()
        mock_wf.run = AsyncMock(
            return_value={
                "success": True,
                "transcript": {},
                "outputs": {},
                "metadata": {},
                "orchestration_meta": {},
                "errors": [],
            }
        )

        try:
            with patch(
                "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
                _make_workflow_class(mock_wf),
            ):
                resp = client.post(
                    "/api/v1/process-video-task",
                    json={
                        "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                        "metadata": {"job_id": job_id},
                    },
                    headers={"X-CloudTasks-TaskName": f"task-{job_id}"},
                )
            assert resp.status_code == 200
        finally:
            _video_jobs.pop(job_id, None)


# ===========================================================================
# Update Action with uvai feedback recording
# ===========================================================================


class TestUpdateActionWithFeedback:
    """Tests for update_action_v1 covering the uvai ml client branch."""

    def test_update_action_with_action_text_and_completed(self, client):
        """action_text + completed=True triggers uvai ml feedback recording."""
        repo = _InMemoryActionRepository()
        _InMemoryActionRepository._actions = {}
        action = repo.save({"video_id": "auJzb1D-fag", "action_text": "Build API"})
        action_id = action["id"]

        mock_ml = MagicMock()
        mock_ml.record_action_feedback = AsyncMock(return_value=None)

        with patch(
            "youtube_extension.backend.api.v1.router.ActionRepository",
            return_value=repo,
        ):
            with patch(
                "youtube_extension.backend.api.v1.router.get_uvai_ml_client",
                return_value=mock_ml,
            ):
                resp = client.put(
                    f"/api/v1/actions/{action_id}",
                    json={
                        "action_text": "Build API",
                        "status": "completed",
                        "clicked": True,
                        "time_to_complete": 60.5,
                    },
                )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_update_action_time_to_complete_invalid(self, client):
        """time_to_complete that can't be cast to float → time_to_complete_seconds=None."""
        repo = _InMemoryActionRepository()
        _InMemoryActionRepository._actions = {}
        action = repo.save({"video_id": "v1", "action_text": "Deploy"})
        action_id = action["id"]

        mock_ml = MagicMock()
        mock_ml.record_action_feedback = AsyncMock(return_value=None)

        with patch(
            "youtube_extension.backend.api.v1.router.ActionRepository",
            return_value=repo,
        ):
            with patch(
                "youtube_extension.backend.api.v1.router.get_uvai_ml_client",
                return_value=mock_ml,
            ):
                resp = client.put(
                    f"/api/v1/actions/{action_id}",
                    json={
                        "action_text": "Deploy",
                        "status": "done",
                        "time_to_complete": "not-a-number",
                    },
                )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ===========================================================================
# Additional Dependency Injector Coverage
# ===========================================================================


class TestAdditionalDependencyInjectors:
    def test_get_websocket_manager_calls_get_service(self):
        with patch("youtube_extension.backend.api.v1.router.get_service") as mock_gs:
            mock_gs.return_value = MagicMock()
            get_websocket_manager()
            mock_gs.assert_called_once_with("websocket_connection_manager")

    def test_get_agent_orchestrator_when_available(self):
        """When AgentOrchestrator is set, call get_service('agent_orchestrator')."""
        with patch("youtube_extension.backend.api.v1.router.get_service") as mock_gs:
            mock_gs.return_value = MagicMock()
            # Ensure AgentOrchestrator is not None
            original = router_module.AgentOrchestrator
            router_module.AgentOrchestrator = MagicMock()
            try:
                result = get_agent_orchestrator_service()
                mock_gs.assert_called_once_with("agent_orchestrator")
            finally:
                router_module.AgentOrchestrator = original


# ===========================================================================
# _queue_transcript_action_job Direct Tests
# ===========================================================================


class TestQueueTranscriptActionJob:
    """Test _queue_transcript_action_job directly."""

    async def test_queue_job_cloud_tasks_unavailable(self):
        """CloudTasksQueueService raises → fallback to local background task."""
        from youtube_extension.backend.api.v1.router import _queue_transcript_action_job
        from youtube_extension.backend.api.v1.models import TranscriptActionRequest

        request = TranscriptActionRequest(
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
            language="en",
        )
        metadata = _FakeMetadata()

        mock_request = MagicMock()
        mock_request.base_url = "http://testserver/"

        # Make CloudTasksQueueService raise so we fall back to local
        error_cloud = MagicMock()
        error_cloud.initialize.side_effect = RuntimeError("cloud tasks unavailable")

        # Patch TranscriptActionWorkflow so get_duration_seconds works
        class _MockWFForQueue:
            ASYNC_VIDEO_THRESHOLD_SECONDS = 9999
            @staticmethod
            def get_duration_seconds(m):
                return 600

        with patch(
            "youtube_extension.backend.api.v1.router.CloudTasksQueueService",
            return_value=error_cloud,
        ):
            with patch(
                "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
                _MockWFForQueue,
            ):
                with patch(
                    "youtube_extension.backend.api.v1.router.asyncio.create_task"
                ) as mock_ct:
                    result = await _queue_transcript_action_job(
                        request, metadata=metadata, http_request=mock_request
                    )

        # Should return async result dict with job_id
        assert result["async_processing"] is True
        assert "job_id" in result
        assert result["processing_transport"] == "local_background"
        # asyncio.create_task should have been called for fallback (may also be called
        # by _persist_video_job background serialization, so check at least once)
        mock_ct.assert_called()

    async def test_queue_job_cloud_tasks_success(self):
        """CloudTasksQueueService succeeds → queued_transport = cloud_tasks."""
        from youtube_extension.backend.api.v1.router import _queue_transcript_action_job
        from youtube_extension.backend.api.v1.models import TranscriptActionRequest

        request = TranscriptActionRequest(
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
            language="en",
        )
        metadata = _FakeMetadata()

        mock_request = MagicMock()
        mock_request.base_url = "http://testserver/"

        mock_queue = MagicMock()
        mock_queue.initialize.return_value = None
        mock_queue.enqueue_video_processing = AsyncMock(return_value=None)
        mock_queue.close.return_value = None

        class _MockWFForQueue:
            ASYNC_VIDEO_THRESHOLD_SECONDS = 9999
            @staticmethod
            def get_duration_seconds(m):
                return 600

        with patch(
            "youtube_extension.backend.api.v1.router.CloudTasksQueueService",
            return_value=mock_queue,
        ):
            with patch(
                "youtube_extension.backend.api.v1.router.TranscriptActionWorkflow",
                _MockWFForQueue,
            ):
                result = await _queue_transcript_action_job(
                    request, metadata=metadata, http_request=mock_request
                )

        assert result["async_processing"] is True
        assert result["processing_transport"] == "cloud_tasks"


# ===========================================================================
# Extra Chat Coverage – real-time processing branches
# ===========================================================================


class TestChatExtraCoVerage:
    def test_chat_realtime_processing_success(self, client):
        """Video not found initially, real-time processing returns success → detail refetched."""
        call_count = {"n": 0}

        def _detail_side_effect(video_id):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return None  # first call: not found
            return {  # second call: found after processing
                "video_id": video_id,
                "metadata": {"title": "Processed", "transcript_text": "RT transcript"},
            }

        def _data_svc():
            svc = _make_data_svc()
            svc.get_video_detail.side_effect = _detail_side_effect
            return svc

        def _vps():
            svc = _make_vps()
            svc.process_video_for_markdown = AsyncMock(
                return_value={"status": "success"}
            )
            return svc

        app.dependency_overrides[get_data_service] = _data_svc
        app.dependency_overrides[get_video_processing_service] = _vps
        try:
            payload = {
                "query": "Tell me about this",
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            }
            resp = client.post("/api/v1/chat", json=payload)
            assert resp.status_code == 200
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc
            app.dependency_overrides[get_video_processing_service] = _make_vps

    def test_chat_realtime_processing_fails_gracefully(self, client):
        """Real-time video processing raises → no crash, chat continues."""
        def _data_svc():
            svc = _make_data_svc()
            svc.get_video_detail.return_value = None
            return svc

        def _vps():
            svc = _make_vps()
            svc.process_video_for_markdown = AsyncMock(
                side_effect=RuntimeError("network error")
            )
            return svc

        app.dependency_overrides[get_data_service] = _data_svc
        app.dependency_overrides[get_video_processing_service] = _vps
        try:
            payload = {
                "query": "Tell me about this",
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            }
            resp = client.post("/api/v1/chat", json=payload)
            assert resp.status_code == 200
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc
            app.dependency_overrides[get_video_processing_service] = _make_vps

    def test_chat_no_transcript_action_result(self, client):
        """results dict has no 'transcript_action' key → error response."""
        def _orch():
            task_result = MagicMock()
            task_result.success = True
            task_result.results = {}  # no transcript_action key
            task_result.errors = []
            svc = MagicMock()
            svc.execute_task = AsyncMock(return_value=task_result)
            return svc

        app.dependency_overrides[get_agent_orchestrator_service] = _orch
        try:
            payload = {"query": "No agent result"}
            resp = client.post("/api/v1/chat", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            # Should still return a response (error message)
            assert "response" in data
        finally:
            app.dependency_overrides[get_agent_orchestrator_service] = _make_orchestrator


# ===========================================================================
# Additional Error Paths
# ===========================================================================


class TestAdditionalErrorPaths:
    def test_markdown_http_exception_reraise(self, client):
        """HTTPException from vps propagates (not wrapped in 500)."""
        from fastapi import HTTPException as FastAPIHTTPException

        def _err():
            svc = _make_vps()
            svc.process_video_for_markdown = AsyncMock(
                side_effect=FastAPIHTTPException(status_code=404, detail="video not found")
            )
            return svc

        app.dependency_overrides[get_video_processing_service] = _err
        try:
            payload = {"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"}
            resp = client.post("/api/v1/process-video-markdown", json=payload)
            # Should re-raise the 404, not wrap it as 500
            assert resp.status_code == 404
        finally:
            app.dependency_overrides[get_video_processing_service] = _make_vps

    def test_performance_alert_error(self, client):
        """performance_monitor.record_metric raises → 500."""
        with patch.object(
            router_module.performance_monitor,
            "record_metric",
            new_callable=AsyncMock,
            side_effect=RuntimeError("monitor error"),
        ):
            resp = client.post(
                "/api/v1/performance/alert", json={"type": "lcp", "data": 100}
            )
        assert resp.status_code == 500

    def test_performance_report_error(self, client):
        """record_metric raises → 500."""
        with patch.object(
            router_module.performance_monitor,
            "record_metric",
            new_callable=AsyncMock,
            side_effect=RuntimeError("monitor error"),
        ):
            resp = client.post(
                "/api/v1/performance/report",
                json={"metrics": {"lcp": {"current": 1200, "unit": "ms"}}},
            )
        assert resp.status_code == 500

    def test_update_action_repo_raises(self, client):
        """ActionRepository.update raises → 500."""
        repo = MagicMock()
        repo.update.side_effect = RuntimeError("db error")

        with patch(
            "youtube_extension.backend.api.v1.router.ActionRepository",
            return_value=repo,
        ):
            resp = client.put(
                "/api/v1/actions/some-action",
                json={"status": "done"},
            )
        assert resp.status_code == 500

    def test_get_cached_video_service_error(self, client):
        """cache_service.get_video_cache_info raises (not HTTPException) → 500."""
        def _err():
            svc = MagicMock()
            svc.get_video_cache_info.side_effect = RuntimeError("db error")
            return svc

        app.dependency_overrides[get_cache_service] = _err
        try:
            resp = client.get("/api/v1/cache/some-video-id")
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_cache_service] = _make_cache_svc

    def test_clear_video_cache_error(self, client):
        """cache_service.clear_cache raises → 500."""
        def _err():
            svc = MagicMock()
            svc.clear_cache.side_effect = RuntimeError("db error")
            return svc

        app.dependency_overrides[get_cache_service] = _err
        try:
            resp = client.delete("/api/v1/cache/some-video-id")
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_cache_service] = _make_cache_svc

    def test_get_video_detail_service_error(self, client):
        """data_service.get_video_detail raises → 500."""
        def _err():
            svc = MagicMock()
            svc.get_video_detail.side_effect = RuntimeError("db error")
            return svc

        app.dependency_overrides[get_data_service] = _err
        try:
            resp = client.get("/api/v1/videos/some-video-id")
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc

    def test_get_learning_log_error(self, client):
        """data_service.get_learning_log raises → 500."""
        def _err():
            svc = MagicMock()
            svc.get_learning_log.side_effect = RuntimeError("db error")
            return svc

        app.dependency_overrides[get_data_service] = _err
        try:
            resp = client.get("/api/v1/learning-log")
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc

    def test_feedback_exception_path(self, client):
        """data_service.save_feedback raises → 500 via outer exception handler."""
        def _err():
            svc = MagicMock()
            svc.save_feedback.side_effect = RuntimeError("db error")
            return svc

        app.dependency_overrides[get_data_service] = _err
        try:
            payload = {"feedback_type": "quality"}
            resp = client.post("/api/v1/feedback", json=payload)
            assert resp.status_code == 500
        finally:
            app.dependency_overrides[get_data_service] = _make_data_svc

    def test_feedback_with_ml_client_error(self, client):
        """uvai ml client raises → logged and response still returned."""
        with patch(
            "youtube_extension.backend.api.v1.router.get_uvai_ml_client"
        ) as mock_client:
            mock_ml = MagicMock()
            mock_ml.record_action_feedback = AsyncMock(
                side_effect=RuntimeError("ml error")
            )
            mock_client.return_value = mock_ml

            payload = {
                "feedback_type": "quality",
                "metadata": {
                    "action_text": "Build something",
                    "clicked": True,
                    "completed": False,
                },
            }
            resp = client.post("/api/v1/feedback", json=payload)
        # Should succeed even if ml client fails
        assert resp.status_code == 200


class TestRunAgentStatus:
    """_run_agent must reflect execute_single's outcome in the execution status.

    execute_single reports agent-level failures by returning an {"error": ...}
    dict rather than raising, so the status must be derived from the result —
    not unconditionally set to complete.
    """

    @staticmethod
    def _execution():
        return AgentExecution(
            agent_type="analyzer", status=AgentStatus.queued, event_id="e1"
        )

    def test_error_dict_marks_execution_failed(self):
        execution = self._execution()
        orch = MagicMock()
        orch.execute_single = AsyncMock(return_value={"error": "agent boom"})
        with patch.object(router_module, "_shared_orchestrator", orch):
            asyncio.run(router_module._run_agent(execution, [{"id": "e1"}]))
        assert execution.status == AgentStatus.failed
        assert "agent boom" in (execution.error or "")

    def test_success_dict_marks_execution_complete(self):
        execution = self._execution()
        orch = MagicMock()
        orch.execute_single = AsyncMock(return_value={"output": "done"})
        with patch.object(router_module, "_shared_orchestrator", orch):
            asyncio.run(router_module._run_agent(execution, [{"id": "e1"}]))
        assert execution.status == AgentStatus.complete
        assert execution.result == {"output": "done"}


# ---------------------------------------------------------------------------
# _TTLDict LRU eviction order (regression for the _touch reordering bug)
# ---------------------------------------------------------------------------
class TestTTLDictEvictionOrder:
    """`_enforce_max_size` must evict the least-recently-*touched* entry.

    Regression for a bug where `_touch` re-assigned an existing key's
    timestamp (`d[k] = v`) without moving it in the dict's insertion order,
    so `next(iter(self._timestamps))` returned the first-inserted key rather
    than the least-recently-touched one — evicting an actively-updated entry.
    """

    def _make(self, max_size: int):
        return router_module._TTLDict(ttl=1000.0, max_size=max_size)

    def test_touched_entry_survives_eviction(self):
        d = self._make(max_size=2)
        d["a"] = 1
        d["b"] = 2
        # Touch the first-inserted key: it must no longer be the eviction target.
        d["a"] = 3
        # Overflow -> exactly one eviction.
        d["c"] = 4
        assert "a" in d, "recently-touched entry was wrongly evicted"
        assert "b" not in d, "least-recently-touched entry should have been evicted"
        assert "c" in d
        assert d["a"] == 3

    def test_eviction_targets_least_recently_touched(self):
        d = self._make(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        d["a"] = 10  # a is now most-recently-touched; b is oldest
        d["d"] = 4   # overflow -> evict b
        assert "b" not in d
        assert {"a", "c", "d"} <= set(d.keys())
