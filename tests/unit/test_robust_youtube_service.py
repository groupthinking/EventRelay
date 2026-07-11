"""
Unit tests for RobustYouTubeService (robust.py).

Coverage targets:
- RobustYouTubeMetadata dataclass
- RobustYouTubeService.__aenter__ / __aexit__
- get_video_metadata – all fallback paths
- _get_metadata_youtube_api
- _get_metadata_pytube
- _get_metadata_search_api
- _get_metadata_ytdlp
- _get_comments
- _get_channel_context
- _check_transcript_availability
- get_transcript – all paths (transcript api / innertube / search python / all-fail)
- _extract_video_id
- Module-level convenience functions

Note: optional libraries (pytube, youtubesearchpython, youtube_transcript_api)
are NOT installed; tests patch the HAS_* flags and inject mocked names via create=True.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.youtube.adapters.innertube import (
    CaptionSegment,
    InnertubeTranscriptError,
    InnertubeTranscriptNotFound,
)
from youtube_extension.backend.services.youtube.adapters.robust import (
    RobustYouTubeMetadata,
    RobustYouTubeService,
    get_video_metadata_robust,
    get_video_transcript_robust,
)

VIDEO_ID = "auJzb1D-fag"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
# A URL that reliably produces None from _extract_video_id (< 11 chars, no match)
INVALID_URL = "not-a-url"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROBUST_MODULE = "youtube_extension.backend.services.youtube.adapters.robust"


def _make_http_response(status: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a mock httpx response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json = MagicMock(return_value=json_data or {})
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status}", request=MagicMock(), response=resp
        )
    return resp


def _youtube_api_response(
    video_id: str = VIDEO_ID,
    title: str = "Test Video",
    channel_id: str = "UC_test",
    channel_title: str = "Test Channel",
    view_count: str = "12345",
    like_count: str = "999",
    comment_count: str = "42",
    duration: str = "PT5M30S",
    published_at: str = "2024-01-01T00:00:00Z",
) -> dict:
    return {
        "items": [
            {
                "id": video_id,
                "snippet": {
                    "title": title,
                    "description": "A test video description",
                    "channelId": channel_id,
                    "channelTitle": channel_title,
                    "publishedAt": published_at,
                    "tags": ["python", "testing"],
                    "categoryId": "28",
                    "defaultLanguage": "en",
                    "defaultAudioLanguage": "en",
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
                "status": {"privacyStatus": "public"},
            }
        ]
    }


def _comments_response() -> dict:
    return {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorDisplayName": "Alice",
                            "textDisplay": "Great video!",
                            "likeCount": 5,
                            "publishedAt": "2024-01-02T00:00:00Z",
                        }
                    }
                }
            }
        ]
    }


def _channel_search_response() -> dict:
    return {
        "items": [
            {
                "id": {"videoId": "other_vid"},
                "snippet": {
                    "title": "Another Video",
                    "publishedAt": "2024-01-03T00:00:00Z",
                },
            }
        ]
    }


def _make_service(api_key: str = "FAKE_KEY") -> RobustYouTubeService:
    svc = RobustYouTubeService(api_key=api_key)
    svc.session = MagicMock(spec=httpx.AsyncClient)
    svc.session.get = AsyncMock()
    return svc


# ---------------------------------------------------------------------------
# RobustYouTubeMetadata dataclass
# ---------------------------------------------------------------------------


class TestRobustYouTubeMetadata:
    def test_defaults(self):
        meta = RobustYouTubeMetadata(
            video_id=VIDEO_ID,
            title="Title",
            description="Desc",
            channel_id="UC_test",
            channel_title="Chan",
            published_at="2024-01-01",
            duration="PT5M",
            view_count=100,
            like_count=10,
            comment_count=5,
            thumbnail_urls={"default": "url"},
            tags=["a", "b"],
            category_id="28",
            default_language="en",
            default_audio_language="en",
            live_broadcast_content="none",
        )
        assert meta.transcript_available is False
        assert meta.transcript_segments == 0
        assert meta.source_api == "unknown"
        assert meta.comments is None
        assert meta.channel_context is None

    def test_with_all_fields(self):
        meta = RobustYouTubeMetadata(
            video_id=VIDEO_ID,
            title="T",
            description="D",
            channel_id="CID",
            channel_title="CT",
            published_at="2024-01-01",
            duration="PT1S",
            view_count=None,
            like_count=None,
            comment_count=None,
            thumbnail_urls={},
            tags=[],
            category_id="0",
            default_language=None,
            default_audio_language=None,
            live_broadcast_content="none",
            transcript_available=True,
            transcript_segments=50,
            source_api="youtube_data_api_v3",
            comments=[{"author": "Bob", "text": "Hi"}],
            channel_context={"channel_id": "CID"},
        )
        assert meta.transcript_available is True
        assert meta.transcript_segments == 50
        assert meta.source_api == "youtube_data_api_v3"


# ---------------------------------------------------------------------------
# _extract_video_id
# ---------------------------------------------------------------------------


class TestExtractVideoId:
    def setup_method(self):
        self.svc = RobustYouTubeService(api_key="FAKE_KEY")

    def test_standard_url(self):
        assert self.svc._extract_video_id(VIDEO_URL) == VIDEO_ID

    def test_short_url(self):
        assert self.svc._extract_video_id(f"https://youtu.be/{VIDEO_ID}") == VIDEO_ID

    def test_embed_url(self):
        assert (
            self.svc._extract_video_id(f"https://www.youtube.com/embed/{VIDEO_ID}")
            == VIDEO_ID
        )

    def test_direct_video_id(self):
        assert self.svc._extract_video_id(VIDEO_ID) == VIDEO_ID

    def test_invalid_url_returns_none(self):
        assert self.svc._extract_video_id(INVALID_URL) is None

    def test_url_with_extra_params(self):
        result = self.svc._extract_video_id(f"{VIDEO_URL}&t=30")
        assert result == VIDEO_ID

    def test_url_with_no_match_returns_none(self):
        # A string with special chars that won't produce 11-char ID
        assert self.svc._extract_video_id("totally invalid with spaces and stuff") is None


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    async def test_aenter_creates_session(self):
        svc = RobustYouTubeService(api_key="KEY")
        mock_client_instance = MagicMock()
        with patch(f"{_ROBUST_MODULE}.httpx.AsyncClient", return_value=mock_client_instance):
            result = await svc.__aenter__()
        assert result is svc
        assert svc.session is mock_client_instance

    async def test_aexit_closes_session(self):
        svc = RobustYouTubeService(api_key="KEY")
        mock_session = AsyncMock()
        svc.session = mock_session
        await svc.__aexit__(None, None, None)
        mock_session.aclose.assert_awaited_once()

    async def test_aexit_with_no_session(self):
        svc = RobustYouTubeService(api_key="KEY")
        # Should not raise
        await svc.__aexit__(None, None, None)

    async def test_as_context_manager(self):
        with patch.object(
            RobustYouTubeService,
            "_get_metadata_youtube_api",
            new_callable=AsyncMock,
        ) as mock_meta:
            mock_meta.return_value = MagicMock(spec=RobustYouTubeMetadata)
            async with RobustYouTubeService(api_key="KEY") as svc:
                result = await svc.get_video_metadata(VIDEO_URL)
            assert result is mock_meta.return_value


# ---------------------------------------------------------------------------
# get_video_metadata – routing / fallback
# ---------------------------------------------------------------------------


class TestGetVideoMetadata:
    async def test_invalid_url_raises(self):
        svc = _make_service()
        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            await svc.get_video_metadata(INVALID_URL)

    async def test_youtube_api_success(self):
        svc = _make_service()
        expected = MagicMock(spec=RobustYouTubeMetadata)
        with patch.object(
            svc, "_get_metadata_youtube_api", new_callable=AsyncMock, return_value=expected
        ):
            result = await svc.get_video_metadata(VIDEO_URL)
        assert result is expected

    async def test_fallback_to_pytube_when_api_fails(self):
        svc = _make_service()
        pytube_result = MagicMock(spec=RobustYouTubeMetadata)
        with (
            patch.object(
                svc,
                "_get_metadata_youtube_api",
                new_callable=AsyncMock,
                side_effect=Exception("API down"),
            ),
            patch(f"{_ROBUST_MODULE}.HAS_PYTube", True),
            patch.object(
                svc,
                "_get_metadata_pytube",
                new_callable=AsyncMock,
                return_value=pytube_result,
            ),
        ):
            result = await svc.get_video_metadata(VIDEO_URL)
        assert result is pytube_result

    async def test_fallback_to_search_api(self):
        svc = _make_service()
        search_result = MagicMock(spec=RobustYouTubeMetadata)
        with (
            patch.object(
                svc,
                "_get_metadata_youtube_api",
                new_callable=AsyncMock,
                side_effect=Exception("API down"),
            ),
            patch(f"{_ROBUST_MODULE}.HAS_PYTube", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch.object(
                svc,
                "_get_metadata_search_api",
                new_callable=AsyncMock,
                return_value=search_result,
            ),
        ):
            result = await svc.get_video_metadata(VIDEO_URL)
        assert result is search_result

    async def test_fallback_to_ytdlp(self):
        svc = _make_service()
        ytdlp_result = MagicMock(spec=RobustYouTubeMetadata)
        with (
            patch.object(
                svc,
                "_get_metadata_youtube_api",
                new_callable=AsyncMock,
                side_effect=Exception("API down"),
            ),
            patch(f"{_ROBUST_MODULE}.HAS_PYTube", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch.object(
                svc,
                "_get_metadata_ytdlp",
                new_callable=AsyncMock,
                return_value=ytdlp_result,
            ),
        ):
            result = await svc.get_video_metadata(VIDEO_URL)
        assert result is ytdlp_result

    async def test_all_fallbacks_fail_raises(self):
        svc = _make_service()
        with (
            patch.object(
                svc,
                "_get_metadata_youtube_api",
                new_callable=AsyncMock,
                side_effect=Exception("API down"),
            ),
            patch(f"{_ROBUST_MODULE}.HAS_PYTube", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch.object(
                svc,
                "_get_metadata_ytdlp",
                new_callable=AsyncMock,
                side_effect=Exception("yt-dlp failed"),
            ),
        ):
            with pytest.raises(Exception, match="All YouTube metadata APIs failed"):
                await svc.get_video_metadata(VIDEO_URL)

    async def test_pytube_fails_falls_through_to_search(self):
        svc = _make_service()
        search_result = MagicMock(spec=RobustYouTubeMetadata)
        with (
            patch.object(
                svc,
                "_get_metadata_youtube_api",
                new_callable=AsyncMock,
                side_effect=Exception("API down"),
            ),
            patch(f"{_ROBUST_MODULE}.HAS_PYTube", True),
            patch.object(
                svc,
                "_get_metadata_pytube",
                new_callable=AsyncMock,
                side_effect=Exception("pytube down"),
            ),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch.object(
                svc,
                "_get_metadata_search_api",
                new_callable=AsyncMock,
                return_value=search_result,
            ),
        ):
            result = await svc.get_video_metadata(VIDEO_URL)
        assert result is search_result


# ---------------------------------------------------------------------------
# _get_metadata_youtube_api
# ---------------------------------------------------------------------------


class TestGetMetadataYouTubeApi:
    async def test_no_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        svc = RobustYouTubeService(api_key=None)
        assert svc.youtube_api_key is None
        with pytest.raises(Exception, match="YouTube API key required"):
            await svc._get_metadata_youtube_api(VIDEO_ID)

    async def test_video_not_found_raises(self):
        svc = _make_service()
        resp = _make_http_response(200, {"items": []})
        svc.session.get = AsyncMock(return_value=resp)
        with (
            patch.object(
                svc,
                "_check_transcript_availability",
                new_callable=AsyncMock,
                return_value=(False, 0),
            ),
            patch.object(svc, "_get_comments", new_callable=AsyncMock, return_value=[]),
            patch.object(
                svc, "_get_channel_context", new_callable=AsyncMock, return_value={}
            ),
        ):
            with pytest.raises(Exception, match="Video not found"):
                await svc._get_metadata_youtube_api(VIDEO_ID)

    async def test_successful_metadata_retrieval(self):
        svc = _make_service()
        api_data = _youtube_api_response()
        resp = _make_http_response(200, api_data)
        svc.session.get = AsyncMock(return_value=resp)

        with (
            patch.object(
                svc,
                "_check_transcript_availability",
                new_callable=AsyncMock,
                return_value=(True, 10),
            ),
            patch.object(
                svc,
                "_get_comments",
                new_callable=AsyncMock,
                return_value=[{"author": "Alice"}],
            ),
            patch.object(
                svc,
                "_get_channel_context",
                new_callable=AsyncMock,
                return_value={"channel_id": "UC_test"},
            ),
        ):
            metadata = await svc._get_metadata_youtube_api(VIDEO_ID)

        assert metadata.video_id == VIDEO_ID
        assert metadata.title == "Test Video"
        assert metadata.channel_id == "UC_test"
        assert metadata.view_count == 12345
        assert metadata.like_count == 999
        assert metadata.comment_count == 42
        assert metadata.duration == "PT5M30S"
        assert metadata.transcript_available is True
        assert metadata.transcript_segments == 10
        assert metadata.source_api == "youtube_data_api_v3"
        assert len(metadata.thumbnail_urls) == 2

    async def test_no_session_creates_one(self):
        svc = RobustYouTubeService(api_key="KEY")
        svc.session = None
        api_data = _youtube_api_response()
        resp = _make_http_response(200, api_data)

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)

        with patch(f"{_ROBUST_MODULE}.httpx.AsyncClient", return_value=mock_client):
            with (
                patch.object(
                    svc,
                    "_check_transcript_availability",
                    new_callable=AsyncMock,
                    return_value=(False, 0),
                ),
                patch.object(svc, "_get_comments", new_callable=AsyncMock, return_value=[]),
                patch.object(
                    svc, "_get_channel_context", new_callable=AsyncMock, return_value={}
                ),
            ):
                metadata = await svc._get_metadata_youtube_api(VIDEO_ID)

        assert metadata is not None
        assert metadata.video_id == VIDEO_ID

    async def test_statistics_none_values(self):
        """Statistics with no likeCount / commentCount should yield None."""
        svc = _make_service()
        api_data = _youtube_api_response()
        api_data["items"][0]["statistics"] = {"viewCount": "5000"}
        resp = _make_http_response(200, api_data)
        svc.session.get = AsyncMock(return_value=resp)

        with (
            patch.object(
                svc,
                "_check_transcript_availability",
                new_callable=AsyncMock,
                return_value=(False, 0),
            ),
            patch.object(svc, "_get_comments", new_callable=AsyncMock, return_value=[]),
            patch.object(
                svc, "_get_channel_context", new_callable=AsyncMock, return_value={}
            ),
        ):
            metadata = await svc._get_metadata_youtube_api(VIDEO_ID)

        assert metadata.like_count is None
        assert metadata.comment_count is None
        assert metadata.view_count == 5000

    async def test_http_raise_for_status_propagates(self):
        svc = _make_service()
        resp = _make_http_response(403)
        svc.session.get = AsyncMock(return_value=resp)

        with pytest.raises(httpx.HTTPStatusError):
            await svc._get_metadata_youtube_api(VIDEO_ID)


# ---------------------------------------------------------------------------
# _get_metadata_pytube
# ---------------------------------------------------------------------------


class TestGetMetadataPyTube:
    async def test_pytube_metadata(self):
        svc = RobustYouTubeService(api_key="KEY")

        fake_pytube_data = {
            "title": "PyTube Title",
            "description": "Desc",
            "channel_title": "My Channel",
            "publish_date": "2024-01-01T00:00:00",
            "length": 300,
            "views": 500,
            "thumbnail_url": "https://example.com/thumb.jpg",
        }

        with patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=fake_pytube_data)
            metadata = await svc._get_metadata_pytube(VIDEO_URL)

        assert metadata.title == "PyTube Title"
        assert metadata.source_api == "pytube"
        assert metadata.view_count == 500
        assert metadata.duration == "PT300S"
        assert metadata.thumbnail_urls == {"default": "https://example.com/thumb.jpg"}

    async def test_pytube_none_values(self):
        svc = RobustYouTubeService(api_key="KEY")

        fake_data = {
            "title": None,
            "description": None,
            "channel_title": None,
            "publish_date": None,
            "length": None,
            "views": None,
            "thumbnail_url": None,
        }

        with patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=fake_data)
            metadata = await svc._get_metadata_pytube(VIDEO_URL)

        assert metadata.title == "Unknown Title"
        assert metadata.channel_title == "Unknown Channel"
        assert metadata.duration == "PT0S"
        assert metadata.thumbnail_urls == {}


# ---------------------------------------------------------------------------
# _get_metadata_search_api
# ---------------------------------------------------------------------------


class TestGetMetadataSearchApi:
    async def test_no_results_raises(self):
        svc = RobustYouTubeService(api_key="KEY")
        mock_VideosSearch = MagicMock()
        mock_search_instance = MagicMock()
        mock_VideosSearch.return_value = mock_search_instance

        with (
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch(f"{_ROBUST_MODULE}.VideosSearch", mock_VideosSearch, create=True),
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value={"result": []})
            with pytest.raises(Exception, match="No search results found"):
                await svc._get_metadata_search_api(VIDEO_ID)

    async def test_successful_search_result(self):
        svc = RobustYouTubeService(api_key="KEY")
        search_response = {
            "result": [
                {
                    "title": "Search Title",
                    "descriptionSnippet": [{"text": "Snippet desc"}],
                    "channel": {"name": "Search Channel"},
                    "publishedTime": "2 weeks ago",
                    "duration": "PT10M",
                    "viewCount": {"text": "1,234,567"},
                    "thumbnails": [{"url": "https://img.com/thumb.jpg"}],
                }
            ]
        }
        mock_VideosSearch = MagicMock()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch(f"{_ROBUST_MODULE}.VideosSearch", mock_VideosSearch, create=True),
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=search_response)
            metadata = await svc._get_metadata_search_api(VIDEO_ID)

        assert metadata.title == "Search Title"
        assert metadata.source_api == "youtube_search_python"
        assert metadata.view_count == 1234567
        assert metadata.description == "Snippet desc"

    async def test_missing_optional_fields(self):
        svc = RobustYouTubeService(api_key="KEY")
        search_response = {
            "result": [
                {
                    "title": "Minimal Video",
                }
            ]
        }
        mock_VideosSearch = MagicMock()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch(f"{_ROBUST_MODULE}.VideosSearch", mock_VideosSearch, create=True),
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=search_response)
            metadata = await svc._get_metadata_search_api(VIDEO_ID)

        assert metadata.title == "Minimal Video"
        assert metadata.view_count is None
        assert metadata.description == ""
        assert metadata.channel_title == "Unknown Channel"


# ---------------------------------------------------------------------------
# _get_metadata_ytdlp
# ---------------------------------------------------------------------------


class TestGetMetadataYtdlp:
    async def test_ytdlp_successful(self):
        svc = RobustYouTubeService(api_key="KEY")

        ytdlp_data = {
            "title": "yt-dlp Title",
            "description": "Some desc",
            "channel_id": "UCytdlp",
            "uploader": "Some Channel",
            "upload_date": "20240101",
            "duration": 360,
            "view_count": 9999,
            "like_count": 200,
            "comment_count": 15,
            "thumbnail": "https://img.example.com/t.jpg",
            "tags": ["tag1"],
            "categories": ["Tech"],
            "language": "en",
        }

        with (
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
            patch.object(
                svc,
                "_check_transcript_availability",
                new_callable=AsyncMock,
                return_value=(True, 20),
            ),
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=ytdlp_data)
            metadata = await svc._get_metadata_ytdlp(VIDEO_URL, VIDEO_ID)

        assert metadata.title == "yt-dlp Title"
        assert metadata.source_api == "yt-dlp"
        assert metadata.duration == "PT360S"
        assert metadata.category_id == "Tech"
        assert metadata.transcript_available is True

    async def test_ytdlp_minimal_data(self):
        svc = RobustYouTubeService(api_key="KEY")

        with (
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
            patch.object(
                svc,
                "_check_transcript_availability",
                new_callable=AsyncMock,
                return_value=(False, 0),
            ),
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value={})
            metadata = await svc._get_metadata_ytdlp(VIDEO_URL, VIDEO_ID)

        assert metadata.title == "Unknown Title"
        assert metadata.category_id == "0"
        assert metadata.source_api == "yt-dlp"

    async def test_ytdlp_uses_channel_field_when_no_uploader(self):
        svc = RobustYouTubeService(api_key="KEY")
        ytdlp_data = {
            "title": "T",
            "channel": "My Channel",
        }

        with (
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
            patch.object(
                svc,
                "_check_transcript_availability",
                new_callable=AsyncMock,
                return_value=(False, 0),
            ),
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=ytdlp_data)
            metadata = await svc._get_metadata_ytdlp(VIDEO_URL, VIDEO_ID)

        assert metadata.channel_title == "My Channel"


# ---------------------------------------------------------------------------
# _get_comments
# ---------------------------------------------------------------------------


class TestGetComments:
    async def test_returns_empty_without_api_key(self):
        svc = RobustYouTubeService(api_key=None)
        result = await svc._get_comments(VIDEO_ID)
        assert result == []

    async def test_returns_empty_without_session(self):
        svc = RobustYouTubeService(api_key="KEY")
        svc.session = None
        result = await svc._get_comments(VIDEO_ID)
        assert result == []

    async def test_non_200_returns_empty(self):
        svc = _make_service()
        resp = _make_http_response(403)
        svc.session.get = AsyncMock(return_value=resp)
        result = await svc._get_comments(VIDEO_ID)
        assert result == []

    async def test_successful_comments(self):
        svc = _make_service()
        resp = _make_http_response(200, _comments_response())
        svc.session.get = AsyncMock(return_value=resp)
        result = await svc._get_comments(VIDEO_ID)
        assert len(result) == 1
        assert result[0]["author"] == "Alice"
        assert result[0]["text"] == "Great video!"

    async def test_exception_returns_empty(self):
        svc = _make_service()
        svc.session.get = AsyncMock(side_effect=RuntimeError("network error"))
        result = await svc._get_comments(VIDEO_ID)
        assert result == []


# ---------------------------------------------------------------------------
# _get_channel_context
# ---------------------------------------------------------------------------


class TestGetChannelContext:
    async def test_returns_empty_without_api_key(self):
        svc = RobustYouTubeService(api_key=None)
        result = await svc._get_channel_context("UC_test")
        assert result == {}

    async def test_returns_empty_without_session(self):
        svc = RobustYouTubeService(api_key="KEY")
        svc.session = None
        result = await svc._get_channel_context("UC_test")
        assert result == {}

    async def test_returns_empty_without_channel_id(self):
        svc = _make_service()
        result = await svc._get_channel_context("")
        assert result == {}

    async def test_non_200_returns_empty(self):
        svc = _make_service()
        resp = _make_http_response(403)
        svc.session.get = AsyncMock(return_value=resp)
        result = await svc._get_channel_context("UC_test")
        assert result == {}

    async def test_successful_channel_context(self):
        svc = _make_service()
        resp = _make_http_response(200, _channel_search_response())
        svc.session.get = AsyncMock(return_value=resp)
        result = await svc._get_channel_context("UC_test")
        assert result["channel_id"] == "UC_test"
        assert len(result["recent_videos"]) == 1
        assert result["recent_videos"][0]["title"] == "Another Video"

    async def test_exception_returns_empty(self):
        svc = _make_service()
        svc.session.get = AsyncMock(side_effect=RuntimeError("timeout"))
        result = await svc._get_channel_context("UC_test")
        assert result == {}


# ---------------------------------------------------------------------------
# _check_transcript_availability
# ---------------------------------------------------------------------------


class TestCheckTranscriptAvailability:
    async def test_returns_false_when_no_providers(self):
        svc = RobustYouTubeService()
        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
        ):
            available, count = await svc._check_transcript_availability(VIDEO_ID)
        assert available is False
        assert count == 0

    async def test_transcript_api_instance_success(self):
        svc = RobustYouTubeService()
        mock_transcript = [{"text": "Hello", "start": 0, "duration": 2}] * 5
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.return_value = mock_transcript
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_ROBUST_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
        ):
            available, count = await svc._check_transcript_availability(VIDEO_ID)

        assert available is True
        assert count == 5

    async def test_transcript_api_fallback_to_list(self):
        svc = RobustYouTubeService()
        mock_transcript = [{"text": "seg"}] * 3
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = Exception("fetch failed")
        mock_api_cls = MagicMock(return_value=mock_api_instance)
        # youtube-transcript-api >=1.0: fallback calls the instance ``list`` then
        # fetches an actual transcript to count real segments (not languages).
        mock_list = MagicMock()
        mock_list.find_transcript.return_value.fetch.return_value = mock_transcript
        mock_api_instance.list.return_value = mock_list

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_ROBUST_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
        ):
            available, count = await svc._check_transcript_availability(VIDEO_ID)

        assert available is True
        assert count == 3

    async def test_no_transcript_api_youtube_search_success(self):
        svc = RobustYouTubeService()
        mock_transcript_data = {"segments": [{"text": "s"}, {"text": "t"}]}
        mock_Transcript = MagicMock()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch(f"{_ROBUST_MODULE}.Transcript", mock_Transcript, create=True),
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=mock_transcript_data
            )
            available, count = await svc._check_transcript_availability(VIDEO_ID)

        assert available is True
        assert count == 2

    async def test_all_inner_fail_returns_false_zero(self):
        """When both the fetch and the list() fallback fail, no transcript was
        obtained, so the method reports (False, 0) — not a contradictory
        (True, 0)."""
        svc = RobustYouTubeService()
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = Exception("boom")
        mock_api_cls = MagicMock(return_value=mock_api_instance)
        # >=1.0: the fallback calls the instance ``list``; make it fail too so
        # the "both inner tries fail" path is actually exercised.
        mock_api_instance.list.side_effect = Exception("boom2")

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_ROBUST_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
        ):
            available, count = await svc._check_transcript_availability(VIDEO_ID)

        assert available is False
        assert count == 0

    async def test_outer_exception_returns_false_zero(self):
        """Outer try/except around the whole body catches unexpected errors."""
        svc = RobustYouTubeService()
        # Force the outer try to raise by making HAS_YOUTUBE_SEARCH truthy
        # but Transcript.get raises unexpected
        mock_Transcript = MagicMock()
        mock_Transcript.get.side_effect = RuntimeError("weird")

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch(f"{_ROBUST_MODULE}.Transcript", mock_Transcript, create=True),
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(
                side_effect=RuntimeError("weird")
            )
            available, count = await svc._check_transcript_availability(VIDEO_ID)

        assert available is False
        assert count == 0


# ---------------------------------------------------------------------------
# get_transcript
# ---------------------------------------------------------------------------


class TestGetTranscript:
    async def test_transcript_api_dict_segments_success(self):
        svc = _make_service()
        segments = [
            {"text": "Hello world", "start": 0.0, "duration": 2.5},
            {"text": "Goodbye world", "start": 2.5, "duration": 2.5},
        ]
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.return_value = segments
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_ROBUST_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "youtube_transcript_api"
        assert result["confidence"] == 0.9
        assert "Hello world" in result["text"]
        assert len(result["segments"]) == 2

    async def test_transcript_api_object_segments_success(self):
        """Segments returned as objects (not dicts) should be handled via getattr."""
        svc = _make_service()

        class FakeSeg:
            text = "Segment text"
            start = 1.0
            duration = 3.0

        mock_api_instance = MagicMock()
        mock_api_instance.fetch.return_value = [FakeSeg()]
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_ROBUST_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "youtube_transcript_api"
        assert "Segment text" in result["text"]

    async def test_transcript_api_fetch_fails_falls_back_to_list_transcripts(self):
        svc = _make_service()
        segments = [{"text": "Fallback segment", "start": 0.0, "duration": 2.0}]

        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = Exception("fetch error")

        mock_transcript_obj = MagicMock()
        mock_transcript_obj.fetch.return_value = segments

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_transcript.return_value = mock_transcript_obj

        mock_api_cls = MagicMock(return_value=mock_api_instance)
        # youtube-transcript-api >=1.0: fallback uses the instance ``list``
        mock_api_instance.list = MagicMock(return_value=mock_transcript_list)

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_ROBUST_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "youtube_transcript_api"
        assert "Fallback segment" in result["text"]

    async def test_transcript_api_returns_empty_text_falls_through(self):
        """When transcript API returns segments with whitespace-only text, falls to innertube."""
        svc = _make_service()
        segments = [{"text": "   ", "start": 0.0, "duration": 1.0}]
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.return_value = segments
        mock_api_cls = MagicMock(return_value=mock_api_instance)

        innertube_segs = [CaptionSegment(text="Innertube text", start=0.0, duration=2.0)]

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_ROBUST_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                return_value=innertube_segs,
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "innertube_android"

    async def test_innertube_success_when_transcript_api_unavailable(self):
        svc = _make_service()
        innertube_segs = [
            CaptionSegment(text="Hello", start=0.0, duration=1.0),
            CaptionSegment(text="World", start=1.0, duration=1.0),
        ]

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                return_value=innertube_segs,
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "innertube_android"
        assert result["confidence"] == 0.75
        assert result["text"] == "Hello World"
        assert len(result["segments"]) == 2

    async def test_innertube_empty_segments_falls_through(self):
        svc = _make_service()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "unavailable"

    async def test_innertube_not_found_error(self):
        svc = _make_service()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                side_effect=InnertubeTranscriptNotFound("no captions"),
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "unavailable"
        assert any("captions not available" in e for e in result["errors"])

    async def test_innertube_transcript_error(self):
        svc = _make_service()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                side_effect=InnertubeTranscriptError("parse error"),
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "unavailable"
        assert any("transcript error" in e for e in result["errors"])

    async def test_innertube_unexpected_error(self):
        svc = _make_service()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                side_effect=RuntimeError("unexpected"),
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "unavailable"
        assert any("unexpected error" in e for e in result["errors"])

    async def test_youtube_search_python_fallback(self):
        svc = _make_service()
        transcript_data = {
            "segments": [
                {"text": "Segment A", "start": 0.0, "duration": 2.0},
                {"text": "Segment B", "start": 2.0, "duration": 2.0},
            ]
        }
        mock_Transcript = MagicMock()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch(f"{_ROBUST_MODULE}.Transcript", mock_Transcript, create=True),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                side_effect=InnertubeTranscriptNotFound("no captions"),
            ),
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=transcript_data)
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "youtube_search_python"
        assert result["confidence"] == 0.8
        assert "Segment A" in result["text"]

    async def test_youtube_search_python_no_segments(self):
        svc = _make_service()
        mock_Transcript = MagicMock()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch(f"{_ROBUST_MODULE}.Transcript", mock_Transcript, create=True),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                side_effect=InnertubeTranscriptNotFound("none"),
            ),
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value={"segments": []})
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "unavailable"
        assert any(
            "YouTube Search Python returned no segments" in e for e in result["errors"]
        )

    async def test_youtube_search_python_exception(self):
        svc = _make_service()
        mock_Transcript = MagicMock()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", True),
            patch(f"{_ROBUST_MODULE}.Transcript", mock_Transcript, create=True),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                side_effect=InnertubeTranscriptNotFound("none"),
            ),
            patch(f"{_ROBUST_MODULE}.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = AsyncMock(
                side_effect=RuntimeError("search fail")
            )
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "unavailable"

    async def test_all_fail_returns_unavailable(self):
        svc = _make_service()

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                side_effect=InnertubeTranscriptNotFound("none"),
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "unavailable"
        assert result["confidence"] == 0.0
        assert result["text"] == ""
        assert "error" in result

    async def test_creates_session_if_none_for_innertube(self):
        """get_transcript creates a session when self.session is None."""
        svc = RobustYouTubeService(api_key="KEY")
        svc.session = None
        innertube_segs = [CaptionSegment(text="Created session", start=0.0, duration=1.0)]

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                return_value=innertube_segs,
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        assert result["source"] == "innertube_android"
        assert svc.session is not None

    async def test_transcript_api_list_transcripts_also_fails(self):
        """Both instance fetch and list_transcripts fail -> falls through to innertube."""
        svc = _make_service()
        mock_api_instance = MagicMock()
        mock_api_instance.fetch.side_effect = Exception("fetch fail")
        mock_api_cls = MagicMock(return_value=mock_api_instance)
        # youtube-transcript-api >=1.0: fallback uses the instance ``list``
        mock_api_instance.list.side_effect = Exception("list fail")

        innertube_segs = [CaptionSegment(text="Hi", start=0.0, duration=1.0)]

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", True),
            patch(f"{_ROBUST_MODULE}.YouTubeTranscriptApi", mock_api_cls, create=True),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                return_value=innertube_segs,
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID)

        # Should fall through to innertube
        assert result["source"] == "innertube_android"

    async def test_transcript_api_not_installed_logs_warning(self):
        """When HAS_TRANSCRIPT_API is False the code logs 'not installed' and continues."""
        svc = _make_service()
        innertube_segs = [CaptionSegment(text="Via innertube", start=0.0, duration=1.0)]

        with (
            patch(f"{_ROBUST_MODULE}.HAS_TRANSCRIPT_API", False),
            patch(f"{_ROBUST_MODULE}.HAS_YOUTUBE_SEARCH", False),
            patch(
                f"{_ROBUST_MODULE}.fetch_innertube_transcript",
                new_callable=AsyncMock,
                return_value=innertube_segs,
            ),
        ):
            result = await svc.get_transcript(VIDEO_ID, language="fr")

        assert result["source"] == "innertube_android"


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    async def test_get_video_metadata_robust(self):
        expected = MagicMock(spec=RobustYouTubeMetadata)
        with patch.object(
            RobustYouTubeService,
            "get_video_metadata",
            new_callable=AsyncMock,
            return_value=expected,
        ):
            result = await get_video_metadata_robust(VIDEO_URL, api_key="KEY")
        assert result is expected

    async def test_get_video_transcript_robust(self):
        expected = {
            "text": "hello",
            "source": "youtube_transcript_api",
            "confidence": 0.9,
            "segments": [],
            "processing_time": "now",
        }
        with patch.object(
            RobustYouTubeService,
            "get_transcript",
            new_callable=AsyncMock,
            return_value=expected,
        ):
            result = await get_video_transcript_robust(VIDEO_ID, api_key="KEY", language="en")
        assert result is expected

    async def test_get_video_metadata_robust_no_api_key(self):
        """Should work without an api_key (uses env var fallback)."""
        expected = MagicMock(spec=RobustYouTubeMetadata)
        with (
            patch.dict("os.environ", {}, clear=False),
            patch.object(
                RobustYouTubeService,
                "get_video_metadata",
                new_callable=AsyncMock,
                return_value=expected,
            ),
        ):
            result = await get_video_metadata_robust(VIDEO_URL)
        assert result is expected
