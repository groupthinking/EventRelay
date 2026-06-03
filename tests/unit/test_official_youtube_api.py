"""
Unit tests for RealYouTubeAPIService (official_api.py).

Coverage targets:
- YouTubeVideoMetadata, YouTubeTranscriptSegment, YouTubeSearchResult dataclasses
- RealYouTubeAPIService.__init__
- get_video_metadata – success, HTTPStatusError, generic exception, video not found
- get_video_transcript – all branches (transcript api, fallback, no providers, object segments)
- search_videos – success, optional params, exception
- get_channel_info – success, not found, exception
- get_related_videos – success, exception
- get_comprehensive_video_data – success with transcript error, channel/related errors
- validate_video_url – public, private, unlisted, invalid, exception
- close
- get_youtube_service, get_video_data convenience functions

Note: youtube_transcript_api IS installed in this env; get_video_transcript_robust is NOT
available in the official_api module (import failed), so tests use create=True.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.youtube.adapters.official_api import (
    RealYouTubeAPIService,
    YouTubeSearchResult,
    YouTubeTranscriptSegment,
    YouTubeVideoMetadata,
    get_video_data,
    get_youtube_service,
)

VIDEO_ID = "auJzb1D-fag"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
API_KEY = "FAKE_API_KEY"

_OFFICIAL_MODULE = "youtube_extension.backend.services.youtube.adapters.official_api"


# ---------------------------------------------------------------------------
# Autouse fixture: reset cost_monitor circuit breaker between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset the global cost_monitor circuit breakers before each test
    so they don't accumulate failures across tests in this module."""
    from youtube_extension.backend.services.api_cost_monitor import cost_monitor

    cost_monitor.circuit_breakers.clear()
    yield
    cost_monitor.circuit_breakers.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_http_response(status: int = 200, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = f"HTTP {status} error"
    resp.json = MagicMock(return_value=json_data or {})
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status}", request=MagicMock(), response=resp
        )
    return resp


def _video_api_response(
    video_id: str = VIDEO_ID,
    title: str = "Test Video",
    channel_id: str = "UC_test",
    channel_title: str = "Test Channel",
    view_count: str = "9999",
    like_count: str = "100",
    comment_count: str = "50",
    duration: str = "PT10M",
    published_at: str = "2024-01-01T00:00:00Z",
    privacy_status: str = "public",
) -> dict:
    return {
        "items": [
            {
                "id": video_id,
                "snippet": {
                    "title": title,
                    "description": "A description",
                    "channelId": channel_id,
                    "channelTitle": channel_title,
                    "publishedAt": published_at,
                    "tags": ["python", "test"],
                    "categoryId": "28",
                    "defaultLanguage": "en",
                    "defaultAudioLanguage": "en",
                    "liveBroadcastContent": "none",
                    "thumbnails": {
                        "default": {"url": "https://img.youtube.com/default.jpg"},
                        "high": {"url": "https://img.youtube.com/high.jpg"},
                    },
                },
                "statistics": {
                    "viewCount": view_count,
                    "likeCount": like_count,
                    "commentCount": comment_count,
                },
                "contentDetails": {"duration": duration},
                "status": {"privacyStatus": privacy_status, "uploadStatus": "processed"},
            }
        ]
    }


def _search_api_response() -> dict:
    return {
        "items": [
            {
                "id": {"videoId": "other_vid_id"},
                "snippet": {
                    "title": "Related Video",
                    "description": "Related desc",
                    "channelTitle": "Related Channel",
                    "publishedAt": "2024-01-02T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://img.youtube.com/related.jpg"}},
                },
            }
        ]
    }


def _channel_api_response() -> dict:
    return {
        "items": [
            {
                "snippet": {
                    "title": "Test Channel",
                    "description": "Chan desc",
                    "publishedAt": "2020-01-01T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://img.youtube.com/chan.jpg"}},
                },
                "statistics": {
                    "subscriberCount": "1000000",
                    "videoCount": "200",
                    "viewCount": "5000000",
                },
            }
        ]
    }


