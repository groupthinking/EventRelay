"""
Unit tests for cloud-related FastAPI routes.

Covers:
  1. src/youtube_extension/backend/cloud_ai_routes.py
  2. src/youtube_extension/backend/cloud_api_endpoints.py
  3. src/youtube_extension/backend/api/advanced_video_routes.py
  4. src/youtube_extension/backend/api/event_routes.py
  5. src/youtube_extension/backend/api/reporting_routes.py  (fills remaining uncovered lines)
"""

from __future__ import annotations

import sys
import types as _types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure 'src' is on sys.path
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))


# ---------------------------------------------------------------------------
# Helper: make a real package stub (with __path__) so sub-imports work
# ---------------------------------------------------------------------------
def _make_pkg(name: str) -> _types.ModuleType:
    m = _types.ModuleType(name)
    m.__path__ = []  # type: ignore[attr-defined]
    m.__package__ = name
    return m


# ---------------------------------------------------------------------------
# Stub out heavy external dependencies BEFORE any project imports
# ---------------------------------------------------------------------------

# google.cloud stubs (needed by pubsub, videointelligence, vision)
_google = _make_pkg("google")
_google_cloud = _make_pkg("google.cloud")
_google_cloud_pubsub = MagicMock()
sys.modules.setdefault("google", _google)
sys.modules.setdefault("google.cloud", _google_cloud)
sys.modules.setdefault("google.cloud.pubsub_v1", _google_cloud_pubsub)

# httpx is a real package but we want to control it later via patch;
# Provide a minimal stub when missing so the import does not break.
try:
    import httpx as _httpx_real  # noqa: F401 – real httpx available, nothing to stub
except ImportError:
    sys.modules.setdefault("httpx", MagicMock())

# src.integration LEAF-module stubs (needed by advanced_video_routes and
# reporting_routes so their heavy transitive imports don't run here). The `src`
# and `src.integration` packages themselves are real and empty (__init__.py has
# no code), so we let them import normally — stubbing them as fake packages
# would leave a __path__-less package in sys.modules and break other test
# modules (e.g. test_temporal_video_analysis) that import the real leaf modules.
_ce_publisher_mod = MagicMock()
_temporal_mod = MagicMock()
_looker_embedded_mod = MagicMock()

sys.modules.setdefault("src.integration.cloudevents_publisher", _ce_publisher_mod)
sys.modules.setdefault("src.integration.temporal_video_analysis", _temporal_mod)
sys.modules.setdefault("src.integration.looker_embedded", _looker_embedded_mod)


# ---------------------------------------------------------------------------
# Now import the modules under test
# ---------------------------------------------------------------------------
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from youtube_extension.backend.cloud_ai_routes import (
        router as cloud_ai_router,
        CloudAIError,
        CloudAIIntegrator,
        CloudAIProvider,
        AnalysisType,
        VideoAnalysisResult,
        ConfigurationError,
        RateLimitError,
        parse_analysis_types,
        parse_provider,
        get_cloud_ai_config,
        format_analysis_result,
        _get_analysis_type_description,
        _get_provider_description,
    )
    from youtube_extension.backend.cloud_api_endpoints import setup_cloud_api_endpoints
    from youtube_extension.backend.api import advanced_video_routes as _avr_mod
    from youtube_extension.backend.api.advanced_video_routes import router as advanced_router
    from youtube_extension.backend.api.event_routes import router as event_router, process_event, EventPayload
    from youtube_extension.backend.api.reporting_routes import router as reporting_router

# The modules under test are now imported and hold their own references to the
# leaf stubs above. Remove those import-time stubs from sys.modules so they do
# NOT shadow the real leaf modules for other test files that run later in the
# same session (e.g. test_temporal_video_analysis.py, which imports the real
# dataclasses). Only entries that are still exactly the stubs we installed are
# removed — if a real module was already loaded, setdefault never installed our
# fake and this is a no-op.
for _stub_name, _stub_obj in (
    ("src.integration.temporal_video_analysis", _temporal_mod),
    ("src.integration.cloudevents_publisher", _ce_publisher_mod),
    ("src.integration.looker_embedded", _looker_embedded_mod),
):
    if sys.modules.get(_stub_name) is _stub_obj:
        del sys.modules[_stub_name]

from youtube_extension.integrations.cloud_ai.base import DetectionResult

from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers to build minimal FastAPI apps
# ---------------------------------------------------------------------------

def _make_cloud_ai_app() -> FastAPI:
    app = FastAPI()
    app.include_router(cloud_ai_router)
    return app


def _make_cloud_api_app() -> FastAPI:
    app = FastAPI()
    setup_cloud_api_endpoints(app)
    return app


def _make_advanced_app() -> FastAPI:
    app = FastAPI()
    app.include_router(advanced_router)
    return app


def _make_event_app() -> FastAPI:
    app = FastAPI()
    app.include_router(event_router)
    return app


def _make_reporting_app() -> FastAPI:
    app = FastAPI()
    app.include_router(reporting_router)
    return app


# ---------------------------------------------------------------------------
# Shared mock factory for VideoAnalysisResult
# ---------------------------------------------------------------------------

