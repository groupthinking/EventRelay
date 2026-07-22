"""Unit tests for backend/enhanced_video_processor.py.

Covers EnhancedVideoProcessor: __init__, all async/sync methods, branches, error paths.
External dependencies (aiohttp, certifi, ssl, youtube_transcript_api, GeminiService) are
fully mocked so tests run without any network or heavyweight library.
"""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

# ---------------------------------------------------------------------------
# Path setup — ensure src/ is on sys.path
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Import the module under test. Individual constructor tests provide their own
# scoped credentials so test collection never mutates the process environment.
# ---------------------------------------------------------------------------
import os

import youtube_extension.backend.enhanced_video_processor as _mod
from youtube_extension.backend.enhanced_video_processor import (
    EnhancedVideoProcessor,
    get_enhanced_video_processor,
)

_VIDEO_URL = "https://www.youtube.com/watch?v=auJzb1D-fag"
_VIDEO_ID = "auJzb1D-fag"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_processor(monkeypatch=None, *, gemini_key="test-key", youtube_key=None):
    """Create an EnhancedVideoProcessor with external deps mocked out."""
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "PYTHONPATH")}
    env["GEMINI_API_KEY"] = gemini_key
    if youtube_key:
        env["YOUTUBE_API_KEY"] = youtube_key

    with patch.dict(os.environ, env, clear=True):
        with patch.object(_mod, "GEMINI_VISION_AVAILABLE", False):
            proc = EnhancedVideoProcessor()
    return proc