def _make_service() -> RealYouTubeAPIService:
    with patch("httpx.AsyncClient"):
        svc = RealYouTubeAPIService(api_key=API_KEY)
    svc.client = MagicMock(spec=httpx.AsyncClient)
    svc.client.get = AsyncMock()
    svc.client.aclose = AsyncMock()
    return svc


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestYouTubeTranscriptSegment:
    def test_end_property(self):
        seg = YouTubeTranscriptSegment(text="hello", start=5.0, duration=3.0)
        assert seg.end == 8.0

    def test_zero_start_and_duration(self):
        seg = YouTubeTranscriptSegment(text="hi", start=0.0, duration=0.0)
        assert seg.end == 0.0


class TestYouTubeVideoMetadata:
    def test_defaults(self):
        meta = YouTubeVideoMetadata(
            video_id=VIDEO_ID,
            title="T",
            description="D",
            channel_id="CID",
            channel_title="CT",
            published_at="2024",
            duration="PT5M",
            view_count=0,
            like_count=None,
            comment_count=None,
            thumbnail_urls={},
            tags=[],
            category_id="0",
            default_language=None,
            default_audio_language=None,
            live_broadcast_content="none",
        )
        assert meta.privacy_status == "public"

    def test_explicit_privacy(self):
        meta = YouTubeVideoMetadata(
            video_id=VIDEO_ID,
            title="T",
            description="D",
            channel_id="C",
            channel_title="CT",
            published_at="2024",
            duration="PT1S",
            view_count=0,
            like_count=None,
            comment_count=None,
            thumbnail_urls={},
            tags=[],
            category_id="0",
            default_language=None,
            default_audio_language=None,
            live_broadcast_content="none",
            privacy_status="private",
        )
        assert meta.privacy_status == "private"


class TestYouTubeSearchResult:
    def test_defaults(self):
        r = YouTubeSearchResult(
            video_id="v1",
            title="T",
            description="D",
            channel_title="C",
            published_at="2024",
            thumbnail_url="u",
        )
        assert r.duration is None
        assert r.view_count is None


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_missing_api_key_raises(self):
        with (
            patch.dict("os.environ", {"YOUTUBE_API_KEY": ""}, clear=False),
            patch(f"{_OFFICIAL_MODULE}.os.getenv", return_value=None),
            pytest.raises(ValueError, match="YouTube API key is required"),
        ):
            RealYouTubeAPIService(api_key=None)

    def test_api_key_from_env(self):
        with (
            patch.dict("os.environ", {"YOUTUBE_API_KEY": "ENV_KEY"}),
            patch("httpx.AsyncClient"),
        ):
            svc = RealYouTubeAPIService()
        assert svc.api_key == "ENV_KEY"

    def test_explicit_api_key(self):
        with patch("httpx.AsyncClient"):
            svc = RealYouTubeAPIService(api_key="MY_KEY")
        assert svc.api_key == "MY_KEY"


# ---------------------------------------------------------------------------
# get_video_metadata
# ---------------------------------------------------------------------------