def _make_analysis_result(
    provider=None,
    video_id="auJzb1D-fag",
) -> VideoAnalysisResult:
    if provider is None:
        provider = CloudAIProvider.GOOGLE_CLOUD
    return VideoAnalysisResult(
        provider=provider,
        video_id=video_id,
        analysis_types=[AnalysisType.LABEL_DETECTION, AnalysisType.OBJECT_TRACKING],
        objects=[DetectionResult(label="car", confidence=0.9, timestamp=1.0)],
        labels=[DetectionResult(label="vehicle", confidence=0.85, metadata={"category": "transport"})],
        text_detections=[DetectionResult(label="STOP", confidence=0.95, timestamp=2.0, bounding_box={"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.1})],
        faces=[DetectionResult(label="face", confidence=0.8, timestamp=3.0, bounding_box={"x": 0.4, "y": 0.4, "width": 0.1, "height": 0.1}, metadata={"age_range": "25-35"})],
        logos=[DetectionResult(label="Google", confidence=0.99, timestamp=4.0, bounding_box={"x": 0.5, "y": 0.5, "width": 0.2, "height": 0.1})],
        shots=[{"start_time": 0.0, "end_time": 10.0}],
        scenes=[{"description": "outdoor scene", "start_time": 0.0}],
        processing_time=1.23,
        cost_estimate=0.05,
    )


# ===========================================================================
# Tests for cloud_ai_routes.py
# ===========================================================================

class TestCloudAIRoutes:

    # -------- helpers / utility functions --------

    def test_get_cloud_ai_config_returns_dict(self):
        config = get_cloud_ai_config()
        assert "google_cloud" in config
        assert "aws_rekognition" in config
        assert "azure_vision" in config
        assert "apple_fastvlm" in config

    def test_parse_analysis_types_valid(self):
        result = parse_analysis_types(["label_detection", "object_tracking"])
        assert AnalysisType.LABEL_DETECTION in result
        assert AnalysisType.OBJECT_TRACKING in result

    def test_parse_analysis_types_invalid_raises_http_422(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            parse_analysis_types(["totally_unknown_type"])
        assert exc_info.value.status_code == 400

    def test_parse_provider_none(self):
        assert parse_provider(None) is None

    def test_parse_provider_valid(self):
        result = parse_provider("google_cloud")
        assert result == CloudAIProvider.GOOGLE_CLOUD

    def test_parse_provider_valid_aws(self):
        result = parse_provider("aws_rekognition")
        assert result == CloudAIProvider.AWS_REKOGNITION

    def test_parse_provider_valid_azure(self):
        result = parse_provider("azure_vision")
        assert result == CloudAIProvider.AZURE_VISION

    def test_parse_provider_invalid(self):
        from fastapi import HTTPException as _HTTPException
        with pytest.raises(_HTTPException) as exc_info:
            parse_provider("nonexistent_provider")
        assert exc_info.value.status_code == 400

    def test_parse_provider_invalid_via_endpoint(self):
        client = TestClient(_make_cloud_ai_app())
        response = client.post("/api/v1/cloud-ai/analyze/video", json={
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "analysis_types": ["label_detection"],
            "preferred_provider": "nonexistent_provider",
        })
        assert response.status_code == 400

    def test_format_analysis_result(self):
        result = _make_analysis_result()
        response = format_analysis_result(result)
        assert response.video_id == "auJzb1D-fag"
        assert response.provider == CloudAIProvider.GOOGLE_CLOUD.value
        assert len(response.objects) == 1
        assert response.objects[0]["label"] == "car"
        assert len(response.labels) == 1
        assert len(response.text_detections) == 1
        assert len(response.faces) == 1
        assert len(response.logos) == 1
        assert response.cost_estimate == 0.05

    def test_get_analysis_type_descriptions(self):
        for analysis_type in AnalysisType:
            desc = _get_analysis_type_description(analysis_type)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_get_provider_descriptions_via_endpoint(self):
        client = TestClient(_make_cloud_ai_app())
        response = client.get("/api/v1/cloud-ai/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert len(data["providers"]) > 0
        for item in data["providers"]:
            assert "name" in item
            assert "description" in item

    # -------- GET /api/v1/cloud-ai/analysis-types --------

    def test_get_available_analysis_types(self):
        client = TestClient(_make_cloud_ai_app())
        response = client.get("/api/v1/cloud-ai/analysis-types")
        assert response.status_code == 200
        data = response.json()
        assert "analysis_types" in data
        assert len(data["analysis_types"]) > 0
        for item in data["analysis_types"]:
            assert "name" in item
            assert "description" in item

    # -------- GET /api/v1/cloud-ai/providers --------
    # Note: this endpoint is tested by test_get_provider_descriptions_via_endpoint

    # -------- GET /api/v1/cloud-ai/providers/status --------

    def test_get_provider_status_success(self):
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.get_provider_status = AsyncMock(return_value={
            "google_cloud": {"available": True, "status": "ok"},
        })
        mock_ai.providers = {"google_cloud": MagicMock()}

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.get("/api/v1/cloud-ai/providers/status")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "available_providers" in data
        assert "google_cloud" in data["available_providers"]

    def test_get_provider_status_error(self):
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(side_effect=Exception("connection failed"))
        mock_ai.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.get("/api/v1/cloud-ai/providers/status")
        assert response.status_code == 500

    # -------- POST /api/v1/cloud-ai/analyze/video --------

    def test_analyze_video_success(self):
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.analyze_video = AsyncMock(return_value=_make_analysis_result())

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.post("/api/v1/cloud-ai/analyze/video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "analysis_types": ["label_detection", "object_tracking"],
            })
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "auJzb1D-fag"
        assert "objects" in data

    def test_analyze_video_invalid_analysis_type(self):
        client = TestClient(_make_cloud_ai_app())
        response = client.post("/api/v1/cloud-ai/analyze/video", json={
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "analysis_types": ["invalid_type"],
        })
        assert response.status_code == 400

    def test_analyze_video_invalid_provider(self):
        client = TestClient(_make_cloud_ai_app())
        response = client.post("/api/v1/cloud-ai/analyze/video", json={
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "analysis_types": ["label_detection"],
            "preferred_provider": "nonexistent_provider",
        })
        assert response.status_code == 400

    def test_analyze_video_cloud_ai_error(self):
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.analyze_video = AsyncMock(side_effect=CloudAIError("service down"))

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.post("/api/v1/cloud-ai/analyze/video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "analysis_types": ["label_detection"],
            })
        assert response.status_code == 503

    def test_analyze_video_rate_limit_error(self):
        # RateLimitError is a subclass of CloudAIError, so it's caught by the
        # CloudAIError except clause first and returns 503 (not 429).
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.analyze_video = AsyncMock(side_effect=RateLimitError("too many requests"))

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.post("/api/v1/cloud-ai/analyze/video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "analysis_types": ["label_detection"],
            })
        assert response.status_code in (429, 503)

    def test_analyze_video_configuration_error(self):
        # ConfigurationError is a subclass of CloudAIError, so it's caught by
        # the CloudAIError clause -> 503.
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.analyze_video = AsyncMock(side_effect=ConfigurationError("missing key"))

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.post("/api/v1/cloud-ai/analyze/video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "analysis_types": ["label_detection"],
            })
        assert response.status_code in (500, 503)

    def test_analyze_video_generic_error(self):
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.analyze_video = AsyncMock(side_effect=RuntimeError("unexpected"))

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.post("/api/v1/cloud-ai/analyze/video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "analysis_types": ["label_detection"],
            })
        assert response.status_code == 500

    def test_analyze_video_with_preferred_provider(self):
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.analyze_video = AsyncMock(return_value=_make_analysis_result())

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai), \
             patch("youtube_extension.backend.cloud_ai_routes.parse_provider",
                   return_value=CloudAIProvider.GOOGLE_CLOUD):
            client = TestClient(_make_cloud_ai_app())
            response = client.post("/api/v1/cloud-ai/analyze/video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "analysis_types": ["label_detection"],
                "preferred_provider": "google_cloud",
                "use_fallback": False,
            })
        assert response.status_code == 200

    # -------- POST /api/v1/cloud-ai/analyze/batch --------

    def test_analyze_batch_videos_success(self):
        client = TestClient(_make_cloud_ai_app())
        response = client.post("/api/v1/cloud-ai/analyze/batch", json={
            "video_urls": [
                "https://www.youtube.com/watch?v=auJzb1D-fag",
                "https://www.youtube.com/watch?v=auJzb1D-fag",
            ],
            "analysis_types": ["label_detection"],
            "batch_size": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["video_count"] == 2
        assert "task_id" in data
        assert "batch_size" in data

    def test_analyze_batch_videos_invalid_analysis_type(self):
        client = TestClient(_make_cloud_ai_app())
        response = client.post("/api/v1/cloud-ai/analyze/batch", json={
            "video_urls": ["https://www.youtube.com/watch?v=auJzb1D-fag"],
            "analysis_types": ["garbage_type"],
        })
        assert response.status_code == 400

    # -------- POST /api/v1/cloud-ai/analyze/multi-provider --------

    def test_analyze_video_multi_provider_success(self):
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.multi_provider_analysis = AsyncMock(return_value=[
            _make_analysis_result(CloudAIProvider.GOOGLE_CLOUD),
            _make_analysis_result(CloudAIProvider.AWS_REKOGNITION),
        ])

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.post("/api/v1/cloud-ai/analyze/multi-provider", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "analysis_types": ["label_detection"],
            })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_analyze_video_multi_provider_error(self):
        mock_ai = AsyncMock()
        mock_ai.__aenter__ = AsyncMock(return_value=mock_ai)
        mock_ai.__aexit__ = AsyncMock(return_value=False)
        mock_ai.multi_provider_analysis = AsyncMock(side_effect=Exception("multi failed"))

        with patch("youtube_extension.backend.cloud_ai_routes.CloudAIIntegrator", return_value=mock_ai):
            client = TestClient(_make_cloud_ai_app())
            response = client.post("/api/v1/cloud-ai/analyze/multi-provider", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "analysis_types": ["label_detection"],
            })
        assert response.status_code == 500