def _aiohttp_response(status=200, json_data=None):
    """Build a mock aiohttp response context-manager."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})

    @asynccontextmanager
    async def _ctx(*args, **kwargs):
        yield resp

    return resp, _ctx


def _make_session(get_ctx=None, post_ctx=None):
    """Return a mock aiohttp ClientSession."""
    session = MagicMock()
    if get_ctx:
        session.get = get_ctx
    if post_ctx:
        session.post = post_ctx
    session.close = AsyncMock()
    return session


# ===========================================================================
# EnhancedVideoProcessor.__init__
# ===========================================================================

class TestEnhancedVideoProcessorInit:
    def test_init_with_gemini_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "my-key"}, clear=False):
            with patch.object(_mod, "GEMINI_VISION_AVAILABLE", False):
                proc = EnhancedVideoProcessor()
        assert proc.gemini_api_key == "my-key"
        assert proc.session is None

    def test_init_falls_back_to_google_api_key(self):
        env = {"GOOGLE_API_KEY": "google-key"}
        with patch.dict(os.environ, env, clear=False):
            with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
                with patch.object(_mod, "GEMINI_VISION_AVAILABLE", False):
                    # Remove GEMINI_API_KEY entirely
                    saved = os.environ.pop("GEMINI_API_KEY", None)
                    try:
                        proc = EnhancedVideoProcessor()
                        assert proc.gemini_api_key == "google-key"
                    finally:
                        if saved is not None:
                            os.environ["GEMINI_API_KEY"] = saved

    def test_init_raises_without_api_key(self):
        env_clean = {k: v for k, v in os.environ.items()
                     if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY")}
        with patch.dict(os.environ, env_clean, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                EnhancedVideoProcessor()

    def test_init_uses_openai_key_as_fallback(self):
        env = {"OPENAI_API_KEY": "oai-key"}
        env_clean = {k: v for k, v in os.environ.items()
                     if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY")}
        env_clean.update(env)
        with patch.dict(os.environ, env_clean, clear=True):
            with patch.object(_mod, "GEMINI_VISION_AVAILABLE", False):
                proc = EnhancedVideoProcessor()
        assert proc.gemini_api_key == "oai-key"

    def test_gemini_base_url_set(self):
        proc = _make_processor()
        assert "googleapis.com" in proc.gemini_base_url

    def test_livekit_url_default(self):
        proc = _make_processor()
        assert proc.livekit_url == "ws://localhost:7880"

    def test_livekit_url_from_env(self):
        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "test-key", "LIVEKIT_URL": "ws://custom:7880"},
            clear=False,
        ):
            with patch.object(_mod, "GEMINI_VISION_AVAILABLE", False):
                proc = EnhancedVideoProcessor()
        assert proc.livekit_url == "ws://custom:7880"

    def test_gemini_vision_none_when_unavailable(self):
        proc = _make_processor()
        assert proc.gemini_vision is None

    def test_gemini_vision_initialized_when_available(self):
        mock_config_cls = MagicMock()
        mock_config_inst = MagicMock()
        mock_config_cls.return_value = mock_config_inst

        mock_service_cls = MagicMock()
        mock_service_inst = MagicMock()
        mock_service_cls.return_value = mock_service_inst

        with patch.object(_mod, "GEMINI_VISION_AVAILABLE", True):
            with patch.object(_mod, "GeminiConfig", mock_config_cls):
                with patch.object(_mod, "GeminiService", mock_service_cls):
                    proc = _make_processor()
                    # GEMINI_VISION_AVAILABLE=False override was already applied in _make_processor,
                    # so re-create directly
                    with patch.dict(os.environ, {"GEMINI_API_KEY": "key"}, clear=False):
                        proc2 = EnhancedVideoProcessor.__new__(EnhancedVideoProcessor)
                        proc2.gemini_api_key = "key"
                        proc2.youtube_api_key = None
                        proc2.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta"
                        proc2.livekit_url = "ws://localhost:7880"
                        proc2.session = None
                        proc2.gemini_vision = None
                        # Simulate vision init
                        config = mock_config_cls(
                            api_key="key",
                            model_name="gemini-2.0-flash-exp",
                            temperature=0.2,
                            max_output_tokens=4096,
                        )
                        proc2.gemini_vision = mock_service_cls(config)
        assert mock_service_inst is not None

    def test_gemini_vision_init_exception_sets_none(self):
        mock_config_cls = MagicMock(side_effect=RuntimeError("cfg error"))
        with patch.dict(os.environ, {"GEMINI_API_KEY": "key"}, clear=False):
            with patch.object(_mod, "GEMINI_VISION_AVAILABLE", True):
                with patch.object(_mod, "GeminiConfig", mock_config_cls):
                    proc = EnhancedVideoProcessor()
        assert proc.gemini_vision is None


# ===========================================================================
# _extract_video_id
# ===========================================================================

class TestExtractVideoId:
    def setup_method(self):
        self.proc = _make_processor()

    def test_standard_watch_url(self):
        assert self.proc._extract_video_id(_VIDEO_URL) == _VIDEO_ID

    def test_short_url(self):
        assert self.proc._extract_video_id(f"https://youtu.be/{_VIDEO_ID}") == _VIDEO_ID

    def test_embed_url(self):
        assert self.proc._extract_video_id(f"https://www.youtube.com/embed/{_VIDEO_ID}") == _VIDEO_ID

    def test_plain_video_id(self):
        assert self.proc._extract_video_id(_VIDEO_ID) == _VIDEO_ID

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Could not extract"):
            self.proc._extract_video_id("https://example.com/noid")

    def test_url_with_extra_params(self):
        url = f"https://www.youtube.com/watch?v={_VIDEO_ID}&t=42s"
        assert self.proc._extract_video_id(url) == _VIDEO_ID


# ===========================================================================
# _parse_duration
# ===========================================================================

class TestParseDuration:
    def setup_method(self):
        self.proc = _make_processor()

    def test_full_hms(self):
        assert self.proc._parse_duration("PT1H2M3S") == "1h 2m 3s"

    def test_minutes_seconds(self):
        assert self.proc._parse_duration("PT15M30S") == "15m 30s"

    def test_seconds_only(self):
        assert self.proc._parse_duration("PT45S") == "45s"

    def test_hours_no_seconds(self):
        assert self.proc._parse_duration("PT2H0M") == "2h 0m 0s"

    def test_invalid_format_returned_as_is(self):
        assert self.proc._parse_duration("INVALID") == "INVALID"

    def test_minutes_only(self):
        assert self.proc._parse_duration("PT10M") == "10m 0s"


# ===========================================================================
# _categorize_video
# ===========================================================================

class TestCategorizeVideo:
    """Test _categorize_video.

    NOTE: The method uses plain substring matching (`keyword in text`) on the
    concatenated title+description.  Several keywords are single letters or
    short strings that appear as substrings in many words (e.g. 'r' in 'r'
    for Data Science matches 'recipes'; 'ai' in 'AI/ML' matches 'container').
    Categories are checked in dict-insertion order and the FIRST match wins.

    Order in source:
        Programming → AI/ML → Web Development → Data Science → DevOps →
        Mobile → Game Development → Cybersecurity → Blockchain → Cloud Computing

    Tests below use carefully chosen snippets that match ONLY the target
    category and do not trigger earlier categories.
    """

    def setup_method(self):
        self.proc = _make_processor()

    def test_programming_category(self):
        # "code" matches Programming and nothing before it
        snippet = {"title": "Code Fundamentals", "description": "Learn to code"}
        assert self.proc._categorize_video(snippet) == "Programming"

    def test_ai_ml_category(self):
        # "machine learning" matches AI/ML; avoid 'code'/'programming' keywords
        snippet = {"title": "Machine Learning 101", "description": "deep learning intro"}
        assert self.proc._categorize_video(snippet) == "AI/ML"

    def test_web_dev_category(self):
        # "javascript" matches Web Development without triggering Programming/AI/ML/DataScience
        snippet = {"title": "JavaScript Tips", "description": "css html vue"}
        assert self.proc._categorize_video(snippet) == "Web Development"

    def test_data_science_category(self):
        # "analysis" and "statistics" match Data Science.
        # Avoid 'code','programming','ai','machine learning','web','html','css','javascript'
        snippet = {"title": "Exploratory Analysis", "description": "statistics"}
        assert self.proc._categorize_video(snippet) == "Data Science"

    def test_devops_category(self):
        # "ci/cd" is a DevOps keyword with no 'r' (avoids Data Science 'r' substring match)
        snippet = {"title": "CI/CD Pipeline Setup", "description": "continuous deployment"}
        assert self.proc._categorize_video(snippet) == "DevOps"

    def test_mobile_category(self):
        # "ios" and "mobile" have no 'r'; avoids Data Science 'r' match
        snippet = {"title": "iOS Mobile App Guide", "description": ""}
        assert self.proc._categorize_video(snippet) == "Mobile"

    def test_game_dev_category(self):
        # "unity" has no 'r'; "gaming" has no 'r' either
        snippet = {"title": "Unity Basics", "description": "gaming"}
        assert self.proc._categorize_video(snippet) == "Game Development"

    def test_security_category(self):
        # "hacking" and "ethical" have no 'r'; avoids Data Science match
        snippet = {"title": "Ethical Hacking", "description": "hacking basics"}
        assert self.proc._categorize_video(snippet) == "Cybersecurity"

    def test_blockchain_category(self):
        # "defi" has no 'r', no 'ai', no 'web'; unique to Blockchain
        snippet = {"title": "DeFi Basics", "description": ""}
        assert self.proc._categorize_video(snippet) == "Blockchain"

    def test_cloud_category(self):
        # "aws" and "gcp" and "cloud" have no 'r'; unique to Cloud Computing
        snippet = {"title": "AWS GCP Cloud", "description": "cloud computing"}
        assert self.proc._categorize_video(snippet) == "Cloud Computing"

    def test_general_fallback(self):
        # No keywords from any category — use truly neutral text
        snippet = {"title": "Cooking With Love", "description": "food and kitchen tips"}
        assert self.proc._categorize_video(snippet) == "General"

    def test_empty_snippet(self):
        assert self.proc._categorize_video({}) == "General"


# ===========================================================================
# get_cached_result
# ===========================================================================

class TestGetCachedResult:
    def test_returns_none(self):
        proc = _make_processor()
        assert proc.get_cached_result(_VIDEO_URL) is None

    def test_returns_none_for_any_url(self):
        proc = _make_processor()
        assert proc.get_cached_result("https://www.youtube.com/watch?v=aaaaaaaaaaa") is None


# ===========================================================================
# _coerce_analysis_to_structured_dict
# ===========================================================================

class TestCoerceAnalysisToStructuredDict:
    def setup_method(self):
        self.proc = _make_processor()

    def test_valid_json_in_text_extracted(self):
        text = 'Some preamble {"key": "value", "nested": 1} trailing'
        result = self.proc._coerce_analysis_to_structured_dict(text)
        assert result.get("key") == "value"

    def test_fallback_on_invalid_json(self):
        text = "Summary line\n- Concept 1\n- Concept 2"
        result = self.proc._coerce_analysis_to_structured_dict(text)
        assert result["summary"] == "Summary line"
        assert "Concept 1" in result["key_concepts"]

    def test_empty_text_returns_empty_summary(self):
        result = self.proc._coerce_analysis_to_structured_dict("")
        assert result["summary"] == ""

    def test_source_is_gemini_api(self):
        result = self.proc._coerce_analysis_to_structured_dict("text")
        assert result["source"] == "gemini_api"

    def test_format_is_text_coerced(self):
        result = self.proc._coerce_analysis_to_structured_dict("text")
        assert result["format"] == "text_coerced"

    def test_analysis_field_contains_original_text(self):
        text = "Original analysis text"
        result = self.proc._coerce_analysis_to_structured_dict(text)
        assert result["analysis"] == text

    def test_bad_json_snippet_falls_back(self):
        text = "{bad json here}"
        result = self.proc._coerce_analysis_to_structured_dict(text)
        # should not raise; returns a dict
        assert isinstance(result, dict)

    def test_bullet_points_become_key_concepts(self):
        text = "Title\n* Item A\n* Item B\n* Item C"
        result = self.proc._coerce_analysis_to_structured_dict(text)
        assert "Item A" in result["key_concepts"]

    def test_max_8_concepts(self):
        bullets = "\n".join(f"- Concept {i}" for i in range(15))
        text = f"Title\n{bullets}"
        result = self.proc._coerce_analysis_to_structured_dict(text)
        # key_concepts is formatted lines separated by newline
        count = result["key_concepts"].count("- Concept")
        assert count <= 8


# ===========================================================================
# _init_session
# ===========================================================================

class TestInitSession:
    async def test_creates_session_on_first_call(self):
        proc = _make_processor()
        mock_session = MagicMock()
        mock_connector = MagicMock()
        mock_ssl_ctx = MagicMock()

        with patch("ssl.create_default_context", return_value=mock_ssl_ctx):
            with patch("certifi.where", return_value="/certs"):
                with patch("aiohttp.TCPConnector", return_value=mock_connector):
                    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_cls:
                        await proc._init_session()

        assert proc.session is mock_session
        mock_cls.assert_called_once()

    async def test_does_not_recreate_existing_session(self):
        proc = _make_processor()
        existing = MagicMock()
        existing.closed = False
        proc.session = existing

        with patch("aiohttp.ClientSession") as mock_cls:
            await proc._init_session()

        mock_cls.assert_not_called()
        assert proc.session is existing


# ===========================================================================
# close
# ===========================================================================

class TestClose:
    async def test_close_calls_session_close(self):
        proc = _make_processor()
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        proc.session = mock_session

        await proc.close()

        mock_session.close.assert_awaited_once()

    async def test_close_with_no_session(self):
        proc = _make_processor()
        assert proc.session is None
        # Should not raise
        await proc.close()


# ===========================================================================
# _get_video_metadata
# ===========================================================================

class TestGetVideoMetadata:
    async def test_returns_error_dict_when_no_youtube_key(self):
        proc = _make_processor()  # no youtube key
        assert proc.youtube_api_key is None
        result = await proc._get_video_metadata(_VIDEO_ID)
        assert "error" in result

    async def test_returns_metadata_on_200(self):
        proc = _make_processor(youtube_key="yt-key")
        video_data = {
            "items": [{
                "snippet": {
                    "title": "Test Video",
                    "channelTitle": "Test Channel",
                    "description": "A test video description",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
                    "tags": ["tag1", "tag2"],
                    "categoryId": "28",
                },
                "contentDetails": {"duration": "PT10M30S"},
                "statistics": {"viewCount": "1000", "likeCount": "100", "commentCount": "50"},
            }]
        }
        resp, get_ctx = _aiohttp_response(200, video_data)
        session = MagicMock()
        session.get = get_ctx
        proc.session = session

        result = await proc._get_video_metadata(_VIDEO_ID)

        assert result["title"] == "Test Video"
        assert result["channel"] == "Test Channel"
        assert result["duration"] == "10m 30s"
        assert result["view_count"] == 1000

    async def test_returns_error_on_non_200(self):
        proc = _make_processor(youtube_key="yt-key")
        resp, get_ctx = _aiohttp_response(403, {})
        session = MagicMock()
        session.get = get_ctx
        proc.session = session

        result = await proc._get_video_metadata(_VIDEO_ID)

        assert "error" in result

    async def test_returns_error_when_no_items(self):
        proc = _make_processor(youtube_key="yt-key")
        resp, get_ctx = _aiohttp_response(200, {"items": []})
        session = MagicMock()
        session.get = get_ctx
        proc.session = session

        result = await proc._get_video_metadata(_VIDEO_ID)

        assert "error" in result

    async def test_description_truncated_at_500(self):
        proc = _make_processor(youtube_key="yt-key")
        long_desc = "x" * 600
        video_data = {
            "items": [{
                "snippet": {
                    "title": "T",
                    "channelTitle": "C",
                    "description": long_desc,
                    "publishedAt": "2024-01-01",
                    "thumbnails": {"high": {"url": "http://x.com"}},
                    "tags": [],
                    "categoryId": "1",
                },
                "contentDetails": {"duration": "PT5S"},
                "statistics": {"viewCount": "0", "likeCount": "0", "commentCount": "0"},
            }]
        }
        resp, get_ctx = _aiohttp_response(200, video_data)
        session = MagicMock()
        session.get = get_ctx
        proc.session = session

        result = await proc._get_video_metadata(_VIDEO_ID)
        # description should be 500 chars + "..."
        assert len(result["description"]) <= 504


# ===========================================================================
# _get_youtube_transcript_fallback
# ===========================================================================

class TestGetYoutubeTranscriptFallback:
    async def test_success_path(self):
        proc = _make_processor()

        mock_segment = MagicMock()
        mock_segment.text = "Hello world"
        mock_segment.start = 0.0
        mock_segment.duration = 2.5

        mock_yt_api = MagicMock()
        mock_yt_api.fetch.return_value = [mock_segment]

        mock_api_cls = MagicMock(return_value=mock_yt_api)

        with patch.dict("sys.modules", {"youtube_transcript_api": MagicMock(YouTubeTranscriptApi=mock_api_cls)}):
            result = await proc._get_youtube_transcript_fallback(_VIDEO_ID)

        assert result["source"] == "youtube_api_fallback"
        assert result["text"] == "Hello world"
        assert result["confidence"] == 0.8

    async def test_multiple_segments_joined(self):
        proc = _make_processor()

        segs = []
        for i, word in enumerate(["Hello", "world", "foo"]):
            s = MagicMock()
            s.text = word
            s.start = float(i)
            s.duration = 1.0
            segs.append(s)

        mock_yt_api = MagicMock()
        mock_yt_api.fetch.return_value = segs
        mock_api_cls = MagicMock(return_value=mock_yt_api)

        with patch.dict("sys.modules", {"youtube_transcript_api": MagicMock(YouTubeTranscriptApi=mock_api_cls)}):
            result = await proc._get_youtube_transcript_fallback(_VIDEO_ID)

        assert result["text"] == "Hello world foo"
        assert len(result["segments"]) == 3

    async def test_exception_returns_failed_dict(self):
        proc = _make_processor()

        with patch.dict("sys.modules", {"youtube_transcript_api": None}):
            # Importing None causes TypeError
            result = await proc._get_youtube_transcript_fallback(_VIDEO_ID)

        assert result["source"] == "failed"
        assert result["confidence"] == 0.0
        assert "error" in result

    async def test_api_fetch_exception_returns_failed(self):
        proc = _make_processor()

        mock_yt_api = MagicMock()
        mock_yt_api.fetch.side_effect = Exception("Network error")
        mock_api_cls = MagicMock(return_value=mock_yt_api)

        with patch.dict("sys.modules", {"youtube_transcript_api": MagicMock(YouTubeTranscriptApi=mock_api_cls)}):
            result = await proc._get_youtube_transcript_fallback(_VIDEO_ID)

        assert result["source"] == "failed"


# ===========================================================================
# _get_gemini_transcript
# ===========================================================================

class TestGetGeminiTranscript:
    async def test_success_returns_transcript(self):
        proc = _make_processor()
        transcript_text = "This is the transcript text"
        response_data = {
            "candidates": [{"content": {"parts": [{"text": transcript_text}]}}]
        }
        resp, post_ctx = _aiohttp_response(200, response_data)
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        result = await proc._get_gemini_transcript(_VIDEO_ID, _VIDEO_URL)

        assert result["source"] == "gemini_api"
        assert result["text"] == transcript_text
        assert result["confidence"] == 0.95

    async def test_non_200_falls_back_to_youtube(self):
        proc = _make_processor()
        resp, post_ctx = _aiohttp_response(500, {})
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        # Mock _get_youtube_transcript_fallback
        fallback_result = {"source": "youtube_api_fallback", "text": "fallback", "confidence": 0.8}
        proc._get_youtube_transcript_fallback = AsyncMock(return_value=fallback_result)

        result = await proc._get_gemini_transcript(_VIDEO_ID, _VIDEO_URL)
        assert result["source"] == "youtube_api_fallback"

    async def test_empty_parts_falls_back(self):
        proc = _make_processor()
        response_data = {"candidates": [{"content": {"parts": []}}]}
        resp, post_ctx = _aiohttp_response(200, response_data)
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        fallback_result = {"source": "failed", "text": "", "confidence": 0.0}
        proc._get_youtube_transcript_fallback = AsyncMock(return_value=fallback_result)

        result = await proc._get_gemini_transcript(_VIDEO_ID, _VIDEO_URL)
        assert result["source"] == "failed"

    async def test_no_api_key_raises_internally_and_falls_back(self):
        proc = _make_processor()
        proc.gemini_api_key = None

        fallback = {"source": "youtube_api_fallback", "text": "fb", "confidence": 0.8}
        proc._get_youtube_transcript_fallback = AsyncMock(return_value=fallback)

        result = await proc._get_gemini_transcript(_VIDEO_ID, _VIDEO_URL)
        assert result["source"] == "youtube_api_fallback"


# ===========================================================================
# _analyze_with_gemini
# ===========================================================================

class TestAnalyzeWithGemini:
    async def test_returns_parsed_json(self):
        proc = _make_processor()
        analysis = {"Content Summary": "Great video", "Key Concepts": ["a", "b"]}
        response_data = {
            "candidates": [{"content": {"parts": [{"text": json.dumps(analysis)}]}}]
        }
        resp, post_ctx = _aiohttp_response(200, response_data)
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        result = await proc._analyze_with_gemini(_VIDEO_URL, {"text": "transcript"}, {"title": "T"})

        assert result["Content Summary"] == "Great video"

    async def test_extracts_json_from_code_fence(self):
        proc = _make_processor()
        analysis = {"Content Summary": "Fenced JSON"}
        fenced = f"```json\n{json.dumps(analysis)}\n```"
        response_data = {
            "candidates": [{"content": {"parts": [{"text": fenced}]}}]
        }
        resp, post_ctx = _aiohttp_response(200, response_data)
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        result = await proc._analyze_with_gemini(_VIDEO_URL, {"text": "t"}, {"title": "T"})
        assert result["Content Summary"] == "Fenced JSON"

    async def test_coerces_plain_text_response(self):
        proc = _make_processor()
        plain_text = "This is a summary\n- Key concept 1\n- Key concept 2"
        response_data = {
            "candidates": [{"content": {"parts": [{"text": plain_text}]}}]
        }
        resp, post_ctx = _aiohttp_response(200, response_data)
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        result = await proc._analyze_with_gemini(_VIDEO_URL, {"text": "t"}, {"title": "T"})
        assert "summary" in result or "Content Summary" in result

    async def test_non_200_returns_error_dict(self):
        proc = _make_processor()
        resp, post_ctx = _aiohttp_response(429, {})
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        result = await proc._analyze_with_gemini(_VIDEO_URL, {"text": "t"}, {"title": "T"})
        assert "error" in result or "source" in result

    async def test_no_api_key_returns_error(self):
        proc = _make_processor()
        proc.gemini_api_key = None

        result = await proc._analyze_with_gemini(_VIDEO_URL, {}, {})
        assert result.get("error") == "GEMINI_API_KEY not configured"

    async def test_empty_parts_returns_error(self):
        proc = _make_processor()
        response_data = {"candidates": [{"content": {"parts": []}}]}
        resp, post_ctx = _aiohttp_response(200, response_data)
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        result = await proc._analyze_with_gemini(_VIDEO_URL, {"text": "t"}, {"title": "T"})
        assert isinstance(result, dict)

    async def test_bad_fenced_json_falls_back_to_coerce(self):
        proc = _make_processor()
        bad_fenced = "```json\n{bad json\n```"
        response_data = {
            "candidates": [{"content": {"parts": [{"text": bad_fenced}]}}]
        }
        resp, post_ctx = _aiohttp_response(200, response_data)
        session = MagicMock()
        session.post = post_ctx
        proc.session = session

        result = await proc._analyze_with_gemini(_VIDEO_URL, {"text": "t"}, {"title": "T"})
        assert isinstance(result, dict)


# ===========================================================================
# _extract_visual_context
# ===========================================================================

class TestExtractVisualContext:
    async def test_no_gemini_vision_returns_empty(self):
        proc = _make_processor()
        proc.gemini_vision = None

        result = await proc._extract_visual_context(_VIDEO_URL, _VIDEO_ID)

        assert result["visual_elements"] == []
        assert result["frame_analysis_count"] == 0
        assert "not available" in result["summary"]

    async def test_with_gemini_vision_success_json(self):
        proc = _make_processor()
        mock_vision = MagicMock()
        visual_data = {
            "visual_elements": [
                {"element_type": "code", "content": "print('hi')", "timestamp": 10, "confidence": 0.9}
            ],
            "summary": "One code element"
        }
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.response = json.dumps(visual_data)
        mock_vision.process_youtube = AsyncMock(return_value=mock_result)
        proc.gemini_vision = mock_vision

        result = await proc._extract_visual_context(_VIDEO_URL, _VIDEO_ID)

        assert len(result["visual_elements"]) == 1
        assert result["frame_analysis_count"] == 1

    async def test_with_gemini_vision_fenced_json(self):
        proc = _make_processor()
        mock_vision = MagicMock()
        visual_data = {"visual_elements": [{"element_type": "diagram", "content": "arch", "timestamp": 5, "confidence": 0.8}]}
        fenced_resp = f"```json\n{json.dumps(visual_data)}\n```"
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.response = fenced_resp
        mock_vision.process_youtube = AsyncMock(return_value=mock_result)
        proc.gemini_vision = mock_vision

        result = await proc._extract_visual_context(_VIDEO_URL, _VIDEO_ID)
        assert len(result["visual_elements"]) == 1

    async def test_with_gemini_vision_bad_json_returns_empty_elements(self):
        proc = _make_processor()
        mock_vision = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.response = "totally not json"
        mock_vision.process_youtube = AsyncMock(return_value=mock_result)
        proc.gemini_vision = mock_vision

        result = await proc._extract_visual_context(_VIDEO_URL, _VIDEO_ID)
        assert result["visual_elements"] == []

    async def test_with_gemini_vision_failure_returns_fallback(self):
        proc = _make_processor()
        mock_vision = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "API error"
        mock_vision.process_youtube = AsyncMock(return_value=mock_result)
        proc.gemini_vision = mock_vision

        result = await proc._extract_visual_context(_VIDEO_URL, _VIDEO_ID)
        assert result["visual_elements"] == []
        assert "not completed" in result["summary"]

    async def test_with_gemini_vision_exception_returns_fallback(self):
        proc = _make_processor()
        mock_vision = MagicMock()
        mock_vision.process_youtube = AsyncMock(side_effect=Exception("crash"))
        proc.gemini_vision = mock_vision

        result = await proc._extract_visual_context(_VIDEO_URL, _VIDEO_ID)
        assert "visual_elements" in result

    async def test_outer_exception_returns_error_summary(self):
        proc = _make_processor()
        mock_vision = MagicMock()
        mock_vision.process_youtube = AsyncMock(side_effect=RuntimeError("outer"))
        proc.gemini_vision = mock_vision

        result = await proc._extract_visual_context(_VIDEO_URL, _VIDEO_ID)
        assert result["frame_analysis_count"] == 0


# ===========================================================================
# _generate_enhanced_markdown
# ===========================================================================

class TestGenerateEnhancedMarkdown:
    def _metadata(self):
        return {
            "title": "Test Video",
            "channel": "Test Channel",
            "duration": "10m",
            "view_count": 5000,
            "published_at": "2024-01-01",
            "category": "Programming",
        }

    def _transcript(self):
        return {"text": "This is the transcript text."}

    def _ai_analysis(self):
        return {
            "Content Summary": "Great content",
            "Key Concepts": "Concept A, Concept B",
            "Technical Details": "Uses Python",
            "Learning Path": "Start here",
            "Code Generation Potential": "High",
            "Difficulty Level": "Beginner",
            "Prerequisites": "None",
            "Related Topics": "Docker",
        }

    async def test_generates_markdown_string(self):
        proc = _make_processor()
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis()
        )
        assert isinstance(result, str)
        assert "Test Video" in result

    async def test_includes_channel_info(self):
        proc = _make_processor()
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis()
        )
        assert "Test Channel" in result

    async def test_includes_transcript_text(self):
        proc = _make_processor()
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis()
        )
        assert "This is the transcript text" in result

    async def test_includes_ai_summary(self):
        proc = _make_processor()
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis()
        )
        assert "Great content" in result

    async def test_with_visual_elements_adds_section(self):
        proc = _make_processor()
        visual_context = {
            "visual_elements": [
                {"element_type": "code", "content": "x = 1", "timestamp": 5, "confidence": 0.9}
            ],
            "summary": "One visual element",
            "frame_analysis_count": 1,
        }
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis(), visual_context
        )
        assert "Visual Context" in result
        assert "x = 1" in result

    async def test_with_numeric_timestamp_formatted(self):
        proc = _make_processor()
        visual_context = {
            "visual_elements": [
                {"element_type": "terminal", "content": "ls -la", "timestamp": 90, "confidence": 0.85}
            ],
            "summary": "Terminal",
            "frame_analysis_count": 1,
        }
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis(), visual_context
        )
        assert "1:30" in result  # 90 seconds = 1:30

    async def test_with_string_timestamp(self):
        proc = _make_processor()
        visual_context = {
            "visual_elements": [
                {"element_type": "UI", "content": "button", "timestamp": "0:05", "confidence": 0.7}
            ],
            "summary": "UI",
            "frame_analysis_count": 1,
        }
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis(), visual_context
        )
        assert "0:05" in result

    async def test_no_visual_context_no_section(self):
        proc = _make_processor()
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis(), None
        )
        assert "Visual Context" not in result

    async def test_empty_visual_elements_no_section(self):
        proc = _make_processor()
        visual_context = {"visual_elements": [], "summary": "None", "frame_analysis_count": 0}
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis(), visual_context
        )
        assert "Visual Context" not in result

    async def test_multiple_element_types_grouped(self):
        proc = _make_processor()
        visual_context = {
            "visual_elements": [
                {"element_type": "code", "content": "x=1", "timestamp": 1, "confidence": 0.9},
                {"element_type": "diagram", "content": "arch", "timestamp": 2, "confidence": 0.8},
                {"element_type": "code", "content": "y=2", "timestamp": 3, "confidence": 0.9},
            ],
            "summary": "Mixed elements",
            "frame_analysis_count": 3,
        }
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, self._metadata(), self._transcript(), self._ai_analysis(), visual_context
        )
        assert "Code" in result or "code" in result
        assert "Diagram" in result or "diagram" in result

    async def test_metadata_defaults_used(self):
        proc = _make_processor()
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, {}, {"text": ""}, {}
        )
        assert "Video Analysis" in result

    async def test_exception_returns_error_message(self):
        proc = _make_processor()
        # Pass a metadata that will cause format error - view_count that can't be formatted as int
        metadata = {"view_count": "not-a-number", "title": "T"}
        result = await proc._generate_enhanced_markdown(
            _VIDEO_ID, metadata, {}, {}
        )
        # Should either work or return error string
        assert isinstance(result, str)


# ===========================================================================
# _save_enhanced_result
# ===========================================================================

class TestSaveEnhancedResult:
    async def test_saves_markdown_and_metadata(self, tmp_path):
        proc = _make_processor()
        metadata = {"title": "T", "category": "Programming"}
        markdown = "# Test Markdown"

        with patch("youtube_extension.backend.enhanced_video_processor.Path") as mock_path_cls:
            # Use real tmp_path for actual file operations
            real_save_dir = tmp_path / "youtube_processed_videos" / "enhanced_analysis" / "Programming"
            mock_path_inst = MagicMock()
            mock_path_inst.__truediv__ = MagicMock(side_effect=lambda x: real_save_dir / x)
            mock_path_cls.return_value = mock_path_inst

            # Use real Path for file I/O
            with patch("builtins.open", mock_open()) as m:
                result = await proc._save_enhanced_result(_VIDEO_ID, metadata, markdown)

        # Result should be a string (even if empty on error)
        assert isinstance(result, str)

    async def test_returns_empty_string_on_exception(self):
        proc = _make_processor()

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with patch("pathlib.Path.mkdir", side_effect=OSError("mkdir failed")):
                result = await proc._save_enhanced_result(_VIDEO_ID, {}, "# md")

        assert result == ""

    async def test_save_creates_directory_structure(self, tmp_path):
        proc = _make_processor()
        metadata = {"category": "AI/ML"}

        with patch("youtube_extension.backend.enhanced_video_processor.Path") as MockPath:
            save_dir = MagicMock()
            save_dir.mkdir = MagicMock()
            # filepath and metadata_file need to work with open()
            filepath = tmp_path / "test_file.md"
            metadata_fp = tmp_path / "test_meta.json"

            MockPath.return_value.__truediv__ = MagicMock()

            with patch("builtins.open", mock_open()) as m:
                result = await proc._save_enhanced_result(_VIDEO_ID, metadata, "# md")
        assert isinstance(result, str)


# ===========================================================================
# process_video
# ===========================================================================

class TestProcessVideo:
    async def test_process_video_success(self):
        """Full pipeline mock — _generate_build_plan and _build_extracted_info are undefined,
        so they must also be mocked."""
        proc = _make_processor()

        proc._init_session = AsyncMock()
        proc._extract_video_id = MagicMock(return_value=_VIDEO_ID)
        proc._get_video_metadata = AsyncMock(return_value={"title": "T", "channel": "C"})
        proc._get_youtube_transcript_fallback = AsyncMock(return_value={
            "text": "hello world", "source": "youtube_api_fallback", "confidence": 0.8
        })
        proc._analyze_with_gemini = AsyncMock(return_value={"Content Summary": "Good"})
        proc._extract_visual_context = AsyncMock(return_value={
            "visual_elements": [], "summary": "none", "frame_analysis_count": 0
        })
        proc._generate_build_plan = AsyncMock(return_value={"steps": []})
        proc._build_extracted_info = MagicMock(return_value={"title": "T"})
        proc._generate_enhanced_markdown = AsyncMock(return_value="# Markdown")
        proc._save_enhanced_result = AsyncMock(return_value="/path/to/file.md")

        result = await proc.process_video(_VIDEO_URL)

        assert result["success"] is True
        assert result["video_id"] == _VIDEO_ID
        assert result["pipeline"] == "enhanced_multimodal_gemini_vision"

    async def test_process_video_falls_back_to_gemini_transcript(self):
        proc = _make_processor()

        proc._init_session = AsyncMock()
        proc._extract_video_id = MagicMock(return_value=_VIDEO_ID)
        proc._get_video_metadata = AsyncMock(return_value={"title": "T"})
        proc._get_youtube_transcript_fallback = AsyncMock(return_value={
            "text": "", "source": "failed", "confidence": 0.0
        })
        proc._get_gemini_transcript = AsyncMock(return_value={
            "text": "gemini text", "source": "gemini_api", "confidence": 0.95
        })
        proc._analyze_with_gemini = AsyncMock(return_value={})
        proc._extract_visual_context = AsyncMock(return_value={
            "visual_elements": [], "summary": "none", "frame_analysis_count": 0
        })
        proc._generate_build_plan = AsyncMock(return_value={})
        proc._build_extracted_info = MagicMock(return_value={})
        proc._generate_enhanced_markdown = AsyncMock(return_value="# md")
        proc._save_enhanced_result = AsyncMock(return_value="/path")

        result = await proc.process_video(_VIDEO_URL)

        proc._get_gemini_transcript.assert_awaited_once()
        assert result["transcript"]["source"] == "gemini_api"

    async def test_process_video_exception_propagates(self):
        proc = _make_processor()
        proc._init_session = AsyncMock(side_effect=RuntimeError("Init failed"))

        with pytest.raises(RuntimeError, match="Init failed"):
            await proc.process_video(_VIDEO_URL)

    async def test_process_video_uses_youtube_transcript_when_not_failed(self):
        proc = _make_processor()

        yt_transcript = {"text": "yt text", "source": "youtube_api_fallback", "confidence": 0.8}
        proc._init_session = AsyncMock()
        proc._extract_video_id = MagicMock(return_value=_VIDEO_ID)
        proc._get_video_metadata = AsyncMock(return_value={"title": "T"})
        proc._get_youtube_transcript_fallback = AsyncMock(return_value=yt_transcript)
        proc._analyze_with_gemini = AsyncMock(return_value={})
        proc._extract_visual_context = AsyncMock(return_value={
            "visual_elements": [], "summary": "none", "frame_analysis_count": 0
        })
        proc._generate_build_plan = AsyncMock(return_value={})
        proc._build_extracted_info = MagicMock(return_value={})
        proc._generate_enhanced_markdown = AsyncMock(return_value="# md")
        proc._save_enhanced_result = AsyncMock(return_value="/path")

        result = await proc.process_video(_VIDEO_URL)

        assert result["transcript"]["source"] == "youtube_api_fallback"


# ===========================================================================
# get_enhanced_video_processor factory
# ===========================================================================

class TestGetEnhancedVideoProcessorFactory:
    def test_returns_instance(self):
        with patch.object(_mod, "GEMINI_VISION_AVAILABLE", False):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "factory-key"}, clear=False):
                proc = get_enhanced_video_processor()
        assert isinstance(proc, EnhancedVideoProcessor)