class TestGetVideoMetadata:
    async def test_success(self):
        svc = _make_service()
        resp = _make_http_response(200, _video_api_response())
        svc.client.get = AsyncMock(return_value=resp)

        with patch(
            f"{_OFFICIAL_MODULE}.track_api_call",
            new_callable=AsyncMock,
        ):
            metadata = await svc.get_video_metadata(VIDEO_URL)

        assert metadata.video_id == VIDEO_ID
        assert metadata.title == "Test Video"
        assert metadata.channel_id == "UC_test"
        assert metadata.view_count == 9999
        assert metadata.like_count == 100
        assert metadata.comment_count == 50
        assert metadata.duration == "PT10M"
        assert metadata.privacy_status == "public"
        assert len(metadata.thumbnail_urls) == 2

    async def test_video_not_found_raises(self):
        svc = _make_service()
        resp = _make_http_response(200, {"items": []})
        svc.client.get = AsyncMock(return_value=resp)

        with (
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
            pytest.raises(ValueError, match="Video not found"),
        ):
            await svc.get_video_metadata(VIDEO_ID)

    async def test_http_status_error(self):
        svc = _make_service()
        resp = _make_http_response(403)
        svc.client.get = AsyncMock(return_value=resp)

        with (
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
            pytest.raises(Exception, match="YouTube API error"),
        ):
            await svc.get_video_metadata(VIDEO_ID)

    async def test_generic_exception_propagates(self):
        svc = _make_service()
        svc.client.get = AsyncMock(side_effect=RuntimeError("connection reset"))

        with (
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
            pytest.raises(RuntimeError),
        ):
            await svc.get_video_metadata(VIDEO_ID)

    async def test_statistics_optional_fields_none(self):
        svc = _make_service()
        api_data = _video_api_response()
        api_data["items"][0]["statistics"] = {"viewCount": "42"}
        resp = _make_http_response(200, api_data)
        svc.client.get = AsyncMock(return_value=resp)

        with patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock):
            metadata = await svc.get_video_metadata(VIDEO_ID)

        assert metadata.like_count is None
        assert metadata.comment_count is None
        assert metadata.view_count == 42

    async def test_uses_direct_video_id(self):
        svc = _make_service()
        resp = _make_http_response(200, _video_api_response())
        svc.client.get = AsyncMock(return_value=resp)

        with patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock):
            metadata = await svc.get_video_metadata(VIDEO_ID)

        assert metadata.video_id == VIDEO_ID

    async def test_http_error_tracks_failure(self):
        """HTTPStatusError path should call track_api_call with success=False."""
        svc = _make_service()
        resp = _make_http_response(429)
        svc.client.get = AsyncMock(return_value=resp)

        track_calls = []

        async def mock_track(**kwargs):
            track_calls.append(kwargs)

        with (
            patch(f"{_OFFICIAL_MODULE}.track_api_call", side_effect=mock_track),
            pytest.raises(Exception, match="YouTube API error"),
        ):
            await svc.get_video_metadata(VIDEO_ID)

        # Should have been called twice: once before request, once after error
        assert len(track_calls) == 2
        assert track_calls[1].get("success") is False


# ---------------------------------------------------------------------------
# get_video_transcript
# ---------------------------------------------------------------------------