# ===========================================================================
# Tests for cloud_api_endpoints.py
# ===========================================================================

class TestCloudApiEndpoints:

    def _build_app(self) -> TestClient:
        return TestClient(_make_cloud_api_app())

    # Helper for a successful VideoProcessingState-like mock
    @staticmethod
    def _make_state(video_id="auJzb1D-fag", status="completed", video_url="https://yt.com/watch?v=auJzb1D-fag"):
        state = MagicMock()
        state.video_id = video_id
        state.status = status
        state.current_stage = "done"
        state.created_at = "2026-06-01T00:00:00Z"
        state.updated_at = "2026-06-01T00:01:00Z"
        state.processing_time = 2.5
        state.error_message = None
        state.video_url = video_url
        state.metadata = {"title": "test"}
        state.transcript = {"text": "hello"}
        state.ai_analysis = {"summary": "great video"}
        state.success = True
        state.from_cache = False
        return state

    # -------- POST /api/v3/process-video (async) --------

    def test_process_video_async(self):
        mock_processor = AsyncMock()
        mock_processor._extract_video_id = MagicMock(return_value="auJzb1D-fag")
        mock_processor.process_video_async = AsyncMock(return_value="task-123")

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.post("/api/v3/process-video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "priority": 5,
                "async_processing": True,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "auJzb1D-fag"
        assert data["task_id"] == "task-123"
        assert data["status"] == "queued"

    def test_process_video_sync(self):
        state = self._make_state()
        state.error_message = None

        mock_processor = AsyncMock()
        mock_processor._extract_video_id = MagicMock(return_value="auJzb1D-fag")
        mock_processor.process_video_sync = AsyncMock(return_value=state)

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.post("/api/v3/process-video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "async_processing": False,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "auJzb1D-fag"
        assert data["status"] == "completed"

    def test_process_video_sync_failed(self):
        state = self._make_state(status="failed")
        state.success = False
        state.error_message = "something went wrong"

        mock_processor = AsyncMock()
        mock_processor._extract_video_id = MagicMock(return_value="auJzb1D-fag")
        mock_processor.process_video_sync = AsyncMock(return_value=state)

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.post("/api/v3/process-video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "async_processing": False,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "something went wrong"

    def test_process_video_exception(self):
        mock_processor = AsyncMock()
        mock_processor._extract_video_id = MagicMock(side_effect=Exception("boom"))

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.post("/api/v3/process-video", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            })
        assert response.status_code == 500

    # -------- POST /api/v3/process-video-task --------

    def test_process_video_task_no_header_returns_403(self):
        client = self._build_app()
        response = client.post("/api/v3/process-video-task", json={
            "video_id": "auJzb1D-fag",
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
        })
        assert response.status_code == 403

    def test_process_video_task_no_header_malformed_payload_still_403(self):
        client = self._build_app()
        response = client.post("/api/v3/process-video-task", json={
            "video_id": "auJzb1D-fag",
        })
        assert response.status_code == 403

    def test_process_video_task_with_header_success(self):
        state = self._make_state()

        mock_processor = AsyncMock()
        mock_processor.process_video_sync = AsyncMock(return_value=state)

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.post(
                "/api/v3/process-video-task",
                json={
                    "video_id": "auJzb1D-fag",
                    "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                },
                headers={"X-CloudTasks-TaskName": "task-abc-123"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["video_id"] == "auJzb1D-fag"

    def test_process_video_task_with_header_malformed_payload_returns_422(self):
        client = self._build_app()
        response = client.post(
            "/api/v3/process-video-task",
            json={"video_id": "auJzb1D-fag"},
            headers={"X-CloudTasks-TaskName": "task-abc-123"},
        )
        assert response.status_code == 422

    def test_process_video_task_with_header_invalid_utf8_returns_422(self):
        client = self._build_app()
        response = client.post(
            "/api/v3/process-video-task",
            content=b"\xff",
            headers={"X-CloudTasks-TaskName": "task-abc-123"},
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["type"] == "json_invalid"

    def test_process_video_task_documents_request_body_schema(self):
        client = self._build_app()
        spec = client.app.openapi()
        operation = spec["paths"]["/api/v3/process-video-task"]["post"]
        schema = operation["requestBody"]["content"]["application/json"]["schema"]
        assert operation["requestBody"]["required"] is True
        assert set(schema["required"]) == {"video_id", "video_url"}

    def test_process_video_task_exception(self):
        mock_processor = AsyncMock()
        mock_processor.process_video_sync = AsyncMock(side_effect=Exception("processing failed"))

        mock_firestore = AsyncMock()
        mock_firestore.update_state = AsyncMock()

        with patch("youtube_extension.backend.cloud_api_endpoints.get_firestore_service",
                   AsyncMock(return_value=mock_firestore)), \
             patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.post(
                "/api/v3/process-video-task",
                json={
                    "video_id": "auJzb1D-fag",
                    "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                },
                headers={"X-CloudTasks-TaskName": "task-error"},
            )
        assert response.status_code == 500

    # -------- POST /api/v3/batch-process --------

    def test_batch_process_success(self):
        mock_processor = AsyncMock()
        mock_processor.batch_process_async = AsyncMock(return_value=["task-1", "task-2"])

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.post("/api/v3/batch-process", json={
                "video_urls": [
                    "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "https://www.youtube.com/watch?v=vid2",
                ],
                "priority": 1,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["queued_count"] == 2

    def test_batch_process_too_many_videos(self):
        client = self._build_app()
        response = client.post("/api/v3/batch-process", json={
            "video_urls": [f"https://yt.com/watch?v=vid{i}" for i in range(51)],
            "priority": 0,
        })
        assert response.status_code == 400

    def test_batch_process_exception(self):
        mock_processor = AsyncMock()
        mock_processor.batch_process_async = AsyncMock(side_effect=Exception("queue error"))

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.post("/api/v3/batch-process", json={
                "video_urls": ["https://www.youtube.com/watch?v=auJzb1D-fag"],
            })
        assert response.status_code == 500

    # -------- GET /api/v3/videos/{video_id}/status --------

    def test_get_video_status_found(self):
        state = self._make_state()
        mock_processor = AsyncMock()
        mock_processor.get_processing_status = AsyncMock(return_value=state)

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.get("/api/v3/videos/auJzb1D-fag/status")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "auJzb1D-fag"
        assert data["status"] == "completed"

    def test_get_video_status_not_found(self):
        mock_processor = AsyncMock()
        mock_processor.get_processing_status = AsyncMock(return_value=None)

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.get("/api/v3/videos/unknown-id/status")
        assert response.status_code == 404

    def test_get_video_status_exception(self):
        mock_processor = AsyncMock()
        mock_processor.get_processing_status = AsyncMock(side_effect=Exception("db error"))

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.get("/api/v3/videos/auJzb1D-fag/status")
        assert response.status_code == 500

    # -------- GET /api/v3/videos/{video_id}/result --------

    def test_get_video_result_found(self):
        state = self._make_state()
        mock_processor = AsyncMock()
        mock_processor.get_processing_status = AsyncMock(return_value=state)

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.get("/api/v3/videos/auJzb1D-fag/result")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "auJzb1D-fag"
        assert data["status"] == "completed"

    def test_get_video_result_not_found(self):
        mock_processor = AsyncMock()
        mock_processor.get_processing_status = AsyncMock(return_value=None)

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.get("/api/v3/videos/missing/result")
        assert response.status_code == 404

    def test_get_video_result_exception(self):
        mock_processor = AsyncMock()
        mock_processor.get_processing_status = AsyncMock(side_effect=Exception("db error"))

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_video_processor",
                   return_value=mock_processor):
            client = self._build_app()
            response = client.get("/api/v3/videos/auJzb1D-fag/result")
        assert response.status_code == 500

    # -------- GET /api/v3/queue/stats --------

    def test_get_queue_stats_success(self):
        mock_tasks_service = AsyncMock()
        mock_tasks_service.get_queue_stats = AsyncMock(return_value={"pending": 3, "running": 1})

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_tasks_service",
                   return_value=mock_tasks_service):
            client = self._build_app()
            response = client.get("/api/v3/queue/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stats" in data

    def test_get_queue_stats_error(self):
        mock_tasks_service = AsyncMock()
        mock_tasks_service.get_queue_stats = AsyncMock(side_effect=Exception("queue unavailable"))

        with patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_tasks_service",
                   return_value=mock_tasks_service):
            client = self._build_app()
            response = client.get("/api/v3/queue/stats")
        assert response.status_code == 200  # returns degraded, not 500
        data = response.json()
        assert data["success"] is False

    # -------- GET /api/v3/cloud-status --------

    def test_get_cloud_status_all_operational(self):
        mock_firestore = AsyncMock()
        mock_tasks_service = AsyncMock()
        mock_tasks_service.get_queue_stats = AsyncMock(return_value={"pending": 0})
        mock_vertex = MagicMock()

        with patch("youtube_extension.backend.cloud_api_endpoints.get_firestore_service",
                   return_value=mock_firestore), \
             patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_tasks_service",
                   return_value=mock_tasks_service), \
             patch("youtube_extension.backend.cloud_api_endpoints.get_vertex_ai_service",
                   return_value=mock_vertex):
            client = self._build_app()
            response = client.get("/api/v3/cloud-status")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "operational"
        assert "services" in data

    def test_get_cloud_status_degraded(self):
        mock_firestore_call = AsyncMock(side_effect=Exception("firestore down"))
        mock_tasks_service = AsyncMock()
        mock_tasks_service.get_queue_stats = AsyncMock(return_value={})
        mock_vertex = MagicMock()

        with patch("youtube_extension.backend.cloud_api_endpoints.get_firestore_service",
                   mock_firestore_call), \
             patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_tasks_service",
                   return_value=mock_tasks_service), \
             patch("youtube_extension.backend.cloud_api_endpoints.get_vertex_ai_service",
                   return_value=mock_vertex):
            client = self._build_app()
            response = client.get("/api/v3/cloud-status")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "degraded"

    def test_get_cloud_status_vertex_error(self):
        mock_firestore = AsyncMock()
        mock_tasks_service = AsyncMock()
        mock_tasks_service.get_queue_stats = AsyncMock(return_value={})

        with patch("youtube_extension.backend.cloud_api_endpoints.get_firestore_service",
                   return_value=mock_firestore), \
             patch("youtube_extension.backend.cloud_api_endpoints.get_cloud_tasks_service",
                   return_value=mock_tasks_service), \
             patch("youtube_extension.backend.cloud_api_endpoints.get_vertex_ai_service",
                   side_effect=Exception("vertex unavailable")):
            client = self._build_app()
            response = client.get("/api/v3/cloud-status")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "degraded"


# ===========================================================================
# Tests for advanced_video_routes.py
# ===========================================================================

class TestAdvancedVideoRoutes:

    def _client(self) -> TestClient:
        return TestClient(_make_advanced_app())

    def _make_mock_analyzer(self):
        analyzer = AsyncMock()
        analyzer.close = AsyncMock()
        return analyzer

    # -------- POST /api/v1/video/temporal/segment --------

    def test_analyze_segment_success(self):
        seg_result = MagicMock()
        seg_result.summary = "Test summary"
        seg_result.key_events = ["event1"]
        seg_result.timestamps = [{"time": "2:30", "desc": "key moment"}]

        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.analyze_segment = AsyncMock(return_value=seg_result)

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/segment", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "start_time": "2:30",
                "end_time": "5:45",
                "focus": "code",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["segment"]["start_time"] == "2:30"
        assert data["analysis"]["summary"] == "Test summary"

    def test_analyze_segment_error(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.analyze_segment = AsyncMock(side_effect=Exception("API error"))

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/segment", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "start_time": "0:00",
                "end_time": "1:00",
            })
        assert response.status_code == 500

    # -------- POST /api/v1/video/temporal/events --------

    def test_extract_temporal_events_no_publish(self):
        evt = MagicMock()
        evt.timestamp = "1:00"
        evt.event_type = "code_change"
        evt.description = "Changed import"
        evt.confidence = 0.9
        evt.metadata = {}

        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.extract_temporal_events = AsyncMock(return_value=[evt])

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/events", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "event_types": ["code_change"],
                "publish_events": False,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["events_count"] == 1
        assert data["published"] is False

    def test_extract_temporal_events_with_publish(self):
        evt = MagicMock()
        evt.timestamp = "2:00"
        evt.event_type = "api_call"
        evt.description = "Called REST API"
        evt.confidence = 0.8
        evt.metadata = {}

        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.extract_temporal_events = AsyncMock(return_value=[evt])

        mock_publisher = AsyncMock()
        mock_publisher.publish = AsyncMock(return_value="event-id-123")
        mock_publisher.close = AsyncMock()

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer), \
             patch.object(_avr_mod, "create_publisher", return_value=mock_publisher):
            response = self._client().post("/api/v1/video/temporal/events", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "publish_events": True,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["published"] is True
        assert "event-id-123" in data["published_event_ids"]

    def test_extract_temporal_events_error(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.extract_temporal_events = AsyncMock(side_effect=Exception("analysis failed"))

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/events", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            })
        assert response.status_code == 500

    # -------- POST /api/v1/video/temporal/question --------

    def test_answer_temporal_question_success(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.temporal_question = AsyncMock(return_value="The API is REST")

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/question", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "question": "What API is called?",
                "time_context": "between 2:30 and 5:00",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "What API is called?"
        assert data["answer"] == "The API is REST"

    def test_answer_temporal_question_error(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.temporal_question = AsyncMock(side_effect=Exception("timeout"))

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/question", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "question": "What happens?",
            })
        assert response.status_code == 500

    # -------- POST /api/v1/video/temporal/timeline --------

    def test_create_timeline_success(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.create_timeline = AsyncMock(return_value=[
            {"time": "0:00", "description": "Intro"}
        ])

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/timeline", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "granularity": "medium",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "medium"
        assert len(data["timeline"]) == 1

    def test_create_timeline_invalid_granularity(self):
        response = self._client().post("/api/v1/video/temporal/timeline", json={
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "granularity": "ultra",
        })
        assert response.status_code == 400

    def test_create_timeline_valid_granularities(self):
        for granularity in ("fine", "medium", "coarse"):
            mock_analyzer = self._make_mock_analyzer()
            mock_analyzer.create_timeline = AsyncMock(return_value=[])

            with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
                response = self._client().post("/api/v1/video/temporal/timeline", json={
                    "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "granularity": granularity,
                })
            assert response.status_code == 200

    def test_create_timeline_error(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.create_timeline = AsyncMock(side_effect=Exception("model error"))

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/timeline", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "granularity": "coarse",
            })
        assert response.status_code == 500

    # -------- POST /api/v1/video/temporal/compare-segments --------

    def test_compare_segments_success(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.compare_segments = AsyncMock(return_value={"diff": "segment 1 is faster"})

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/compare-segments", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "segments": [["1:00", "2:00"], ["3:00", "4:00"]],
                "comparison_focus": "code quality",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["segments_compared"] == 2
        assert data["comparison_focus"] == "code quality"

    def test_compare_segments_error(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.compare_segments = AsyncMock(side_effect=Exception("compare failed"))

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/compare-segments", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "segments": [["0:00", "1:00"]],
            })
        assert response.status_code == 500

    # -------- POST /api/v1/video/temporal/tutorial-steps --------

    def test_extract_tutorial_steps_success(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.extract_tutorial_steps = AsyncMock(return_value=[
            {"step": 1, "timestamp": "0:30", "description": "Install dependencies"},
            {"step": 2, "timestamp": "2:00", "description": "Configure settings"},
        ])

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/tutorial-steps", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["steps_count"] == 2
        assert len(data["steps"]) == 2

    def test_extract_tutorial_steps_error(self):
        mock_analyzer = self._make_mock_analyzer()
        mock_analyzer.extract_tutorial_steps = AsyncMock(side_effect=Exception("extraction failed"))

        with patch.object(_avr_mod, "TemporalVideoAnalyzer", return_value=mock_analyzer):
            response = self._client().post("/api/v1/video/temporal/tutorial-steps", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            })
        assert response.status_code == 500

    # -------- POST /api/v1/video/analyze/structured --------

    def test_analyze_with_schema_success(self):
        mock_service_result = MagicMock()
        mock_service_result.response = '{"summary": "great video", "key_points": ["point1"]}'

        mock_gemini_service = AsyncMock()
        mock_gemini_service.generate_content_async = AsyncMock(return_value=mock_service_result)

        mock_gemini_config = MagicMock()
        mock_gemini_module = MagicMock()
        mock_gemini_module.GeminiConfig = mock_gemini_config
        mock_gemini_module.GeminiService = MagicMock(return_value=mock_gemini_service)

        with patch.dict(sys.modules, {
            "src.youtube_extension.services.ai.gemini_service": mock_gemini_module,
            "youtube_extension.services.ai.gemini_service": mock_gemini_module,
        }):
            response = self._client().post("/api/v1/video/analyze/structured", json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "prompt": "Summarize this video",
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "key_points": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "publish_result": False,
            })
        assert response.status_code == 200

    def test_analyze_with_schema_error(self):
        response = self._client().post("/api/v1/video/analyze/structured", json={
            "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
            "prompt": "Summarize",
            "schema": {"type": "object"},
            "publish_result": False,
        })
        assert response.status_code == 500

    # -------- POST /api/v1/video/publish-event --------

    def test_publish_video_event_success(self):
        mock_publisher = AsyncMock()
        mock_publisher.publish = AsyncMock(return_value="pub-event-id-456")
        mock_publisher.close = AsyncMock()

        with patch.object(_avr_mod, "create_publisher", return_value=mock_publisher):
            response = self._client().post(
                "/api/v1/video/publish-event",
                params={
                    "source": "/video-processor",
                    "event_type": "com.eventrelay.video.processed",
                    "subject": "https://www.youtube.com/watch?v=auJzb1D-fag",
                    "backend": "file",
                },
                json={"video_id": "auJzb1D-fag", "status": "done"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["event_id"] == "pub-event-id-456"

    def test_publish_video_event_error(self):
        mock_publisher = AsyncMock()
        mock_publisher.publish = AsyncMock(side_effect=Exception("publish failed"))
        mock_publisher.close = AsyncMock()

        with patch.object(_avr_mod, "create_publisher", return_value=mock_publisher):
            response = self._client().post(
                "/api/v1/video/publish-event",
                params={
                    "source": "/video-processor",
                    "event_type": "com.eventrelay.video.processed",
                },
                json={"video_id": "auJzb1D-fag"},
            )
        assert response.status_code == 500


# ===========================================================================
# Tests for event_routes.py
# ===========================================================================

class TestEventRoutes:

    def _client(self) -> TestClient:
        return TestClient(_make_event_app())

    def test_ingest_event_accepted_type(self):
        response = self._client().post("/api/v1/events/", json={
            "type": "user_login",
            "data": {"user_id": "user-42"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["type"] == "user_login"

    def test_ingest_event_ignored_type(self):
        response = self._client().post("/api/v1/events/", json={
            "type": "user_logout",
            "data": {"user_id": "user-42"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert "user_logout" in data["metadata"]["message"]

    def test_ingest_event_missing_type_returns_422(self):
        response = self._client().post("/api/v1/events/", json={
            "data": {"some_field": "value"},
        })
        assert response.status_code == 422

    def test_ingest_event_no_data(self):
        response = self._client().post("/api/v1/events/", json={
            "type": "user_login",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

    def test_ingest_event_with_timestamp(self):
        response = self._client().post("/api/v1/events/", json={
            "type": "user_login",
            "data": {"user_id": "alice"},
            "timestamp": "2026-06-01T12:00:00",
        })
        assert response.status_code == 200

    def test_process_event_helper_user_login(self, capsys):
        """Test the standalone process_event function."""
        from core.event_types import migrate_legacy_type

        payload = EventPayload(type="user_login", data={"user_id": "bob"})
        process_event(payload, migrate_legacy_type(payload.type))
        captured = capsys.readouterr()
        assert "bob" in captured.out

    def test_process_event_helper_unknown_user(self, capsys):
        """process_event when user_id key is missing."""
        from core.event_types import migrate_legacy_type

        payload = EventPayload(type="user_login", data={})
        process_event(payload, migrate_legacy_type(payload.type))
        captured = capsys.readouterr()
        assert "user_login" in captured.out

    def test_ingest_event_with_extra_fields(self):
        """EventPayload allows extra fields (Config.extra = allow)."""
        response = self._client().post("/api/v1/events/", json={
            "type": "user_login",
            "data": {"user_id": "user-99"},
            "source": "mobile_app",
            "session_id": "sess-xyz",
        })
        assert response.status_code == 200

    def test_ingest_event_process_raises_returns_500(self):
        """When process_event raises, ingest_event returns 500."""
        import youtube_extension.backend.api.event_routes as _er
        with patch.object(_er, "process_event", side_effect=RuntimeError("handler crash")):
            response = self._client().post("/api/v1/events/", json={
                "type": "user_login",
                "data": {"user_id": "crash-user"},
            })
        assert response.status_code == 500


# ===========================================================================
# Tests for reporting_routes.py  (fill remaining uncovered lines)
# ===========================================================================

class TestReportingRoutes:

    def _client(self) -> TestClient:
        return TestClient(_make_reporting_app())

    def test_list_dashboards(self):
        response = self._client().get("/api/v1/reporting/dashboards", params={"tenant_id": "tenant-abc"})
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-abc"
        assert len(data["dashboards"]) == 3

    def test_list_dashboards_requires_tenant_id(self):
        response = self._client().get("/api/v1/reporting/dashboards")
        assert response.status_code == 422

    def _client_with_looker(self, mock_service) -> TestClient:
        """Build a TestClient with LookerEmbeddedService overridden via dependency_overrides."""
        from youtube_extension.backend.api.reporting_routes import get_looker_service
        app = _make_reporting_app()
        app.dependency_overrides[get_looker_service] = lambda: mock_service
        return TestClient(app)

    def test_generate_dashboard_url_success(self):
        """Mock LookerEmbeddedService to return a URL."""
        mock_service = MagicMock()
        mock_service.get_tenant_dashboard_url = MagicMock(
            return_value="https://looker.example.com/embed/dashboards/1?sig=abc"
        )

        response = self._client_with_looker(mock_service).post(
            "/api/v1/reporting/embed/dashboard",
            json={
                "dashboard_id": "events_overview",
                "tenant_id": "tenant-xyz",
                "user_id": "user-001",
                "user_email": "alice@example.com",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "embed_url" in data
        assert "looker.example.com" in data["embed_url"]

    def test_generate_dashboard_url_service_error(self):
        """Service error propagates as a sanitized HTTP 500 (no internal detail leaked)."""
        mock_service = MagicMock()
        mock_service.get_tenant_dashboard_url = MagicMock(
            side_effect=Exception("Looker unavailable")
        )

        response = self._client_with_looker(mock_service).post(
            "/api/v1/reporting/embed/dashboard",
            json={
                "dashboard_id": "cost_usage",
                "tenant_id": "tenant-xyz",
                "user_id": "user-001",
                "user_email": "bob@example.com",
            }
        )
        assert response.status_code == 500
        # The handler sanitizes 500 bodies to a static string (CWE-209 hardening);
        # the full exception is logged server-side, never returned to the client.
        detail = response.json()["detail"]
        assert detail == "Internal server error"
        assert "Looker unavailable" not in detail
        assert "Failed to generate" not in detail

    def test_generate_dashboard_url_missing_fields(self):
        """Missing required fields return 422."""
        # Override the Looker dependency so this test is order-independent:
        # if another test imported the real backend first, the leaf-module
        # stub above never installed and the real service would raise before
        # request validation could return 422.
        response = self._client_with_looker(MagicMock()).post(
            "/api/v1/reporting/embed/dashboard", json={
                "dashboard_id": "events_overview",
                # missing tenant_id, user_id, user_email
            })
        assert response.status_code == 422

    # -------- CWE-209: additional coverage for sanitized 500 detail --------

    @pytest.mark.parametrize(
        "exc",
        [
            Exception("Looker unavailable"),
            ValueError("db_password=super-secret-123"),
            KeyError("client_secret"),
            RuntimeError("Traceback (most recent call last): connection to 10.0.0.5:5432 refused"),
            Exception(""),
        ],
        ids=["generic", "value_error_with_secret", "key_error", "runtime_error_with_internals", "empty_message"],
    )
    def test_generate_dashboard_url_error_detail_always_sanitized(self, exc):
        """Regardless of exception type or message content, the 500 detail
        returned to the client must always be the static generic string and
        must never contain any fragment of the original exception text."""
        mock_service = MagicMock()
        mock_service.get_tenant_dashboard_url = MagicMock(side_effect=exc)

        response = self._client_with_looker(mock_service).post(
            "/api/v1/reporting/embed/dashboard",
            json={
                "dashboard_id": "cost_usage",
                "tenant_id": "tenant-xyz",
                "user_id": "user-001",
                "user_email": "bob@example.com",
            }
        )
        assert response.status_code == 500
        body = response.json()
        assert body == {"detail": "Internal server error"}
        exc_text = str(exc)
        if exc_text:
            assert exc_text not in body["detail"]

    def test_generate_dashboard_url_error_logs_original_exception(self):
        """The original exception must still be logged server-side (with
        traceback) even though it is withheld from the HTTP response, so
        operators retain the ability to debug failures."""
        mock_service = MagicMock()
        mock_service.get_tenant_dashboard_url = MagicMock(
            side_effect=Exception("Looker unavailable")
        )

        import youtube_extension.backend.api.reporting_routes as _reporting_mod

        with patch.object(_reporting_mod, "logger") as mock_logger:
            response = self._client_with_looker(mock_service).post(
                "/api/v1/reporting/embed/dashboard",
                json={
                    "dashboard_id": "cost_usage",
                    "tenant_id": "tenant-xyz",
                    "user_id": "user-001",
                    "user_email": "bob@example.com",
                }
            )

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert "Looker unavailable" in args[0]
        assert kwargs.get("exc_info") is True

    def test_generate_dashboard_url_error_response_has_no_extra_keys(self):
        """The sanitized error body must only expose the `detail` field and
        must not leak `embed_url` or any other internal data on failure."""
        mock_service = MagicMock()
        mock_service.get_tenant_dashboard_url = MagicMock(
            side_effect=Exception("Looker unavailable")
        )

        response = self._client_with_looker(mock_service).post(
            "/api/v1/reporting/embed/dashboard",
            json={
                "dashboard_id": "cost_usage",
                "tenant_id": "tenant-xyz",
                "user_id": "user-001",
                "user_email": "bob@example.com",
            }
        )
        assert response.status_code == 500
        assert set(response.json().keys()) == {"detail"}

    def test_generate_dashboard_url_success_after_prior_error(self):
        """A subsequent successful call through the same client is unaffected by
        a prior failure - the sanitized error path leaves no lingering state."""
        mock_service = MagicMock()
        mock_service.get_tenant_dashboard_url = MagicMock(
            side_effect=[
                Exception("Looker unavailable"),
                "https://looker.example.com/embed/dashboards/2?sig=def",
            ]
        )

        client = self._client_with_looker(mock_service)

        # First request: the service raises, so we expect a sanitized 500.
        error_response = client.post(
            "/api/v1/reporting/embed/dashboard",
            json={
                "dashboard_id": "cost_usage",
                "tenant_id": "tenant-xyz",
                "user_id": "user-001",
                "user_email": "bob@example.com",
            }
        )
        assert error_response.status_code == 500
        assert error_response.json() == {"detail": "Internal server error"}

        # Second request: the service now returns a URL - success must not be
        # blocked by any state left over from the previous failure.
        ok_response = client.post(
            "/api/v1/reporting/embed/dashboard",
            json={
                "dashboard_id": "video_analytics",
                "tenant_id": "tenant-xyz",
                "user_id": "user-002",
                "user_email": "carol@example.com",
            }
        )
        assert ok_response.status_code == 200
        assert ok_response.json() == {
            "embed_url": "https://looker.example.com/embed/dashboards/2?sig=def"
        }
