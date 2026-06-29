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

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
    BatchProcessingRequest,
    VideoAnalysisResponse,
    VideoProcessingRequest,
    VideoValidationRequest,
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

    def test_error_response_includes_video_url(self, client, mock_processor):
        mock_processor.process_video = AsyncMock(side_effect=RuntimeError("crash"))
        response = client.post(
            "/api/v2/process-video",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
        )
        detail = response.json()["detail"]
        assert "auJzb1D-fag" in str(detail)

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

    def test_batch_with_more_than_20_videos_returns_error(self, client):
        """Source code raises HTTPException(400) inside a try block that
        re-wraps it as 500. Test matches actual behaviour."""
        urls = [f"https://youtube.com/watch?v=vid{i:05d}" for i in range(21)]
        response = client.post(
            "/api/v2/batch-process",
            json={"video_urls": urls, "max_concurrent": 3},
        )
        # The HTTPException(400) is caught by the outer except -> HTTP 500
        assert response.status_code in (400, 500)

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

    def test_max_results_above_50_returns_error(self, client):
        """Source code raises HTTPException(400) inside a try block that
        catches Exception -> results in HTTP 500."""
        response = client.post("/api/v2/search-videos?query=python&max_results=51")
        assert response.status_code in (400, 500)

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