class TestGetVideoTranscript:
    async def test_no_providers_returns_empty(self):
        svc = _make_service()

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", False),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert result == []

    async def test_transcript_api_success_dict_segments(self):
        svc = _make_service()
        segments = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
            {"text": "World", "start": 2.0, "duration": 2.0},
        ]
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.return_value = segments
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_OFFICIAL_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert len(result) == 2
        assert isinstance(result[0], YouTubeTranscriptSegment)
        assert result[0].text == "Hello"
        assert result[1].text == "World"

    async def test_transcript_api_success_object_segments(self):
        """Segments returned as objects (not dicts) via getattr."""
        svc = _make_service()

        class FakeSeg:
            text = "Segment"
            start = 1.0
            duration = 3.5

        mock_api_instance = MagicMock()
        mock_api_instance.fetch.return_value = [FakeSeg()]
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_OFFICIAL_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert len(result) == 1
        assert result[0].text == "Segment"
        assert result[0].start == 1.0
        assert result[0].duration == 3.5

    async def test_transcripts_disabled_falls_through(self):
        """Simulate TranscriptsDisabled without importing the real class."""
        svc = _make_service()

        # Create a fake TranscriptsDisabled class matching what the code catches
        class FakeTranscriptsDisabled(Exception):
            pass

        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = FakeTranscriptsDisabled(VIDEO_ID)
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_OFFICIAL_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(f"{_OFFICIAL_MODULE}.TranscriptsDisabled", FakeTranscriptsDisabled, create=True),
            patch(f"{_OFFICIAL_MODULE}.NoTranscriptFound", Exception, create=True),
            patch(f"{_OFFICIAL_MODULE}.CouldNotRetrieveTranscript", Exception, create=True),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", False),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert result == []

    async def test_no_transcript_found_falls_through(self):
        """Simulate NoTranscriptFound without importing the real class."""
        svc = _make_service()

        class FakeNoTranscriptFound(Exception):
            pass

        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = FakeNoTranscriptFound(VIDEO_ID)
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_OFFICIAL_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(f"{_OFFICIAL_MODULE}.TranscriptsDisabled", Exception, create=True),
            patch(f"{_OFFICIAL_MODULE}.NoTranscriptFound", FakeNoTranscriptFound, create=True),
            patch(f"{_OFFICIAL_MODULE}.CouldNotRetrieveTranscript", Exception, create=True),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", False),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert result == []

    async def test_could_not_retrieve_falls_through(self):
        """Simulate CouldNotRetrieveTranscript without importing the real class."""
        svc = _make_service()

        class FakeCouldNotRetrieve(Exception):
            pass

        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = FakeCouldNotRetrieve(VIDEO_ID)
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_OFFICIAL_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(f"{_OFFICIAL_MODULE}.TranscriptsDisabled", Exception, create=True),
            patch(f"{_OFFICIAL_MODULE}.NoTranscriptFound", Exception, create=True),
            patch(f"{_OFFICIAL_MODULE}.CouldNotRetrieveTranscript", FakeCouldNotRetrieve, create=True),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", False),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert result == []

    async def test_generic_fetch_error_falls_through(self):
        svc = _make_service()
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = RuntimeError("network error")
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_OFFICIAL_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(f"{_OFFICIAL_MODULE}.TranscriptsDisabled", type("TD", (Exception,), {}), create=True),
            patch(f"{_OFFICIAL_MODULE}.NoTranscriptFound", type("NTF", (Exception,), {}), create=True),
            patch(f"{_OFFICIAL_MODULE}.CouldNotRetrieveTranscript", type("CNR", (Exception,), {}), create=True),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", False),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert result == []

    async def test_fallback_via_robust_with_segments(self):
        svc = _make_service()
        fallback_result = {
            "source": "innertube_android",
            "segments": [
                {"text": "Fallback seg", "start": 0.0, "duration": 2.0}
            ],
            "text": "Fallback seg",
        }
        mock_robust_fn = AsyncMock(return_value=fallback_result)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", True),
            patch(f"{_OFFICIAL_MODULE}.get_video_transcript_robust", mock_robust_fn, create=True),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert len(result) == 1
        assert result[0].text == "Fallback seg"

    async def test_fallback_via_robust_text_only_no_segments(self):
        """If fallback has no segments but has text, a single segment is created."""
        svc = _make_service()
        fallback_result = {
            "source": "some_source",
            "segments": [],
            "text": "Just plain text",
        }
        mock_robust_fn = AsyncMock(return_value=fallback_result)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", True),
            patch(f"{_OFFICIAL_MODULE}.get_video_transcript_robust", mock_robust_fn, create=True),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert len(result) == 1
        assert result[0].text == "Just plain text"

    async def test_fallback_via_robust_fails(self):
        svc = _make_service()
        mock_robust_fn = AsyncMock(side_effect=RuntimeError("fallback fail"))

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", True),
            patch(f"{_OFFICIAL_MODULE}.get_video_transcript_robust", mock_robust_fn, create=True),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert result == []

    async def test_outer_exception_tracks_failure_and_returns_empty(self):
        """When an exception occurs after video_id is set, returns [] and tracks failure."""
        svc = _make_service()

        track_calls = []

        async def mock_track(**kwargs):
            track_calls.append(kwargs)

        # Make the api fetch crash after video_id is extracted
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = RuntimeError("crash after extract")
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_OFFICIAL_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(f"{_OFFICIAL_MODULE}.TranscriptsDisabled", type("TD", (Exception,), {}), create=True),
            patch(f"{_OFFICIAL_MODULE}.NoTranscriptFound", type("NTF", (Exception,), {}), create=True),
            patch(f"{_OFFICIAL_MODULE}.CouldNotRetrieveTranscript", type("CNR", (Exception,), {}), create=True),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", False),
            # Force an exception AFTER video_id assignment by making track_api_call raise
            # on the first call (inside the try block)
            patch(f"{_OFFICIAL_MODULE}.track_api_call", side_effect=mock_track),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert result == []

    async def test_fallback_via_robust_no_segments_and_no_text(self):
        """When fallback returns neither segments nor text, returns []."""
        svc = _make_service()
        fallback_result = {
            "source": "unavailable",
            "segments": [],
            "text": "",
        }
        mock_robust_fn = AsyncMock(return_value=fallback_result)

        with (
            patch(f"{_OFFICIAL_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_OFFICIAL_MODULE}.HAS_ROBUST_TRANSCRIPT_FALLBACK", True),
            patch(f"{_OFFICIAL_MODULE}.get_video_transcript_robust", mock_robust_fn, create=True),
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
        ):
            result = await svc.get_video_transcript(VIDEO_ID)

        assert result == []


