"""
Unit tests for src/youtube_extension/backend/real_api_endpoints.py

Covers:
- Pydantic request/response models
- init_real_api_services helper
- setup_real_api_endpoints - all route handlers:
    POST /api/v2/process-video
    POST /api/v2/validate-video
    POST /api/v2/batch-process
    GET  /api/v2/videos/list
    GET  /api/v2/videos/{video_id}
    GET  /api/v2/cost-dashboard
    GET  /api/v2/usage-analytics
    GET  /api/v2/optimization-recommendations
    GET  /api/v2/service-status
    DELETE /api/v2/cache/clear
    POST /api/v2/search-videos
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Ensure src/ is importable
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# ---------------------------------------------------------------------------
# Imports under test (module-level side-effects are fine; services are already
# initialised at import time via init_real_api_services())
# ---------------------------------------------------------------------------
from youtube_extension.backend.real_api_endpoints import (  # noqa: E402
    _CACHE_MISS,
    _VALIDATION_MAX_BYTES,
    BatchProcessingRequest,
    VideoAnalysisResponse,
    VideoProcessingRequest,
    VideoValidationRequest,
    _collect_processed_videos_sync,
    _read_video_analysis_sync,
    init_real_api_services,
    setup_real_api_endpoints,
)

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------


def _make_search_result(video_id: str = "auJzb1D-fag") -> MagicMock:
    r = MagicMock()
    r.video_id = video_id
    r.title = "Test Video"
    r.description = "A test video"
    r.channel_title = "Test Channel"
    r.published_at = "2026-01-01T00:00:00Z"
    r.thumbnail_url = f"https://img.youtube.com/vi/{video_id}/default.jpg"
    return r


def _write_cache_file(cache_dir: Path, video_id: str, extra: dict | None = None) -> Path:
    """Write a fake _processed.json cache file."""
    data = {
        "video_id": video_id,
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "metadata": {
            "title": "Cached Test Video",
            "channel_title": "Test Channel",
            "duration": "05:30",
        },
        "transcript": {"has_transcript": True},
        "ai_analysis": {"success": True},
        "cost_breakdown": {"total_cost": 0.02},
        "timestamp": "2026-01-01T00:00:00Z",
    }
    if extra:
        data.update(extra)
    cache_file = cache_dir / f"{video_id}_processed.json"
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    return cache_file


@pytest.fixture()
def tmp_cache(tmp_path):
    """A temporary directory used as processor.cache_dir."""
    return tmp_path / "cache"


@pytest.fixture()
def mock_processor(tmp_cache):
    """Pre-configured processor mock with cache_dir wired to tmp_cache."""
    tmp_cache.mkdir(parents=True, exist_ok=True)
    proc = MagicMock()
    proc.cache_dir = tmp_cache
    proc.process_video = AsyncMock(
        return_value={
            "video_id": "auJzb1D-fag",
            "success": True,
            "metadata": {"title": "Test Video"},
            "transcript": {"has_transcript": True},
            "ai_analysis": {"success": True},
            "cost_breakdown": {"total_cost": 0.01},
            "cached": False,
            "error": None,
        }
    )
    proc.batch_process_videos = AsyncMock(return_value={"results": [], "total": 0})
    proc.get_processing_status = AsyncMock(return_value={"service_status": "operational"})
    # _get_cache_path returns a non-existent path by default
    proc._get_cache_path.return_value = tmp_cache / "nonexistent_processed.json"
    return proc


@pytest.fixture()
def mock_youtube():
    yt = MagicMock()
    yt.validate_video_url = AsyncMock(return_value=(True, "auJzb1D-fag", "Valid URL"))
    yt.search_videos = AsyncMock(return_value=[_make_search_result()])
    return yt


@pytest.fixture()
def mock_cost_monitor():
    cm = MagicMock()
    cm.get_cost_dashboard = AsyncMock(
        return_value={
            "today_summary": {"total_cost": 0.5, "budget_remaining": 9.5},
        }
    )
    cm.get_usage_analytics = AsyncMock(return_value={"days": 7, "usage": []})
    cm.optimize_api_usage = AsyncMock(return_value={"recommendations": []})
    return cm


@pytest.fixture()
def api_app(mock_processor, mock_youtube, mock_cost_monitor):
    """A minimal FastAPI app with real_api_endpoints wired up, all services mocked."""
    mini = FastAPI()

    with (
        patch(
            "youtube_extension.backend.real_api_endpoints.get_real_video_processor",
            return_value=mock_processor,
        ),
        patch(
            "youtube_extension.backend.real_api_endpoints.get_youtube_service",
            return_value=mock_youtube,
        ),
        patch(
            "youtube_extension.backend.real_api_endpoints.get_ai_processor",
            return_value=MagicMock(),
        ),
        patch(
            "youtube_extension.backend.real_api_endpoints.cost_monitor",
            mock_cost_monitor,
        ),
    ):
        setup_real_api_endpoints(mini)

    return mini


@pytest.fixture()
def client(api_app, mock_processor, mock_youtube, mock_cost_monitor):
    """TestClient for the api_app fixture."""
    with (
        patch(
            "youtube_extension.backend.real_api_endpoints.get_real_video_processor",
            return_value=mock_processor,
        ),
        patch(
            "youtube_extension.backend.real_api_endpoints.get_youtube_service",
            return_value=mock_youtube,
        ),
        patch(
            "youtube_extension.backend.real_api_endpoints.cost_monitor",
            mock_cost_monitor,
        ),
    ):
        yield TestClient(api_app, raise_server_exceptions=False)


# ===========================================================================
# Pydantic model tests
# ===========================================================================


class TestPydanticModels:
    def test_video_processing_request_defaults(self):
        req = VideoProcessingRequest(video_url="https://youtube.com/watch?v=auJzb1D-fag")
        assert req.force_refresh is False
        assert req.include_related is True
        assert req.ai_analysis is True

    def test_video_processing_request_custom_flags(self):
        req = VideoProcessingRequest(
            video_url="https://youtube.com/watch?v=auJzb1D-fag",
            force_refresh=True,
            include_related=False,
            ai_analysis=False,
        )
        assert req.force_refresh is True
        assert req.include_related is False
        assert req.ai_analysis is False

    def test_video_validation_request_stores_url(self):
        req = VideoValidationRequest(video_url="https://youtube.com/watch?v=auJzb1D-fag")
        assert req.video_url == "https://youtube.com/watch?v=auJzb1D-fag"

    def test_batch_processing_request_defaults(self):
        req = BatchProcessingRequest(video_urls=["url1", "url2"])
        assert req.max_concurrent == 3
        assert req.force_refresh is False

    def test_batch_processing_request_max_concurrent_bounds(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BatchProcessingRequest(video_urls=["u"], max_concurrent=0)  # ge=1
        with pytest.raises(ValidationError):
            BatchProcessingRequest(video_urls=["u"], max_concurrent=11)  # le=10

    def test_video_analysis_response_defaults(self):
        resp = VideoAnalysisResponse(
            video_id="auJzb1D-fag",
            video_url="https://youtube.com/watch?v=auJzb1D-fag",
            success=True,
            processing_time=1.23,
        )
        assert resp.cached is False
        assert resp.error is None
        assert resp.metadata is None

    def test_video_analysis_response_with_all_fields(self):
        resp = VideoAnalysisResponse(
            video_id="auJzb1D-fag",
            video_url="https://youtube.com/watch?v=auJzb1D-fag",
            success=True,
            metadata={"title": "T"},
            transcript={"text": "hello"},
            ai_analysis={"summary": "s"},
            cost_breakdown={"total_cost": 0.01},
            processing_time=2.5,
            cached=True,
            error=None,
        )
        assert resp.cached is True
        assert resp.cost_breakdown == {"total_cost": 0.01}


# ===========================================================================
# init_real_api_services
# ===========================================================================


class TestInitRealApiServices:
    def test_returns_true_when_all_services_ok(self):
        with (
            patch(
                "youtube_extension.backend.real_api_endpoints.get_real_video_processor",
                return_value=MagicMock(),
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.get_youtube_service",
                return_value=MagicMock(),
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.get_ai_processor",
                return_value=MagicMock(),
            ),
        ):
            result = init_real_api_services()
        assert result is True

    def test_returns_false_when_service_raises(self):
        with patch(
            "youtube_extension.backend.real_api_endpoints.get_real_video_processor",
            side_effect=RuntimeError("init fail"),
        ):
            result = init_real_api_services()
        assert result is False


# ===========================================================================
# POST /api/v2/process-video
# ===========================================================================


class TestProcessVideoEndpoint:
    def test_returns_200_on_success(self, client):
        response = client.post(
            "/api/v2/process-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        assert response.status_code == 200

    def test_response_contains_video_id(self, client):
        response = client.post(
            "/api/v2/process-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        data = response.json()
        assert data["video_id"] == "auJzb1D-fag"

    def test_response_contains_success_flag(self, client):
        response = client.post(
            "/api/v2/process-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        assert response.json()["success"] is True

    def test_response_contains_processing_time(self, client):
        response = client.post(
            "/api/v2/process-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        data = response.json()
        assert "processing_time" in data
        assert data["processing_time"] >= 0

    def test_force_refresh_passed_to_processor(self, client, mock_processor):
        client.post(
            "/api/v2/process-video",
            json={
                "video_url": "https://youtube.com/watch?v=auJzb1D-fag",
                "force_refresh": True,
            },
        )
        _, kwargs = mock_processor.process_video.call_args
        assert kwargs.get("force_refresh") is True

    def test_returns_500_when_processor_raises(self, client, mock_processor):
        mock_processor.process_video = AsyncMock(side_effect=RuntimeError("processing failed"))
        response = client.post(
            "/api/v2/process-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        assert response.status_code == 500

    def test_error_response_does_not_leak_internal_state(self, client, mock_processor):
        mock_processor.process_video = AsyncMock(side_effect=RuntimeError("crash"))
        response = client.post(
            "/api/v2/process-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        assert response.status_code == 500
        # 500 responses must not disclose internal state (CWE-209):
        # neither the request-supplied video_url nor the exception text.
        detail = response.json()["detail"]
        assert detail == "Internal server error"
        assert "auJzb1D-fag" not in str(detail)
        assert "crash" not in str(detail)

    def test_missing_video_url_returns_422(self, client):
        response = client.post("/api/v2/process-video", json={})
        assert response.status_code == 422


# ===========================================================================
# POST /api/v2/validate-video
# ===========================================================================


class TestValidateVideoEndpoint:
    def test_valid_url_returns_200(self, client):
        response = client.post(
            "/api/v2/validate-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        assert response.status_code == 200

    def test_valid_url_response_contains_valid_true(self, client):
        response = client.post(
            "/api/v2/validate-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        data = response.json()
        assert data["valid"] is True

    def test_response_contains_video_id(self, client):
        response = client.post(
            "/api/v2/validate-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        assert response.json()["video_id"] == "auJzb1D-fag"

    def test_response_contains_timestamp(self, client):
        response = client.post(
            "/api/v2/validate-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        assert "timestamp" in response.json()

    def test_invalid_url_returns_valid_false(self, client, mock_youtube):
        mock_youtube.validate_video_url = AsyncMock(
            return_value=(False, None, "Invalid YouTube URL")
        )
        response = client.post(
            "/api/v2/validate-video",
            json={"video_url": "https://notvalid.example.com"},
        )
        data = response.json()
        assert data["valid"] is False

    def test_service_error_returns_500(self, client, mock_youtube):
        mock_youtube.validate_video_url = AsyncMock(side_effect=RuntimeError("YT API down"))
        response = client.post(
            "/api/v2/validate-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        assert response.status_code == 500

    def test_missing_url_returns_422(self, client):
        response = client.post("/api/v2/validate-video", json={})
        assert response.status_code == 422


# ===========================================================================
# POST /api/v2/batch-process
# ===========================================================================


class TestBatchProcessEndpoint:
    def test_valid_batch_returns_200(self, client):
        response = client.post(
            "/api/v2/batch-process",
            json={
                "video_urls": [
                    "https://youtube.com/watch?v=auJzb1D-fag",
                    "https://youtube.com/watch?v=abc123def45",
                ],
                "max_concurrent": 2,
            },
        )
        assert response.status_code == 200

    def test_batch_with_more_than_20_videos_returns_400(self, client):
        """A >20-video batch must surface the explicit 400 validation error and
        not be swallowed into a generic 500 by the broad exception handler
        (the handler re-raises HTTPException before the catch-all)."""
        urls = [f"https://youtube.com/watch?v=vid{i:05d}" for i in range(21)]
        response = client.post(
            "/api/v2/batch-process",
            json={"video_urls": urls, "max_concurrent": 3},
        )
        assert response.status_code == 400
        assert "Maximum 20 videos" in response.json()["detail"]

    def test_batch_response_contains_results(self, client):
        response = client.post(
            "/api/v2/batch-process",
            json={"video_urls": ["https://youtube.com/watch?v=auJzb1D-fag"]},
        )
        assert "results" in response.json()

    def test_batch_processor_error_returns_500(self, client, mock_processor):
        mock_processor.batch_process_videos = AsyncMock(side_effect=RuntimeError("batch fail"))
        response = client.post(
            "/api/v2/batch-process",
            json={"video_urls": ["https://youtube.com/watch?v=auJzb1D-fag"]},
        )
        assert response.status_code == 500

    def test_batch_max_concurrent_bounds_enforced_by_model(self, client):
        """max_concurrent=0 fails Pydantic validation (ge=1)."""
        response = client.post(
            "/api/v2/batch-process",
            json={"video_urls": ["u1"], "max_concurrent": 0},
        )
        assert response.status_code == 422


# ===========================================================================
# GET /api/v2/videos/list
# ===========================================================================


class TestGetProcessedVideosListEndpoint:
    def test_empty_cache_returns_empty_list(self, client, mock_processor, tmp_cache):
        # cache_dir exists but is empty
        tmp_cache.mkdir(parents=True, exist_ok=True)
        response = client.get("/api/v2/videos/list")
        assert response.status_code == 200
        assert response.json() == []

    def test_cached_videos_returned(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "auJzb1D-fag")
        response = client.get("/api/v2/videos/list")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "auJzb1D-fag"

    def test_returned_video_has_expected_fields(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "auJzb1D-fag")
        response = client.get("/api/v2/videos/list")
        video = response.json()[0]
        for field in ("id", "title", "channel", "processed_at", "total_cost"):
            assert field in video, f"Missing field: {field}"

    def test_multiple_cached_videos_returned(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "auJzb1D-fag")
        _write_cache_file(tmp_cache, "abc123def45")
        response = client.get("/api/v2/videos/list")
        assert len(response.json()) == 2

    def test_nonexistent_cache_dir_returns_empty_list(self, client, mock_processor, tmp_cache):
        # Point cache_dir to a path that does NOT exist
        mock_processor.cache_dir = tmp_cache / "does_not_exist"
        response = client.get("/api/v2/videos/list")
        assert response.status_code == 200
        assert response.json() == []

    def test_corrupted_json_file_skipped(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        bad_file = tmp_cache / "bad_processed.json"
        bad_file.write_text("{invalid json", encoding="utf-8")
        response = client.get("/api/v2/videos/list")
        assert response.status_code == 200
        # Bad file is silently skipped
        assert response.json() == []

    def test_videos_sorted_by_timestamp_descending(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "vid_a", {"timestamp": "2026-01-01T00:00:00Z"})
        _write_cache_file(tmp_cache, "vid_b", {"timestamp": "2026-06-01T00:00:00Z"})
        response = client.get("/api/v2/videos/list")
        data = response.json()
        assert data[0]["id"] == "vid_b"  # newer first


# ===========================================================================
# GET /api/v2/videos/{video_id}
# ===========================================================================


class TestGetVideoAnalysisEndpoint:
    def test_existing_video_returns_200(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = _write_cache_file(tmp_cache, "auJzb1D-fag")
        mock_processor._get_cache_path.return_value = cache_file
        response = client.get("/api/v2/videos/auJzb1D-fag")
        assert response.status_code == 200

    def test_existing_video_returns_correct_data(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = _write_cache_file(tmp_cache, "auJzb1D-fag")
        mock_processor._get_cache_path.return_value = cache_file
        response = client.get("/api/v2/videos/auJzb1D-fag")
        data = response.json()
        assert data["video_id"] == "auJzb1D-fag"

    def test_missing_video_returns_404(self, client, mock_processor, tmp_cache):
        mock_processor._get_cache_path.return_value = tmp_cache / "nonexistent_processed.json"
        response = client.get("/api/v2/videos/nonexistent")
        assert response.status_code == 404

    def test_404_detail_contains_video_id(self, client, mock_processor, tmp_cache):
        mock_processor._get_cache_path.return_value = tmp_cache / "nonexistent_processed.json"
        response = client.get("/api/v2/videos/nonexistent")
        assert "nonexistent" in response.json()["detail"]

    def test_processor_error_returns_500(self, client, mock_processor):
        mock_processor._get_cache_path.side_effect = RuntimeError("disk error")
        response = client.get("/api/v2/videos/auJzb1D-fag")
        assert response.status_code == 500


# ===========================================================================
# GET /api/v2/cost-dashboard
# ===========================================================================


class TestCostDashboardEndpoint:
    def test_returns_200(self, client):
        response = client.get("/api/v2/cost-dashboard")
        assert response.status_code == 200

    def test_returns_dashboard_data(self, client):
        response = client.get("/api/v2/cost-dashboard")
        data = response.json()
        assert "today_summary" in data

    def test_error_returns_fallback_dict(self, client, mock_cost_monitor):
        mock_cost_monitor.get_cost_dashboard = AsyncMock(side_effect=RuntimeError("db down"))
        response = client.get("/api/v2/cost-dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


# ===========================================================================
# GET /api/v2/usage-analytics
# ===========================================================================


class TestUsageAnalyticsEndpoint:
    def test_default_7_days_returns_200(self, client):
        response = client.get("/api/v2/usage-analytics")
        assert response.status_code == 200

    def test_valid_days_returns_analytics(self, client):
        response = client.get("/api/v2/usage-analytics?days=30")
        assert response.status_code == 200

    def test_days_zero_returns_400(self, client):
        response = client.get("/api/v2/usage-analytics?days=0")
        assert response.status_code == 400

    def test_days_91_returns_400(self, client):
        response = client.get("/api/v2/usage-analytics?days=91")
        assert response.status_code == 400

    def test_days_1_returns_200(self, client):
        response = client.get("/api/v2/usage-analytics?days=1")
        assert response.status_code == 200

    def test_days_90_returns_200(self, client):
        response = client.get("/api/v2/usage-analytics?days=90")
        assert response.status_code == 200

    def test_service_error_returns_fallback_dict(self, client, mock_cost_monitor):
        mock_cost_monitor.get_usage_analytics = AsyncMock(side_effect=RuntimeError("fail"))
        response = client.get("/api/v2/usage-analytics?days=7")
        assert response.status_code == 200
        assert "error" in response.json()


# ===========================================================================
# GET /api/v2/optimization-recommendations
# ===========================================================================


class TestOptimizationRecommendationsEndpoint:
    def test_returns_200(self, client):
        response = client.get("/api/v2/optimization-recommendations")
        assert response.status_code == 200

    def test_returns_recommendations_key(self, client, mock_cost_monitor):
        mock_cost_monitor.optimize_api_usage = AsyncMock(
            return_value={"recommendations": ["use caching"]}
        )
        response = client.get("/api/v2/optimization-recommendations")
        assert "recommendations" in response.json()

    def test_service_error_returns_fallback(self, client, mock_cost_monitor):
        mock_cost_monitor.optimize_api_usage = AsyncMock(side_effect=RuntimeError("crash"))
        response = client.get("/api/v2/optimization-recommendations")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data or "recommendations" in data


# ===========================================================================
# GET /api/v2/service-status
# ===========================================================================


class TestServiceStatusEndpoint:
    def test_operational_processor_returns_operational(self, client):
        response = client.get("/api/v2/service-status")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "operational"

    def test_degraded_processor_returns_degraded(self, client, mock_processor):
        mock_processor.get_processing_status = AsyncMock(
            return_value={"service_status": "degraded"}
        )
        response = client.get("/api/v2/service-status")
        data = response.json()
        assert data["overall_status"] == "degraded"

    def test_response_contains_api_keys_status(self, client):
        response = client.get("/api/v2/service-status")
        data = response.json()
        assert "api_keys" in data

    def test_response_contains_features(self, client):
        response = client.get("/api/v2/service-status")
        data = response.json()
        assert "features" in data
        assert data["features"]["real_youtube_api"] is True

    def test_response_contains_timestamp(self, client):
        response = client.get("/api/v2/service-status")
        assert "timestamp" in response.json()

    def test_response_contains_version(self, client):
        response = client.get("/api/v2/service-status")
        assert "version" in response.json()

    def test_service_error_returns_error_status(self, client, mock_processor):
        mock_processor.get_processing_status = AsyncMock(side_effect=RuntimeError("status fail"))
        response = client.get("/api/v2/service-status")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "error"

    def test_api_key_present_when_env_set(self, client):
        with patch.dict("os.environ", {"YOUTUBE_API_KEY": "yt-key-xyz"}):
            response = client.get("/api/v2/service-status")
        data = response.json()
        assert data["api_keys"]["youtube_api"] is True

    def test_api_key_absent_when_env_not_set(self, client):
        import os

        env_without_keys = {
            k: v
            for k, v in os.environ.items()
            if k not in ("YOUTUBE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")
        }
        with patch.dict("os.environ", env_without_keys, clear=True):
            response = client.get("/api/v2/service-status")
        data = response.json()
        assert data["api_keys"]["youtube_api"] is False


# ===========================================================================
# DELETE /api/v2/cache/clear
# ===========================================================================


class TestClearCacheEndpoint:
    def test_existing_cache_cleared_returns_200(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "auJzb1D-fag")
        response = client.delete("/api/v2/cache/clear")
        assert response.status_code == 200

    def test_clear_cache_response_success_true(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        response = client.delete("/api/v2/cache/clear")
        assert response.json()["success"] is True

    def test_clear_cache_response_contains_message(self, client, mock_processor, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        response = client.delete("/api/v2/cache/clear")
        assert "message" in response.json()

    def test_nonexistent_cache_still_returns_success(self, client, mock_processor, tmp_cache):
        # cache_dir doesn't exist -> shutil.rmtree won't be called
        mock_processor.cache_dir = tmp_cache / "no_such_dir"
        response = client.delete("/api/v2/cache/clear")
        assert response.status_code == 200

    def test_clear_cache_error_returns_500(self, client, mock_processor, tmp_cache):
        # Make cache_dir.exists() raise an error
        bad_path = MagicMock()
        bad_path.exists.side_effect = OSError("permission denied")
        mock_processor.cache_dir = bad_path
        response = client.delete("/api/v2/cache/clear")
        assert response.status_code == 500


# ===========================================================================
# POST /api/v2/search-videos
# ===========================================================================


class TestSearchVideosEndpoint:
    def test_valid_search_returns_200(self, client):
        response = client.post("/api/v2/search-videos?query=python+tutorial&max_results=5")
        assert response.status_code == 200

    def test_response_contains_query(self, client):
        response = client.post("/api/v2/search-videos?query=python")
        data = response.json()
        assert data["query"] == "python"

    def test_response_contains_results_list(self, client):
        response = client.post("/api/v2/search-videos?query=python")
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_response_contains_total_results(self, client):
        response = client.post("/api/v2/search-videos?query=python")
        data = response.json()
        assert "total_results" in data
        assert data["total_results"] == 1  # one mock result

    def test_result_contains_expected_fields(self, client):
        response = client.post("/api/v2/search-videos?query=python")
        result = response.json()["results"][0]
        for field in ("video_id", "title", "description", "channel_title", "video_url"):
            assert field in result, f"Missing field: {field}"

    def test_result_video_url_format(self, client):
        response = client.post("/api/v2/search-videos?query=python")
        result = response.json()["results"][0]
        assert "youtube.com/watch?v=" in result["video_url"]

    def test_max_results_above_50_returns_400(self, client):
        """A >50-result search must surface the explicit 400 validation error and
        not be swallowed into a generic 500 by the broad exception handler
        (the handler re-raises HTTPException before the catch-all)."""
        response = client.post("/api/v2/search-videos?query=python&max_results=51")
        assert response.status_code == 400
        assert "Maximum 50 results" in response.json()["detail"]

    def test_default_order_is_relevance(self, client, mock_youtube):
        client.post("/api/v2/search-videos?query=test")
        _, kwargs = mock_youtube.search_videos.call_args
        assert kwargs.get("order") == "relevance"

    def test_custom_order_passed_to_service(self, client, mock_youtube):
        client.post("/api/v2/search-videos?query=test&order=date")
        _, kwargs = mock_youtube.search_videos.call_args
        assert kwargs.get("order") == "date"

    def test_youtube_service_error_returns_500(self, client, mock_youtube):
        mock_youtube.search_videos = AsyncMock(side_effect=RuntimeError("YT down"))
        response = client.post("/api/v2/search-videos?query=test")
        assert response.status_code == 500

    def test_response_contains_timestamp(self, client):
        response = client.post("/api/v2/search-videos?query=python")
        assert "timestamp" in response.json()

    def test_empty_results_returns_empty_list(self, client, mock_youtube):
        mock_youtube.search_videos = AsyncMock(return_value=[])
        response = client.post("/api/v2/search-videos?query=unusual+query")
        assert response.json()["total_results"] == 0
        assert response.json()["results"] == []


# ===========================================================================
# GET /api/v2/videos/list - blocking I/O offload (performance regression)
# ===========================================================================


class _ThreadRecordingPath:
    """Path-like proxy that records the thread performing the per-file read.

    ``open()`` resolves a non-``str`` argument through ``__fspath__``, so this
    captures the calling thread at the exact moment the blocking read starts —
    rather than inferring it from the enclosing directory scan.
    """

    def __init__(self, real_path: Path, read_thread_ids: list[int]) -> None:
        self._real = real_path
        self._read_thread_ids = read_thread_ids

    def __fspath__(self) -> str:
        self._read_thread_ids.append(threading.get_ident())
        return str(self._real)

    def __str__(self) -> str:
        return str(self._real)


class _ThreadRecordingCacheDir:
    """Stand-in for ``processor.cache_dir`` that records the scanning thread.

    Delegates to a real :class:`~pathlib.Path` so the endpoint keeps its normal
    behaviour, while capturing which thread performed each blocking filesystem
    operation — both the directory-level ``exists()``/``glob()`` and the
    per-entry ``open()``.
    """

    def __init__(self, real_dir: Path) -> None:
        self._real = real_dir
        self.scan_thread_ids: list[int] = []
        self.read_thread_ids: list[int] = []

    def exists(self) -> bool:
        self.scan_thread_ids.append(threading.get_ident())
        return self._real.exists()

    def glob(self, pattern: str):
        self.scan_thread_ids.append(threading.get_ident())
        return [
            _ThreadRecordingPath(p, self.read_thread_ids)
            for p in self._real.glob(pattern)
        ]


class TestVideosListOffloadsBlockingIO:
    """The cache scan must not run on the event loop thread."""

    def test_cache_scan_runs_off_the_event_loop_thread(
        self, api_app, mock_processor, mock_youtube, mock_cost_monitor, tmp_cache
    ):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "auJzb1D-fag")

        recording_dir = _ThreadRecordingCacheDir(tmp_cache)
        mock_processor.cache_dir = recording_dir

        # get_real_video_processor() is invoked by the handler *on the event
        # loop thread*, immediately before the scan is dispatched. Recording it
        # here gives us the loop's thread id without assuming the test itself
        # runs on that loop.
        loop_thread_ids: list[int] = []

        def _record_loop_thread():
            loop_thread_ids.append(threading.get_ident())
            return mock_processor

        with (
            patch(
                "youtube_extension.backend.real_api_endpoints.get_real_video_processor",
                side_effect=_record_loop_thread,
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.get_youtube_service",
                return_value=mock_youtube,
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.cost_monitor",
                mock_cost_monitor,
            ),
        ):
            with TestClient(api_app, raise_server_exceptions=False) as c:
                response = c.get("/api/v2/videos/list")

        assert response.status_code == 200
        assert len(response.json()) == 1

        assert loop_thread_ids, "handler never resolved the processor"
        assert recording_dir.scan_thread_ids, "cache directory was never scanned"

        loop_thread_id = loop_thread_ids[0]
        assert all(tid != loop_thread_id for tid in recording_dir.scan_thread_ids), (
            "blocking cache scan ran on the event loop thread "
            f"({loop_thread_id}); observed {recording_dir.scan_thread_ids}"
        )

        # The directory scan and the per-entry read are separate blocking
        # operations; assert the reads moved off-loop too rather than inferring
        # it from the helper extraction.
        assert recording_dir.read_thread_ids, "no cache entry was ever read"
        assert all(tid != loop_thread_id for tid in recording_dir.read_thread_ids), (
            "blocking cache entry read ran on the event loop thread "
            f"({loop_thread_id}); observed {recording_dir.read_thread_ids}"
        )

    async def test_event_loop_stays_responsive_during_cache_scan(
        self, api_app, mock_processor, mock_youtube, mock_cost_monitor, tmp_cache
    ):
        """A slow scan must not starve other tasks on the loop."""
        tmp_cache.mkdir(parents=True, exist_ok=True)

        scan_duration = 0.30

        class _SlowCacheDir:
            def exists(self) -> bool:
                return True

            def glob(self, pattern: str):
                time.sleep(scan_duration)
                return []

        mock_processor.cache_dir = _SlowCacheDir()

        heartbeats = 0

        async def _heartbeat():
            nonlocal heartbeats
            while True:
                await asyncio.sleep(0.01)
                heartbeats += 1

        with (
            patch(
                "youtube_extension.backend.real_api_endpoints.get_real_video_processor",
                return_value=mock_processor,
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.get_youtube_service",
                return_value=mock_youtube,
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.cost_monitor",
                mock_cost_monitor,
            ),
        ):
            transport = httpx.ASGITransport(app=api_app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as ac:
                ticker = asyncio.create_task(_heartbeat())
                try:
                    response = await ac.get("/api/v2/videos/list")
                finally:
                    ticker.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await ticker

        assert response.status_code == 200
        # A responsive loop ticks ~30x during a 0.30s scan. Assert a very
        # conservative fraction of that to stay robust on loaded CI runners,
        # while still failing outright when the loop is fully blocked.
        assert (
            heartbeats >= 5
        ), f"event loop was starved during the cache scan (ticks={heartbeats})"

    def test_offloaded_scan_returns_same_payload(
        self, client, mock_processor, tmp_cache
    ):
        """Offloading must not change the response contract."""
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "auJzb1D-fag")

        response = client.get("/api/v2/videos/list")

        assert response.status_code == 200
        payload = response.json()
        assert payload == _collect_processed_videos_sync(tmp_cache)


class TestCollectProcessedVideosSync:
    """Direct coverage of the extracted blocking helper."""

    def test_missing_directory_returns_empty_list(self, tmp_path):
        assert _collect_processed_videos_sync(tmp_path / "absent") == []

    def test_empty_directory_returns_empty_list(self, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        assert _collect_processed_videos_sync(tmp_cache) == []

    def test_corrupt_entry_is_skipped_without_failing_the_scan(self, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        (tmp_cache / "bad_processed.json").write_text("{invalid json", encoding="utf-8")
        _write_cache_file(tmp_cache, "auJzb1D-fag")

        result = _collect_processed_videos_sync(tmp_cache)

        assert [v["id"] for v in result] == ["auJzb1D-fag"]

    def test_results_are_sorted_by_timestamp_descending(self, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "vid_a", {"timestamp": "2026-01-01T00:00:00Z"})
        _write_cache_file(tmp_cache, "vid_b", {"timestamp": "2026-06-01T00:00:00Z"})

        result = _collect_processed_videos_sync(tmp_cache)

        assert [v["id"] for v in result] == ["vid_b", "vid_a"]

    def test_non_matching_files_are_ignored(self, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        (tmp_cache / "notes.txt").write_text("ignore me", encoding="utf-8")
        (tmp_cache / "other.json").write_text("{}", encoding="utf-8")

        assert _collect_processed_videos_sync(tmp_cache) == []


# ===========================================================================
# GET /api/v2/videos/{video_id} - blocking I/O offload (performance regression)
# ===========================================================================


class _SlowReadPath:
    """Path-like proxy whose resolution blocks, standing in for a large read.

    ``open()`` resolves a non-``str`` argument through ``__fspath__``, so the
    sleep lands inside the blocking read itself rather than around it. If the
    read is dispatched to a worker thread the loop stays free for that whole
    window; if it is not, the loop is pinned for exactly this long.
    """

    def __init__(self, real_path: Path, duration: float) -> None:
        self._real = real_path
        self._duration = duration

    def __fspath__(self) -> str:
        time.sleep(self._duration)
        return str(self._real)

    def __str__(self) -> str:
        return str(self._real)


class TestVideoDetailOffloadsBlockingIO:
    """The single-entry cache read must not run on the event loop thread."""

    def test_cache_entry_read_runs_off_the_event_loop_thread(
        self, api_app, mock_processor, mock_youtube, mock_cost_monitor, tmp_cache
    ):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = _write_cache_file(tmp_cache, "auJzb1D-fag")

        read_thread_ids: list[int] = []
        mock_processor._get_cache_path.return_value = _ThreadRecordingPath(
            cache_file, read_thread_ids
        )

        # get_real_video_processor() is invoked by the handler *on the event
        # loop thread*, immediately before the read is dispatched. Recording it
        # here gives us the loop's thread id without assuming the test itself
        # runs on that loop.
        loop_thread_ids: list[int] = []

        def _record_loop_thread():
            loop_thread_ids.append(threading.get_ident())
            return mock_processor

        with (
            patch(
                "youtube_extension.backend.real_api_endpoints.get_real_video_processor",
                side_effect=_record_loop_thread,
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.get_youtube_service",
                return_value=mock_youtube,
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.cost_monitor",
                mock_cost_monitor,
            ),
        ):
            with TestClient(api_app, raise_server_exceptions=False) as c:
                response = c.get("/api/v2/videos/auJzb1D-fag")

        assert response.status_code == 200
        assert response.json()["video_id"] == "auJzb1D-fag"

        assert loop_thread_ids, "handler never resolved the processor"
        assert read_thread_ids, "cache entry was never read"

        loop_thread_id = loop_thread_ids[0]
        assert all(tid != loop_thread_id for tid in read_thread_ids), (
            "blocking cache entry read ran on the event loop thread "
            f"({loop_thread_id}); observed {read_thread_ids}"
        )

    async def test_event_loop_stays_responsive_during_cache_read(
        self, api_app, mock_processor, mock_youtube, mock_cost_monitor, tmp_cache
    ):
        """A slow read must not starve other tasks on the loop.

        Scope note: ``_SlowReadPath`` sleeps in ``__fspath__``, which models
        *filesystem* latency -- and ``time.sleep`` releases the GIL, exactly as
        a real blocking syscall does. It is not vacuous: reverting the
        ``asyncio.to_thread`` hop drives ``heartbeats`` to 0. Since the helper
        stopped parsing the payload, filesystem latency is essentially the
        whole read; the size-proportional stall that used to remain is pinned
        by ``test_read_stall_no_longer_scales_with_payload``.
        """
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = _write_cache_file(tmp_cache, "auJzb1D-fag")

        read_duration = 0.30
        mock_processor._get_cache_path.return_value = _SlowReadPath(
            cache_file, read_duration
        )

        heartbeats = 0

        async def _heartbeat():
            nonlocal heartbeats
            while True:
                await asyncio.sleep(0.01)
                heartbeats += 1

        with (
            patch(
                "youtube_extension.backend.real_api_endpoints.get_real_video_processor",
                return_value=mock_processor,
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.get_youtube_service",
                return_value=mock_youtube,
            ),
            patch(
                "youtube_extension.backend.real_api_endpoints.cost_monitor",
                mock_cost_monitor,
            ),
        ):
            transport = httpx.ASGITransport(app=api_app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as ac:
                ticker = asyncio.create_task(_heartbeat())
                try:
                    response = await ac.get("/api/v2/videos/auJzb1D-fag")
                finally:
                    ticker.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await ticker

        assert response.status_code == 200
        # A responsive loop ticks ~30x during a 0.30s read. Assert a very
        # conservative fraction of that to stay robust on loaded CI runners,
        # while still failing outright when the loop is fully blocked.
        assert (
            heartbeats >= 5
        ), f"event loop was starved during the cache read (ticks={heartbeats})"

    async def test_read_stall_no_longer_scales_with_payload(self, tmp_path):
        """The read must not stall the loop in proportion to payload size.

        Successor to ``test_parse_still_stalls_the_loop_in_proportion_to_
        payload``, which characterised the residual left by the ``to_thread``
        offload: ``json.load()`` held the GIL in the worker, so the loop still
        stalled ~3 ms/MB of payload. The helper no longer parses entries above
        the validation threshold -- it returns raw bytes, and ``read()``
        releases the GIL -- so that proportional stall must be gone.

        Self-calibrating rather than absolute-time based: the baseline is the
        same payload pushed through ``json.loads`` on a worker thread, which
        is exactly the old behaviour. The helper's read must stall the loop
        for a small fraction of what the parse does, whatever the runner's
        speed. If this fails, size-proportional GIL-held work has crept back
        into the read path and the documented bounded-stall guarantee in
        ``_read_video_analysis_sync`` no longer holds.
        """
        payload = json.dumps({"transcript": [{"t": i} for i in range(400_000)]})
        large = tmp_path / "large.json"
        large.write_text(payload)
        # The point of the threshold is that entries above it skip the
        # validation parse; the fixture must actually exercise that path.
        assert large.stat().st_size > _VALIDATION_MAX_BYTES

        async def _max_loop_gap(work, arg):
            gaps: list[float] = []
            stop = asyncio.Event()

            async def _ticker():
                last = time.perf_counter()
                while not stop.is_set():
                    await asyncio.sleep(0)
                    now = time.perf_counter()
                    gaps.append(now - last)
                    last = now

            task = asyncio.create_task(_ticker())
            await asyncio.sleep(0.02)
            gaps.clear()
            await asyncio.to_thread(work, arg)
            stop.set()
            await task
            return max(gaps)

        parse_gap = await _max_loop_gap(json.loads, payload)
        # Take the best of a few runs for the read: a single scheduling hiccup
        # on a loaded CI runner must not masquerade as a proportional stall.
        read_gap = min(
            [await _max_loop_gap(_read_video_analysis_sync, large) for _ in range(3)]
        )

        assert read_gap < parse_gap / 4, (
            "expected the raw-bytes read to stall the loop far less than "
            "parsing the same payload "
            f"(read={read_gap * 1000:.2f}ms, parse={parse_gap * 1000:.2f}ms); "
            "size-proportional GIL-held work appears to be back on the read "
            "path -- re-narrow the guarantee documented in "
            "_read_video_analysis_sync if that is intentional"
        )

    def test_offloaded_read_returns_same_payload(
        self, client, mock_processor, tmp_cache
    ):
        """Offloading must not change the response contract.

        Stronger than semantic equality: the raw-passthrough response body is
        the cache entry byte-for-byte, and it still declares itself as JSON.
        """
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = _write_cache_file(tmp_cache, "auJzb1D-fag")
        mock_processor._get_cache_path.return_value = cache_file

        response = client.get("/api/v2/videos/auJzb1D-fag")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert response.content == cache_file.read_bytes()
        assert response.json() == json.loads(cache_file.read_text(encoding="utf-8"))


class TestReadVideoAnalysisSync:
    """Direct coverage of the extracted blocking helper."""

    def test_missing_file_returns_the_miss_sentinel(self, tmp_path):
        assert (
            _read_video_analysis_sync(tmp_path / "absent_processed.json") is _CACHE_MISS
        )

    def test_existing_file_returns_raw_bytes_verbatim(self, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = _write_cache_file(tmp_cache, "auJzb1D-fag")

        result = _read_video_analysis_sync(cache_file)

        assert isinstance(result, bytes)
        assert result == cache_file.read_bytes()
        assert json.loads(result)["video_id"] == "auJzb1D-fag"

    def test_null_content_is_a_payload_not_a_miss(self, tmp_cache):
        """A stored JSON ``null`` is a payload, *not* a cache miss.

        It comes back as the raw bytes ``b"null"`` and must be served as a
        200. The sentinel keeps absence distinguishable from any content --
        including the parsed-``None`` form the helper used to return.
        """
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = tmp_cache / "nullish_processed.json"
        cache_file.write_text("null", encoding="utf-8")

        result = _read_video_analysis_sync(cache_file)

        assert result == b"null"
        assert result is not _CACHE_MISS

    def test_falsy_payloads_are_not_misses(self, tmp_cache):
        """Neither is any other JSON value that parses to something falsy."""
        tmp_cache.mkdir(parents=True, exist_ok=True)

        for index, raw in enumerate(("{}", "[]", '""', "0", "false")):
            cache_file = tmp_cache / f"falsy{index}_processed.json"
            cache_file.write_text(raw, encoding="utf-8")

            assert _read_video_analysis_sync(cache_file) is not _CACHE_MISS, raw

    def test_embedded_null_byte_in_path_is_a_miss(self, tmp_cache):
        """A path the OS cannot even name is a miss, not a fault.

        ``Path.exists()`` swallows the ``ValueError`` that an embedded null
        byte provokes and reports the entry as absent, so the pre-change
        handler answered 404. A bare ``open()`` lets that ``ValueError``
        escape, which would turn the same request into a 500.
        """
        tmp_cache.mkdir(parents=True, exist_ok=True)
        poisoned = Path(f"{tmp_cache}/\x00_processed.json")

        assert _read_video_analysis_sync(poisoned) is _CACHE_MISS

    def test_corrupt_entry_raises_rather_than_reporting_a_miss(self, tmp_cache):
        """A damaged entry must surface as a 500, never as a 404.

        Only "the path names no readable entry" -- ``FileNotFoundError`` or a
        path the OS rejects outright -- means "no such analysis"; anything
        else is a real fault and has to keep propagating.

        This guarantee is now scoped to entries at or below
        ``_VALIDATION_MAX_BYTES``; validating above the threshold would
        reintroduce the unbounded GIL-held parse the raw-bytes read removed.
        See ``test_oversized_corrupt_entry_is_returned_unvalidated`` for the
        other side of that line.
        """
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = tmp_cache / "bad_processed.json"
        cache_file.write_text("{invalid json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            _read_video_analysis_sync(cache_file)

    def test_corrupt_entry_at_the_threshold_still_raises(self, tmp_cache):
        """The validation boundary is inclusive: exactly-at-cap entries parse."""
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = tmp_cache / "boundary_processed.json"
        blob = b"{invalid json" + b" " * (_VALIDATION_MAX_BYTES - len(b"{invalid json"))
        assert len(blob) == _VALIDATION_MAX_BYTES
        cache_file.write_bytes(blob)

        with pytest.raises(json.JSONDecodeError):
            _read_video_analysis_sync(cache_file)

    def test_oversized_corrupt_entry_is_returned_unvalidated(self, tmp_cache):
        """Entries above the validation threshold are served verbatim.

        Validating them would mean a GIL-held parse proportional to payload
        size -- exactly the unbounded loop stall this helper exists to avoid.
        Integrity above the threshold is delegated to the writer, which
        publishes entries atomically (temp file + ``os.replace``), so a torn
        entry cannot be observed; only out-of-band corruption slips through,
        and it reaches the client as-is rather than as a 500.
        """
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = tmp_cache / "huge_processed.json"
        blob = b"{not json at all" + b"x" * _VALIDATION_MAX_BYTES
        cache_file.write_bytes(blob)

        assert _read_video_analysis_sync(cache_file) == blob

    def test_directory_path_raises_rather_than_reporting_a_miss(self, tmp_cache):
        """Opening a directory is an ``OSError`` but not a missing entry."""
        tmp_cache.mkdir(parents=True, exist_ok=True)
        directory = tmp_cache / "a_directory_processed.json"
        directory.mkdir()

        with pytest.raises(OSError) as excinfo:
            _read_video_analysis_sync(directory)

        assert not isinstance(excinfo.value, FileNotFoundError)


class TestVideoDetailIgnoresProcessorCacheTtl:
    """This endpoint has never expired cached analyses, and still must not.

    ``RealVideoProcessor._read_cache_file`` treats any entry older than
    ``_CACHE_TTL_SECONDS`` (24 hours) as a miss. Reusing it here to avoid a
    second reader would silently turn every analysis over a day old into a 404.
    These tests pin the existing contract so that "simplification" cannot land
    unnoticed.
    """

    @staticmethod
    def _age_file(path: Path, seconds: float) -> None:
        stale = path.stat().st_mtime - seconds
        os.utime(path, (stale, stale))

    def test_helper_returns_entry_older_than_processor_ttl(self, tmp_cache):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = _write_cache_file(tmp_cache, "auJzb1D-fag")
        self._age_file(cache_file, 48 * 60 * 60)

        result = _read_video_analysis_sync(cache_file)

        assert result is not _CACHE_MISS
        assert json.loads(result)["video_id"] == "auJzb1D-fag"

    def test_endpoint_serves_entry_older_than_processor_ttl(
        self, client, mock_processor, tmp_cache
    ):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = _write_cache_file(tmp_cache, "auJzb1D-fag")
        self._age_file(cache_file, 48 * 60 * 60)
        mock_processor._get_cache_path.return_value = cache_file

        response = client.get("/api/v2/videos/auJzb1D-fag")

        assert response.status_code == 200
        assert response.json()["video_id"] == "auJzb1D-fag"


# ===========================================================================
# Cache-miss sentinel: absence vs. a stored ``null``
# ===========================================================================


class TestVideoDetailDistinguishesNullFromMissing:
    """A stored JSON ``null`` is a payload; only absence is a 404.

    The helper runs in a worker thread and hands its result back to the
    handler, so the value it uses to signal "no entry" must be one that
    ``json.load`` can never itself produce. ``None`` fails that test, and
    using it regressed a ``null`` entry from 200 to 404.
    """

    def test_null_content_entry_is_served_as_200(
        self, client, mock_processor, tmp_cache
    ):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        cache_file = tmp_cache / "auJzb1D-fag_processed.json"
        cache_file.write_text("null", encoding="utf-8")
        mock_processor._get_cache_path.return_value = cache_file

        response = client.get("/api/v2/videos/auJzb1D-fag")

        assert response.status_code == 200
        assert response.json() is None

    def test_absent_entry_is_still_a_404(self, client, mock_processor, tmp_cache):
        """The control: the sentinel must not swallow genuine misses."""
        tmp_cache.mkdir(parents=True, exist_ok=True)
        mock_processor._get_cache_path.return_value = (
            tmp_cache / "auJzb1D-fag_processed.json"
        )

        response = client.get("/api/v2/videos/auJzb1D-fag")

        assert response.status_code == 404


# ============================================================================
# Malformed identifiers stay on the 404 path
# ============================================================================


class TestVideoDetailRejectsMalformedIdentifiers:
    """A ``video_id`` the filesystem cannot name is a 404, not a 500.

    Dropping the ``Path.exists()`` probe removed an implicit guard: that call
    catches ``ValueError`` as well as ``OSError``, so an identifier carrying an
    embedded null byte was reported as absent. A bare ``open()`` raises
    instead, which escalated the same request from 404 to 500.
    """

    def test_null_byte_identifier_is_a_404_not_a_500(
        self, client, mock_processor, tmp_cache
    ):
        tmp_cache.mkdir(parents=True, exist_ok=True)
        # Real path-building semantics, mirroring ``_get_cache_path``: a fixed
        # return value would never carry the null byte into the open() call.
        mock_processor._get_cache_path.side_effect = lambda vid: Path(
            f"{tmp_cache}/{vid}_processed.json"
        )

        response = client.get("/api/v2/videos/%00")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_wellformed_identifier_still_reaches_the_payload(
        self, client, mock_processor, tmp_cache
    ):
        """The control: the widened miss rule must not swallow real reads."""
        tmp_cache.mkdir(parents=True, exist_ok=True)
        _write_cache_file(tmp_cache, "auJzb1D-fag")
        mock_processor._get_cache_path.side_effect = lambda vid: Path(
            f"{tmp_cache}/{vid}_processed.json"
        )

        response = client.get("/api/v2/videos/auJzb1D-fag")

        assert response.status_code == 200
        assert response.json()["video_id"] == "auJzb1D-fag"