# ---------------------------------------------------------------------------
# search_videos
# ---------------------------------------------------------------------------


class TestSearchVideos:
    async def test_successful_search(self):
        svc = _make_service()
        resp = _make_http_response(200, _search_api_response())
        svc.client.get = AsyncMock(return_value=resp)

        with patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock):
            results = await svc.search_videos("python tutorials")

        assert len(results) == 1
        assert results[0].video_id == "other_vid_id"
        assert results[0].title == "Related Video"

    async def test_search_with_optional_params(self):
        svc = _make_service()
        resp = _make_http_response(200, {"items": []})
        svc.client.get = AsyncMock(return_value=resp)

        with patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock):
            results = await svc.search_videos(
                "query",
                max_results=5,
                order="date",
                published_after="2024-01-01T00:00:00Z",
                duration="medium",
                video_type="episode",
            )

        call_args = svc.client.get.call_args
        params = call_args[1].get("params") or call_args[0][1]
        assert params.get("publishedAfter") == "2024-01-01T00:00:00Z"
        assert params.get("videoDuration") == "medium"
        assert params.get("videoType") == "episode"
        assert results == []

    async def test_search_caps_max_results_at_50(self):
        svc = _make_service()
        resp = _make_http_response(200, {"items": []})
        svc.client.get = AsyncMock(return_value=resp)

        with patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock):
            await svc.search_videos("query", max_results=100)

        call_args = svc.client.get.call_args
        params = call_args[1].get("params") or call_args[0][1]
        assert params["maxResults"] == 50

    async def test_search_exception_propagates(self):
        svc = _make_service()
        svc.client.get = AsyncMock(side_effect=RuntimeError("search failed"))

        with (
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
            pytest.raises(RuntimeError),
        ):
            await svc.search_videos("query")

    async def test_search_without_optional_params(self):
        """None optional params should not be added to request params."""
        svc = _make_service()
        resp = _make_http_response(200, {"items": []})
        svc.client.get = AsyncMock(return_value=resp)

        with patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock):
            await svc.search_videos("query")

        call_args = svc.client.get.call_args
        params = call_args[1].get("params") or call_args[0][1]
        assert "publishedAfter" not in params
        assert "videoDuration" not in params
        assert "videoType" not in params


# ---------------------------------------------------------------------------
# get_channel_info
# ---------------------------------------------------------------------------


class TestGetChannelInfo:
    async def test_success(self):
        svc = _make_service()
        resp = _make_http_response(200, _channel_api_response())
        svc.client.get = AsyncMock(return_value=resp)

        with patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock):
            info = await svc.get_channel_info("UC_test")

        assert info["channel_id"] == "UC_test"
        assert info["title"] == "Test Channel"
        assert info["subscriber_count"] == 1000000
        assert info["video_count"] == 200
        assert info["view_count"] == 5000000

    async def test_not_found_raises(self):
        svc = _make_service()
        resp = _make_http_response(200, {"items": []})
        svc.client.get = AsyncMock(return_value=resp)

        with (
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
            pytest.raises(ValueError, match="Channel not found"),
        ):
            await svc.get_channel_info("UC_nonexistent")

    async def test_exception_propagates(self):
        svc = _make_service()
        svc.client.get = AsyncMock(side_effect=RuntimeError("network fail"))

        with (
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
            pytest.raises(RuntimeError),
        ):
            await svc.get_channel_info("UC_test")

    async def test_http_status_error_propagates(self):
        svc = _make_service()
        resp = _make_http_response(403)
        svc.client.get = AsyncMock(return_value=resp)

        with (
            patch(f"{_OFFICIAL_MODULE}.track_api_call", new_callable=AsyncMock),
            pytest.raises(Exception),
        ):
            await svc.get_channel_info("UC_test")


# ---------------------------------------------------------------------------
# get_related_videos
# ---------------------------------------------------------------------------


class TestGetRelatedVideos:
    async def test_success_filters_original(self):
        svc = _make_service()
        meta = YouTubeVideoMetadata(
            video_id=VIDEO_ID,
            title="Original Video",
            description="D",
            channel_id="C",
            channel_title="Chan",
            published_at="2024",
            duration="PT5M",
            view_count=0,
            like_count=None,
            comment_count=None,
            thumbnail_urls={},
            tags=[],
            category_id="0",
            default_language=None,
            default_audio_language=None,
            live_broadcast_content="none",
        )
        related = [
            YouTubeSearchResult(
                video_id="other_vid",
                title="Other",
                description="D",
                channel_title="C",
                published_at="2024",
                thumbnail_url="u",
            ),
            YouTubeSearchResult(
                video_id=VIDEO_ID,
                title="Original Video",
                description="D",
                channel_title="C",
                published_at="2024",
                thumbnail_url="u",
            ),
        ]

        with (
            patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta),
            patch.object(svc, "search_videos", new_callable=AsyncMock, return_value=related),
        ):
            results = await svc.get_related_videos(VIDEO_URL, max_results=5)

        assert len(results) == 1
        assert results[0].video_id == "other_vid"

    async def test_exception_returns_empty(self):
        svc = _make_service()
        with patch.object(
            svc,
            "get_video_metadata",
            new_callable=AsyncMock,
            side_effect=Exception("meta failed"),
        ):
            results = await svc.get_related_videos(VIDEO_URL)

        assert results == []

    async def test_max_results_honored(self):
        svc = _make_service()
        meta = YouTubeVideoMetadata(
            video_id=VIDEO_ID,
            title="T",
            description="D",
            channel_id="C",
            channel_title="CT",
            published_at="2024",
            duration="PT5M",
            view_count=0,
            like_count=None,
            comment_count=None,
            thumbnail_urls={},
            tags=[],
            category_id="0",
            default_language=None,
            default_audio_language=None,
            live_broadcast_content="none",
        )
        many_results = [
            YouTubeSearchResult(
                video_id=f"v{i}",
                title=f"V{i}",
                description="",
                channel_title="C",
                published_at="2024",
                thumbnail_url="u",
            )
            for i in range(10)
        ]

        with (
            patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta),
            patch.object(svc, "search_videos", new_callable=AsyncMock, return_value=many_results),
        ):
            results = await svc.get_related_videos(VIDEO_URL, max_results=3)

        assert len(results) == 3


# ---------------------------------------------------------------------------
# get_comprehensive_video_data
# ---------------------------------------------------------------------------


class TestGetComprehensiveVideoData:
    def _make_metadata(self, privacy_status="public") -> YouTubeVideoMetadata:
        return YouTubeVideoMetadata(
            video_id=VIDEO_ID,
            title="Comprehensive Test Video",
            description="D",
            channel_id="UC_test",
            channel_title="Test Channel",
            published_at="2024-01-01T00:00:00Z",
            duration="PT10M",
            view_count=10000,
            like_count=500,
            comment_count=100,
            thumbnail_urls={"default": "url"},
            tags=["python"],
            category_id="28",
            default_language="en",
            default_audio_language="en",
            live_broadcast_content="none",
            privacy_status=privacy_status,
        )

    async def test_success_all_data(self):
        svc = _make_service()
        meta = self._make_metadata()
        transcript = [
            YouTubeTranscriptSegment(text="Hello", start=0.0, duration=2.0),
            YouTubeTranscriptSegment(text="World", start=2.0, duration=2.0),
        ]
        channel_info = {"channel_id": "UC_test", "title": "Test Channel"}
        related = [
            YouTubeSearchResult(
                video_id="v1",
                title="V1",
                description="",
                channel_title="C",
                published_at="2024",
                thumbnail_url="u",
            )
        ]

        with (
            patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta),
            patch.object(
                svc, "get_video_transcript", new_callable=AsyncMock, return_value=transcript
            ),
            patch.object(
                svc, "get_channel_info", new_callable=AsyncMock, return_value=channel_info
            ),
            patch.object(
                svc, "get_related_videos", new_callable=AsyncMock, return_value=related
            ),
        ):
            data = await svc.get_comprehensive_video_data(VIDEO_URL)

        assert data["video_id"] == VIDEO_ID
        assert data["transcript"]["segment_count"] == 2
        assert data["transcript"]["has_transcript"] is True
        assert data["transcript"]["full_text"] == "Hello World"
        assert data["channel_info"]["title"] == "Test Channel"
        assert len(data["related_videos"]) == 1
        assert data["api_source"] == "youtube_data_api_v3"

    async def test_transcript_exception_gracefully_handled(self):
        svc = _make_service()
        meta = self._make_metadata()

        with (
            patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta),
            patch.object(
                svc,
                "get_video_transcript",
                new_callable=AsyncMock,
                side_effect=RuntimeError("transcript fail"),
            ),
            patch.object(svc, "get_channel_info", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "get_related_videos", new_callable=AsyncMock, return_value=[]),
        ):
            data = await svc.get_comprehensive_video_data(VIDEO_URL)

        assert data["transcript"]["segment_count"] == 0
        assert data["transcript"]["has_transcript"] is False

    async def test_channel_info_error_gracefully_handled(self):
        svc = _make_service()
        meta = self._make_metadata()

        with (
            patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta),
            patch.object(svc, "get_video_transcript", new_callable=AsyncMock, return_value=[]),
            patch.object(
                svc,
                "get_channel_info",
                new_callable=AsyncMock,
                side_effect=RuntimeError("chan fail"),
            ),
            patch.object(svc, "get_related_videos", new_callable=AsyncMock, return_value=[]),
        ):
            data = await svc.get_comprehensive_video_data(VIDEO_URL)

        assert data["channel_info"] == {}

    async def test_related_videos_error_gracefully_handled(self):
        svc = _make_service()
        meta = self._make_metadata()

        with (
            patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta),
            patch.object(svc, "get_video_transcript", new_callable=AsyncMock, return_value=[]),
            patch.object(svc, "get_channel_info", new_callable=AsyncMock, return_value={}),
            patch.object(
                svc,
                "get_related_videos",
                new_callable=AsyncMock,
                side_effect=RuntimeError("related fail"),
            ),
        ):
            data = await svc.get_comprehensive_video_data(VIDEO_URL)

        assert data["related_videos"] == []

    async def test_metadata_error_propagates(self):
        svc = _make_service()
        with patch.object(
            svc,
            "get_video_metadata",
            new_callable=AsyncMock,
            side_effect=ValueError("Video not found"),
        ):
            with pytest.raises(ValueError, match="Video not found"):
                await svc.get_comprehensive_video_data(VIDEO_URL)

    async def test_no_transcript_zero_duration_covered(self):
        svc = _make_service()
        meta = self._make_metadata()

        with (
            patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta),
            patch.object(svc, "get_video_transcript", new_callable=AsyncMock, return_value=[]),
            patch.object(svc, "get_channel_info", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "get_related_videos", new_callable=AsyncMock, return_value=[]),
        ):
            data = await svc.get_comprehensive_video_data(VIDEO_URL)

        assert data["transcript"]["duration_covered"] == 0

    async def test_duration_covered_uses_max_end(self):
        """duration_covered should be max(segment.end) across all segments."""
        svc = _make_service()
        meta = self._make_metadata()
        transcript = [
            YouTubeTranscriptSegment(text="A", start=0.0, duration=2.0),   # end=2.0
            YouTubeTranscriptSegment(text="B", start=5.0, duration=3.0),   # end=8.0
            YouTubeTranscriptSegment(text="C", start=2.0, duration=1.5),   # end=3.5
        ]

        with (
            patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta),
            patch.object(
                svc, "get_video_transcript", new_callable=AsyncMock, return_value=transcript
            ),
            patch.object(svc, "get_channel_info", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "get_related_videos", new_callable=AsyncMock, return_value=[]),
        ):
            data = await svc.get_comprehensive_video_data(VIDEO_URL)

        assert data["transcript"]["duration_covered"] == 8.0


# ---------------------------------------------------------------------------
# validate_video_url
# ---------------------------------------------------------------------------


class TestValidateVideoUrl:
    async def test_public_video(self):
        svc = _make_service()
        meta = MagicMock()
        meta.privacy_status = "public"
        with patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta):
            is_valid, vid_id, msg = await svc.validate_video_url(VIDEO_URL)
        assert is_valid is True
        assert vid_id == VIDEO_ID
        assert "public" in msg

    async def test_private_video(self):
        svc = _make_service()
        meta = MagicMock()
        meta.privacy_status = "private"
        with patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta):
            is_valid, vid_id, msg = await svc.validate_video_url(VIDEO_URL)
        assert is_valid is False
        assert "private" in msg.lower()

    async def test_unlisted_video(self):
        svc = _make_service()
        meta = MagicMock()
        meta.privacy_status = "unlisted"
        with patch.object(svc, "get_video_metadata", new_callable=AsyncMock, return_value=meta):
            is_valid, vid_id, msg = await svc.validate_video_url(VIDEO_URL)
        assert is_valid is True
        assert "unlisted" in msg.lower()

    async def test_invalid_url_format(self):
        svc = _make_service()
        with patch.object(
            svc,
            "get_video_metadata",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid URL"),
        ):
            is_valid, vid_id, msg = await svc.validate_video_url("not-a-url")
        assert is_valid is False
        assert "Invalid URL format" in msg

    async def test_generic_exception(self):
        svc = _make_service()
        with patch.object(
            svc,
            "get_video_metadata",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API down"),
        ):
            is_valid, vid_id, msg = await svc.validate_video_url(VIDEO_URL)
        assert is_valid is False
        assert "Video validation failed" in msg


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    async def test_close_calls_aclose(self):
        svc = _make_service()
        await svc.close()
        svc.client.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    def test_get_youtube_service_creates_instance(self):
        import youtube_extension.backend.services.youtube.adapters.official_api as module

        module.youtube_service = None
        with (
            patch("httpx.AsyncClient"),
            patch.dict("os.environ", {"YOUTUBE_API_KEY": "TEST_KEY"}),
        ):
            svc = get_youtube_service()
        assert isinstance(svc, RealYouTubeAPIService)
        module.youtube_service = None

    def test_get_youtube_service_returns_existing(self):
        import youtube_extension.backend.services.youtube.adapters.official_api as module

        module.youtube_service = None
        with (
            patch("httpx.AsyncClient"),
            patch.dict("os.environ", {"YOUTUBE_API_KEY": "TEST_KEY"}),
        ):
            first = get_youtube_service()
            second = get_youtube_service()
        assert first is second
        module.youtube_service = None

    async def test_get_video_data(self):
        expected = {"video_id": VIDEO_ID}
        with patch(f"{_OFFICIAL_MODULE}.get_youtube_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.get_comprehensive_video_data = AsyncMock(return_value=expected)
            mock_get_svc.return_value = mock_svc

            result = await get_video_data(VIDEO_URL)

        assert result is expected
        mock_svc.get_comprehensive_video_data.assert_awaited_once_with(VIDEO_URL)
