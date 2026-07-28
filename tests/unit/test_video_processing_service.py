"""Unit tests for backend/services/video_processing_service.py.

Covers VideoProcessingService: all methods, branches, and error paths.
All external dependencies (processors, code generators, deployment managers, langextract)
are fully mocked.
"""

from __future__ import annotations

import asyncio
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from youtube_extension.backend.services.video_processing_service import (
    DEPLOYMENT_TARGET_ALIASES,
    VideoProcessingService,
    resolve_deployment_target,
)

_VIDEO_URL = "https://www.youtube.com/watch?v=auJzb1D-fag"
_VIDEO_ID = "auJzb1D-fag"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(
    *,
    processor=None,
    cache=None,
    use_langextract: bool = False,
):
    """Create a VideoProcessingService with mocked dependencies."""
    factory = MagicMock()
    if processor is not None:
        factory.create_processor.return_value = processor
    else:
        factory.create_processor.return_value = MagicMock()

    cache_svc = cache if cache is not None else MagicMock()

    svc = VideoProcessingService(
        video_processor_factory=factory,
        cache_service=cache_svc,
    )
    # Override env-driven flag for deterministic tests
    svc.use_langextract_fallback = use_langextract
    return svc


def _make_processor_with_process_video(result: dict):
    """Return a mock processor whose process_video is an AsyncMock."""
    proc = MagicMock()
    proc.process_video = AsyncMock(return_value=result)
    proc.get_cached_result = MagicMock(return_value=None)
    proc.close = AsyncMock()
    return proc


def _success_result(video_id=_VIDEO_ID) -> dict:
    return {
        "video_id": video_id,
        "success": True,
        "metadata": {"title": "Test Video", "channel": "Test Channel", "category": "Programming"},
        "transcript": {"text": "hello world", "source": "youtube_api_fallback", "segments": []},
        "ai_analysis": {"Content Summary": "Good", "actions": []},
        "markdown_analysis": "# Test Markdown",
        "save_path": "/path/to/file.md",
        "pipeline": "enhanced",
        "processing_time": "1.23",
    }


def _make_cache_service(cached_result=None, video_id=_VIDEO_ID):
    cache = MagicMock()
    cache.get_cached_result.return_value = cached_result
    cache.extract_video_id.return_value = video_id
    return cache


# ===========================================================================
# resolve_deployment_target
# ===========================================================================

class TestResolveDeploymentTarget:
    def test_none_target_resolves_to_vercel(self):
        r = resolve_deployment_target(None)
        assert r["resolved"] == "vercel"
        assert r["requested"] == "vercel"

    def test_empty_string_resolves_to_vercel(self):
        r = resolve_deployment_target("")
        assert r["resolved"] == "vercel"

    def test_vercel_resolves_to_vercel(self):
        r = resolve_deployment_target("vercel")
        assert r["resolved"] == "vercel"
        assert r["alias_applied"] is False

    def test_claude_alias_resolves_to_vercel(self):
        r = resolve_deployment_target("claude")
        assert r["resolved"] == "vercel"
        assert r["alias_applied"] is True

    def test_github_resolves_to_github(self):
        r = resolve_deployment_target("github")
        assert r["resolved"] == "github"

    def test_github_pages_resolves_to_github(self):
        r = resolve_deployment_target("github_pages")
        assert r["resolved"] == "github"

    def test_netlify_resolves_to_netlify(self):
        r = resolve_deployment_target("netlify")
        assert r["resolved"] == "netlify"

    def test_aws_resolves_to_aws(self):
        r = resolve_deployment_target("aws")
        assert r["resolved"] == "aws"

    def test_unknown_target_resolves_to_vercel(self):
        r = resolve_deployment_target("unknown-platform")
        assert r["resolved"] == "vercel"
        assert r["alias_applied"] is True  # normalized != resolved

    def test_case_insensitive(self):
        r = resolve_deployment_target("VERCEL")
        assert r["resolved"] == "vercel"

    def test_strips_whitespace(self):
        r = resolve_deployment_target("  vercel  ")
        assert r["resolved"] == "vercel"

    def test_lindy_ai_resolves_to_vercel(self):
        r = resolve_deployment_target("lindy.ai")
        assert r["resolved"] == "vercel"

    def test_genspark_resolves_to_vercel(self):
        r = resolve_deployment_target("genspark")
        assert r["resolved"] == "vercel"

    def test_cursor_resolves_to_vercel(self):
        r = resolve_deployment_target("cursor")
        assert r["resolved"] == "vercel"

    def test_codex_resolves_to_vercel(self):
        r = resolve_deployment_target("codex")
        assert r["resolved"] == "vercel"


# ===========================================================================
# DEPLOYMENT_TARGET_ALIASES dict
# ===========================================================================

class TestDeploymentTargetAliases:
    def test_dict_has_expected_keys(self):
        expected = {"vercel", "claude", "openai", "gemini", "lindy", "lindy.ai",
                    "manus", "genspark", "genspark.ai", "codex", "cursor",
                    "github", "github_pages", "netlify", "aws", "heroku"}
        assert set(DEPLOYMENT_TARGET_ALIASES.keys()) == expected

    def test_heroku_maps_to_vercel(self):
        assert DEPLOYMENT_TARGET_ALIASES["heroku"] == "vercel"


# ===========================================================================
# VideoProcessingService.__init__
# ===========================================================================

class TestVideoProcessingServiceInit:
    def test_stores_factory_and_cache(self):
        factory = MagicMock()
        cache = MagicMock()
        svc = VideoProcessingService(factory, cache)
        assert svc.video_processor_factory is factory
        assert svc.cache_service is cache

    def test_singleton_starts_none(self):
        svc = _make_service()
        assert svc._processor_singleton is None

    def test_use_langextract_fallback_default_false(self):
        with patch.dict("os.environ", {"USE_LANGEXTRACT_FALLBACK": "false"}, clear=False):
            svc = _make_service()
            svc.use_langextract_fallback = svc.use_langextract_fallback  # re-read from env
        # re-create to read env properly
        svc2 = VideoProcessingService(MagicMock(), MagicMock())
        assert isinstance(svc2.use_langextract_fallback, bool)

    def test_use_langextract_fallback_from_env_true(self):
        with patch.dict("os.environ", {"USE_LANGEXTRACT_FALLBACK": "true"}, clear=False):
            svc = VideoProcessingService(MagicMock(), MagicMock())
        assert svc.use_langextract_fallback is True

    def test_use_langextract_fallback_from_env_1(self):
        with patch.dict("os.environ", {"USE_LANGEXTRACT_FALLBACK": "1"}, clear=False):
            svc = VideoProcessingService(MagicMock(), MagicMock())
        assert svc.use_langextract_fallback is True

    def test_use_langextract_fallback_from_env_yes(self):
        with patch.dict("os.environ", {"USE_LANGEXTRACT_FALLBACK": "yes"}, clear=False):
            svc = VideoProcessingService(MagicMock(), MagicMock())
        assert svc.use_langextract_fallback is True


# ===========================================================================
# get_video_processor
# ===========================================================================

class TestGetVideoProcessor:
    def test_returns_processor_on_first_call(self):
        mock_proc = MagicMock()
        svc = _make_service(processor=mock_proc)
        result = svc.get_video_processor()
        assert result is mock_proc

    def test_returns_same_singleton_on_second_call(self):
        mock_proc = MagicMock()
        svc = _make_service(processor=mock_proc)
        p1 = svc.get_video_processor()
        p2 = svc.get_video_processor()
        assert p1 is p2
        # Factory only called once
        svc.video_processor_factory.create_processor.assert_called_once()

    def test_returns_singleton_if_already_set(self):
        svc = _make_service()
        sentinel = MagicMock()
        svc._processor_singleton = sentinel
        result = svc.get_video_processor()
        assert result is sentinel
        svc.video_processor_factory.create_processor.assert_not_called()

    def test_returns_none_on_exception(self):
        svc = _make_service()
        svc.video_processor_factory.create_processor.side_effect = RuntimeError("oops")
        result = svc.get_video_processor()
        assert result is None


# ===========================================================================
# _normalize_result
# ===========================================================================

class TestNormalizeResult:
    def test_basic_normalization(self):
        svc = _make_service()
        raw = _success_result()
        result = svc._normalize_result(_VIDEO_URL, raw)
        assert "video_data" in result
        assert "actions" in result
        assert "transcript" in result
        assert "quality_score" in result
        assert "processing_time" in result

    def test_non_dict_result_wrapped(self):
        svc = _make_service()
        result = svc._normalize_result(_VIDEO_URL, "not a dict")
        assert isinstance(result, dict)

    def test_video_id_from_result(self):
        svc = _make_service()
        cache = _make_cache_service(video_id=_VIDEO_ID)
        svc.cache_service = cache
        raw = {"video_id": _VIDEO_ID, "success": True}
        result = svc._normalize_result(_VIDEO_URL, raw)
        assert result is not None

    def test_video_id_fallback_to_cache_service(self):
        cache = _make_cache_service(video_id=_VIDEO_ID)
        svc = _make_service(cache=cache)
        raw = {"success": True}
        result = svc._normalize_result(_VIDEO_URL, raw)
        cache.extract_video_id.assert_called_once_with(_VIDEO_URL)

    def test_video_data_built_from_metadata(self):
        svc = _make_service()
        raw = {
            "video_id": _VIDEO_ID,
            "metadata": {"title": "My Title", "channel": "My Channel", "duration": "5m"},
        }
        # yt_dlp not available → fallback
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["video_data"]["title"] == "My Title"

    def test_actions_from_ai_analysis(self):
        svc = _make_service()
        raw = {
            "video_id": _VIDEO_ID,
            "ai_analysis": {"actions": [{"type": "run", "command": "npm start"}]},
        }
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert len(result["actions"]) == 1

    def test_actions_empty_when_none(self):
        svc = _make_service()
        raw = {"video_id": _VIDEO_ID}
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["actions"] == []

    def test_transcript_from_dict_uses_segments(self):
        svc = _make_service()
        raw = {
            "video_id": _VIDEO_ID,
            "transcript": {
                "segments": [{"text": "hello", "start": 0, "duration": 1}],
                "text": "hello",
            },
        }
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert len(result["transcript"]) == 1

    def test_transcript_list_used_directly(self):
        svc = _make_service()
        segs = [{"text": "a", "start": 0, "duration": 1}, {"text": "b", "start": 1, "duration": 1}]
        raw = {"video_id": _VIDEO_ID, "transcript": segs}
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["transcript"] == segs

    def test_quality_score_high_when_actions_and_transcript(self):
        svc = _make_service()
        raw = {
            "video_id": _VIDEO_ID,
            "actions": [{"type": "run"}],
            "transcript": [{"text": "a"}, {"text": "b"}],
        }
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["quality_score"] == 0.9

    def test_quality_score_medium_when_only_actions(self):
        svc = _make_service()
        raw = {
            "video_id": _VIDEO_ID,
            "actions": [{"type": "run"}],
            "transcript": [],
        }
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["quality_score"] == 0.7

    def test_quality_score_medium_when_only_transcript(self):
        svc = _make_service()
        raw = {
            "video_id": _VIDEO_ID,
            "actions": [],
            "transcript": [{"text": "a"}],
        }
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["quality_score"] == 0.7

    def test_quality_score_low_when_empty(self):
        svc = _make_service()
        raw = {"video_id": _VIDEO_ID, "actions": [], "transcript": []}
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["quality_score"] == 0.2

    def test_explicit_quality_score_preserved(self):
        svc = _make_service()
        raw = {"video_id": _VIDEO_ID, "quality_score": 0.55}
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["quality_score"] == 0.55

    def test_extra_fields_carried_forward(self):
        svc = _make_service()
        raw = {"video_id": _VIDEO_ID, "cached": True, "pipeline": "enhanced"}
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["cached"] is True
        assert result["pipeline"] == "enhanced"

    def test_video_data_provided_used_directly(self):
        svc = _make_service()
        vdata = {"id": _VIDEO_ID, "title": "Direct", "channel": "C"}
        raw = {"video_id": _VIDEO_ID, "video_data": vdata}
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["video_data"] is vdata

    def test_yt_dlp_used_when_available(self):
        svc = _make_service()
        mock_ydl_info = {"id": _VIDEO_ID, "title": "yt-dlp title"}
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = mock_ydl_info
        mock_ydl_cm = MagicMock()
        mock_ydl_cm.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_ydl_cm.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl_cm

        raw = {"video_id": _VIDEO_ID, "metadata": {}}
        with patch.dict("sys.modules", {"yt_dlp": mock_yt_dlp}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["video_data"]["id"] == _VIDEO_ID

    def test_cache_service_extract_video_id_exception_falls_back(self):
        cache = MagicMock()
        cache.extract_video_id.side_effect = Exception("id error")
        svc = _make_service(cache=cache)
        raw = {}
        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = svc._normalize_result(_VIDEO_URL, raw)
        assert result["video_data"] is not None


# ===========================================================================
# process_video_for_markdown
# ===========================================================================

class TestProcessVideoForMarkdown:
    async def test_returns_cached_result_when_available(self):
        cached = {
            "video_id": _VIDEO_ID,
            "metadata": {"title": "Cached"},
            "markdown_content": "# Cached",
            "save_path": "/cache/path",
        }
        cache = _make_cache_service(cached_result=cached)
        svc = _make_service(cache=cache)

        result = await svc.process_video_for_markdown(_VIDEO_URL)

        assert result["cached"] is True
        assert result["video_id"] == _VIDEO_ID
        assert result["status"] == "success"

    async def test_strips_frontmatter_from_cached_content(self):
        cached = {
            "video_id": _VIDEO_ID,
            "metadata": {},
            "markdown_content": "---\ntitle: T\n---\n# Real Content",
            "save_path": "",
        }
        cache = _make_cache_service(cached_result=cached)
        svc = _make_service(cache=cache)

        result = await svc.process_video_for_markdown(_VIDEO_URL)

        assert result["markdown_content"] == "# Real Content"

    async def test_cached_no_frontmatter_unchanged(self):
        cached = {
            "video_id": _VIDEO_ID,
            "metadata": {},
            "markdown_content": "# Already Clean",
            "save_path": "",
        }
        cache = _make_cache_service(cached_result=cached)
        svc = _make_service(cache=cache)

        result = await svc.process_video_for_markdown(_VIDEO_URL)

        assert result["markdown_content"] == "# Already Clean"

    async def test_force_regenerate_skips_cache(self):
        cached = {
            "video_id": _VIDEO_ID,
            "metadata": {},
            "markdown_content": "# Cached",
            "save_path": "",
        }
        cache = _make_cache_service(cached_result=cached)
        processor = _make_processor_with_process_video(_success_result())
        svc = _make_service(processor=processor, cache=cache)

        result = await svc.process_video_for_markdown(_VIDEO_URL, force_regenerate=True)

        cache.get_cached_result.assert_not_called()
        assert result["cached"] is False

    async def test_processes_fresh_when_no_cache(self):
        cache = _make_cache_service(cached_result=None)
        processor = _make_processor_with_process_video(_success_result())
        svc = _make_service(processor=processor, cache=cache)

        result = await svc.process_video_for_markdown(_VIDEO_URL)

        assert result["status"] == "success"
        assert result["cached"] is False

    async def test_strips_frontmatter_from_fresh_content(self):
        raw = _success_result()
        raw["markdown_analysis"] = "---\ntitle: T\n---\n# Content"
        cache = _make_cache_service(cached_result=None)
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor, cache=cache)

        result = await svc.process_video_for_markdown(_VIDEO_URL)

        assert result["markdown_content"] == "# Content"

    async def test_raises_value_error_when_no_processor(self):
        cache = _make_cache_service(cached_result=None)
        svc = _make_service(cache=cache)
        svc.video_processor_factory.create_processor.side_effect = RuntimeError("factory error")

        with pytest.raises(ValueError, match="not available"):
            await svc.process_video_for_markdown(_VIDEO_URL)

    async def test_raises_when_result_not_successful(self):
        cache = _make_cache_service(cached_result=None)
        processor = _make_processor_with_process_video({"success": False, "error": "fail"})
        svc = _make_service(processor=processor, cache=cache)

        with pytest.raises(ValueError, match="processing failed"):
            await svc.process_video_for_markdown(_VIDEO_URL)

    async def test_langextract_fallback_on_failed_result(self):
        cache = _make_cache_service(cached_result=None)
        processor = _make_processor_with_process_video({"success": False})
        svc = _make_service(processor=processor, cache=cache, use_langextract=True)

        fallback_result = {
            "video_id": _VIDEO_ID,
            "video_url": _VIDEO_URL,
            "metadata": {},
            "markdown_content": "# Fallback",
            "cached": False,
            "save_path": "",
            "processing_time": "now",
            "status": "success",
        }
        svc._try_langextract_fallback = AsyncMock(return_value=fallback_result)

        result = await svc.process_video_for_markdown(_VIDEO_URL)

        assert result["markdown_content"] == "# Fallback"
        svc._try_langextract_fallback.assert_awaited_once_with(_VIDEO_URL)

    async def test_langextract_fallback_on_exception(self):
        cache = _make_cache_service(cached_result=None)
        processor = MagicMock()
        processor.process_video = AsyncMock(side_effect=RuntimeError("network error"))
        processor.get_cached_result = MagicMock(return_value=None)
        svc = _make_service(processor=processor, cache=cache, use_langextract=True)

        fallback_result = {
            "video_id": _VIDEO_ID,
            "video_url": _VIDEO_URL,
            "metadata": {},
            "markdown_content": "# Fallback",
            "cached": False,
            "save_path": "",
            "processing_time": "now",
            "status": "success",
        }
        svc._try_langextract_fallback = AsyncMock(return_value=fallback_result)

        result = await svc.process_video_for_markdown(_VIDEO_URL)

        assert result["markdown_content"] == "# Fallback"

    async def test_exception_raised_when_langextract_disabled(self):
        cache = _make_cache_service(cached_result=None)
        processor = MagicMock()
        processor.process_video = AsyncMock(side_effect=RuntimeError("crash"))
        processor.get_cached_result = MagicMock(return_value=None)
        svc = _make_service(processor=processor, cache=cache, use_langextract=False)

        with pytest.raises(RuntimeError, match="crash"):
            await svc.process_video_for_markdown(_VIDEO_URL)

    async def test_langextract_returns_none_reraises(self):
        cache = _make_cache_service(cached_result=None)
        processor = MagicMock()
        processor.process_video = AsyncMock(side_effect=RuntimeError("crash"))
        processor.get_cached_result = MagicMock(return_value=None)
        svc = _make_service(processor=processor, cache=cache, use_langextract=True)
        svc._try_langextract_fallback = AsyncMock(return_value=None)

        with pytest.raises(RuntimeError, match="crash"):
            await svc.process_video_for_markdown(_VIDEO_URL)


# ===========================================================================
# process_video_basic
# ===========================================================================

class TestProcessVideoBasic:
    async def test_basic_processing_success(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = await svc.process_video_basic(_VIDEO_URL)

        assert "video_data" in result
        assert "actions" in result
        assert "transcript" in result

    async def test_with_options_dict(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = await svc.process_video_basic(_VIDEO_URL, options={"extra": "value"})

        assert "video_data" in result

    async def test_processor_level_cache_used(self):
        cached_raw = _success_result()
        processor = MagicMock()
        processor.get_cached_result = MagicMock(return_value=cached_raw)
        processor.process_video = AsyncMock()
        svc = _make_service(processor=processor)

        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = await svc.process_video_basic(_VIDEO_URL)

        # process_video should NOT be called when cache hit
        processor.process_video.assert_not_called()
        assert "video_data" in result

    async def test_processor_level_cache_none_skipped(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        processor.get_cached_result = MagicMock(return_value=None)
        svc = _make_service(processor=processor)

        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = await svc.process_video_basic(_VIDEO_URL)

        processor.process_video.assert_awaited_once()

    async def test_raises_value_error_when_no_processor(self):
        svc = _make_service()
        svc.video_processor_factory.create_processor.side_effect = RuntimeError("broken")

        with pytest.raises(ValueError, match="not available"):
            await svc.process_video_basic(_VIDEO_URL)

    async def test_timeout_error_propagated(self):
        processor = MagicMock()
        processor.get_cached_result = MagicMock(return_value=None)
        processor.process_video = AsyncMock(side_effect=asyncio.TimeoutError())
        svc = _make_service(processor=processor)

        with pytest.raises(asyncio.TimeoutError):
            await svc.process_video_basic(_VIDEO_URL)

    async def test_value_error_propagated(self):
        processor = MagicMock()
        processor.get_cached_result = MagicMock(return_value=None)
        processor.process_video = AsyncMock(side_effect=ValueError("bad input"))
        svc = _make_service(processor=processor)

        with pytest.raises(ValueError, match="bad input"):
            await svc.process_video_basic(_VIDEO_URL)

    async def test_generic_exception_propagated(self):
        processor = MagicMock()
        processor.get_cached_result = MagicMock(return_value=None)
        processor.process_video = AsyncMock(side_effect=RuntimeError("generic"))
        svc = _make_service(processor=processor)

        with pytest.raises(RuntimeError, match="generic"):
            await svc.process_video_basic(_VIDEO_URL)

    async def test_processing_time_added_when_missing(self):
        raw = _success_result()
        # Remove processing_time so it must be derived
        raw.pop("processing_time", None)
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = await svc.process_video_basic(_VIDEO_URL)

        assert "processing_time" in result

    async def test_get_cached_result_exception_continues(self):
        """If get_cached_result raises, processing should continue normally."""
        raw = _success_result()
        processor = MagicMock()
        processor.get_cached_result = MagicMock(side_effect=Exception("cache error"))
        processor.process_video = AsyncMock(return_value=raw)
        svc = _make_service(processor=processor)

        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = await svc.process_video_basic(_VIDEO_URL)

        processor.process_video.assert_awaited_once()
        assert "video_data" in result

    async def test_processor_without_get_cached_result(self):
        """Processor without get_cached_result attribute should work fine."""
        raw = _success_result()
        processor = MagicMock(spec=["process_video", "close"])
        processor.process_video = AsyncMock(return_value=raw)
        svc = _make_service(processor=processor)

        with patch.dict("sys.modules", {"yt_dlp": None}):
            result = await svc.process_video_basic(_VIDEO_URL)

        assert "video_data" in result


# ===========================================================================
# process_video_to_software
# ===========================================================================

class TestProcessVideoToSoftware:
    def _make_generation_result(self):
        return {
            "project_type": "my-project",
            "framework": "nextjs",
            "files_created": ["index.js"],
            "entry_point": "index.js",
            "build_command": "npm run build",
            "start_command": "npm start",
            "project_path": "/tmp/project",
        }

    def _make_deployment_result(self, status="success", target="vercel"):
        return {
            "status": status,
            "deployment_id": "dep-123",
            "urls": {target: f"https://my-app.{target}.app"},
            "deployments": {
                "github": {"url": "https://github.com/user/repo"},
            },
            "errors": [],
        }

    async def test_pipeline_not_available_raises(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        with patch.dict("sys.modules", {
            "youtube_extension.backend.code_generator": None,
            "youtube_extension.backend.deployment_manager": None,
        }):
            with pytest.raises(ValueError, match="pipeline not available"):
                await svc.process_video_to_software(_VIDEO_URL)

    async def test_success_with_success_flag(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        gen_result = self._make_generation_result()
        dep_result = self._make_deployment_result()

        mock_generator = MagicMock()
        mock_generator.generate_project = AsyncMock(return_value=gen_result)
        mock_deployment = MagicMock()
        mock_deployment.deploy_project = AsyncMock(return_value=dep_result)

        mock_code_gen_mod = MagicMock()
        mock_code_gen_mod.get_code_generator = MagicMock(return_value=mock_generator)
        mock_deploy_mod = MagicMock()
        mock_deploy_mod.get_deployment_manager = MagicMock(return_value=mock_deployment)

        with patch.dict("sys.modules", {
            "youtube_extension.backend.code_generator": mock_code_gen_mod,
            "youtube_extension.backend.deployment_manager": mock_deploy_mod,
        }):
            result = await svc.process_video_to_software(_VIDEO_URL, project_type="web", deployment_target="vercel")

        assert result["status"] == "success"
        assert result["build_status"] == "completed"
        assert "vercel" in result["live_url"]

    async def test_video_analysis_status_success_branch(self):
        """Test branch where result has 'status' == 'success' instead of 'success' flag."""
        raw = {
            "status": "success",
            "extracted_info": {"title": "My Project"},
            "ai_analysis": {},
            "metadata": {"title": "Test"},
            "video_id": _VIDEO_ID,
            "processing_pipeline": [],
        }
        processor = MagicMock()
        processor.get_cached_result = MagicMock(return_value=None)
        processor.process_video = AsyncMock(return_value=raw)
        svc = _make_service(processor=processor)

        gen_result = self._make_generation_result()
        dep_result = self._make_deployment_result()

        mock_generator = MagicMock()
        mock_generator.generate_project = AsyncMock(return_value=gen_result)
        mock_deployment = MagicMock()
        mock_deployment.deploy_project = AsyncMock(return_value=dep_result)

        mock_code_gen_mod = MagicMock()
        mock_code_gen_mod.get_code_generator = MagicMock(return_value=mock_generator)
        mock_deploy_mod = MagicMock()
        mock_deploy_mod.get_deployment_manager = MagicMock(return_value=mock_deployment)

        with patch.dict("sys.modules", {
            "youtube_extension.backend.code_generator": mock_code_gen_mod,
            "youtube_extension.backend.deployment_manager": mock_deploy_mod,
        }):
            result = await svc.process_video_to_software(_VIDEO_URL)

        assert result["status"] == "success"

    async def test_failed_video_analysis_raises(self):
        raw = {"error": "Analysis failed", "video_id": _VIDEO_ID}
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        mock_code_gen_mod = MagicMock()
        mock_code_gen_mod.get_code_generator = MagicMock()
        mock_deploy_mod = MagicMock()
        mock_deploy_mod.get_deployment_manager = MagicMock()

        with patch.dict("sys.modules", {
            "youtube_extension.backend.code_generator": mock_code_gen_mod,
            "youtube_extension.backend.deployment_manager": mock_deploy_mod,
        }):
            with pytest.raises(ValueError, match="Video processing failed"):
                await svc.process_video_to_software(_VIDEO_URL)

    async def test_fallback_to_vercel_when_primary_url_missing(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        gen_result = self._make_generation_result()
        dep_result = {
            "status": "success",
            "deployment_id": "dep-456",
            "urls": {"vercel": "https://fallback.vercel.app"},  # target not in urls
            "deployments": {"github": {"url": "https://github.com/x"}},
            "errors": [],
        }

        mock_generator = MagicMock()
        mock_generator.generate_project = AsyncMock(return_value=gen_result)
        mock_deployment = MagicMock()
        mock_deployment.deploy_project = AsyncMock(return_value=dep_result)

        mock_code_gen_mod = MagicMock()
        mock_code_gen_mod.get_code_generator = MagicMock(return_value=mock_generator)
        mock_deploy_mod = MagicMock()
        mock_deploy_mod.get_deployment_manager = MagicMock(return_value=mock_deployment)

        with patch.dict("sys.modules", {
            "youtube_extension.backend.code_generator": mock_code_gen_mod,
            "youtube_extension.backend.deployment_manager": mock_deploy_mod,
        }):
            result = await svc.process_video_to_software(
                _VIDEO_URL, project_type="web", deployment_target="aws"
            )

        # aws not in urls, falls back to vercel url
        assert result["build_status"] == "completed"
        assert "vercel" in result["live_url"]

    async def test_build_failed_when_no_urls(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        gen_result = self._make_generation_result()
        dep_result = {
            "status": "failed",
            "deployment_id": "dep-err",
            "urls": {},
            "deployments": {},
            "errors": ["Deploy failed"],
        }

        mock_generator = MagicMock()
        mock_generator.generate_project = AsyncMock(return_value=gen_result)
        mock_deployment = MagicMock()
        mock_deployment.deploy_project = AsyncMock(return_value=dep_result)

        mock_code_gen_mod = MagicMock()
        mock_code_gen_mod.get_code_generator = MagicMock(return_value=mock_generator)
        mock_deploy_mod = MagicMock()
        mock_deploy_mod.get_deployment_manager = MagicMock(return_value=mock_deployment)

        with patch.dict("sys.modules", {
            "youtube_extension.backend.code_generator": mock_code_gen_mod,
            "youtube_extension.backend.deployment_manager": mock_deploy_mod,
        }):
            result = await svc.process_video_to_software(
                _VIDEO_URL, project_type="web", deployment_target="vercel"
            )

        assert result["build_status"] == "failed"
        assert result["live_url"] == ""

    async def test_exception_propagated(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        mock_generator = MagicMock()
        mock_generator.generate_project = AsyncMock(side_effect=RuntimeError("gen error"))

        mock_code_gen_mod = MagicMock()
        mock_code_gen_mod.get_code_generator = MagicMock(return_value=mock_generator)
        mock_deploy_mod = MagicMock()
        mock_deploy_mod.get_deployment_manager = MagicMock()

        with patch.dict("sys.modules", {
            "youtube_extension.backend.code_generator": mock_code_gen_mod,
            "youtube_extension.backend.deployment_manager": mock_deploy_mod,
        }):
            with pytest.raises(RuntimeError, match="gen error"):
                await svc.process_video_to_software(_VIDEO_URL)

    async def test_features_included_in_result(self):
        raw = _success_result()
        processor = _make_processor_with_process_video(raw)
        svc = _make_service(processor=processor)

        features = ["auth", "payments"]
        gen_result = self._make_generation_result()
        dep_result = self._make_deployment_result()

        mock_generator = MagicMock()
        mock_generator.generate_project = AsyncMock(return_value=gen_result)
        mock_deployment = MagicMock()
        mock_deployment.deploy_project = AsyncMock(return_value=dep_result)

        mock_code_gen_mod = MagicMock()
        mock_code_gen_mod.get_code_generator = MagicMock(return_value=mock_generator)
        mock_deploy_mod = MagicMock()
        mock_deploy_mod.get_deployment_manager = MagicMock(return_value=mock_deployment)

        with patch.dict("sys.modules", {
            "youtube_extension.backend.code_generator": mock_code_gen_mod,
            "youtube_extension.backend.deployment_manager": mock_deploy_mod,
        }):
            result = await svc.process_video_to_software(_VIDEO_URL, features=features)

        assert "auth" in result["features_implemented"]
        assert "payments" in result["features_implemented"]
        assert "uvai_generated" in result["features_implemented"]


# ===========================================================================
# _try_langextract_fallback
# ===========================================================================

class TestTryLangextractFallback:
    async def test_returns_none_when_server_file_missing(self):
        svc = _make_service()

        env = {"LANGEXTRACT_MCP_SERVER": "/nonexistent/langextract_mcp_server.py"}
        with patch.dict("os.environ", env), \
                patch("subprocess.run") as mock_run:
            result = await svc._try_langextract_fallback(_VIDEO_URL)

        assert result is None
        mock_run.assert_not_called()

    async def test_returns_none_on_non_zero_returncode(self):
        svc = _make_service()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = b"error message"

        with patch("subprocess.run", return_value=mock_proc):
            result = await svc._try_langextract_fallback(_VIDEO_URL)

        assert result is None

    async def test_returns_none_when_result_has_error(self):
        svc = _make_service()
        output = json.dumps({"result": {"error": "extraction failed"}}).encode()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = output

        with patch("subprocess.run", return_value=mock_proc):
            result = await svc._try_langextract_fallback(_VIDEO_URL)

        assert result is None

    async def test_returns_none_when_empty_text(self):
        svc = _make_service()
        output = json.dumps({"result": {"text": ""}}).encode()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = output

        with patch("subprocess.run", return_value=mock_proc):
            result = await svc._try_langextract_fallback(_VIDEO_URL)

        assert result is None

    async def test_returns_dict_on_success(self):
        cache = _make_cache_service(video_id=_VIDEO_ID)
        svc = _make_service(cache=cache)

        output_text = "This is extracted text from the video"
        output = json.dumps({"result": {"text": output_text}}).encode()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = output + b"\n"

        with patch("subprocess.run", return_value=mock_proc):
            result = await svc._try_langextract_fallback(_VIDEO_URL)

        assert result is not None
        assert result["status"] == "success"
        assert "Extracted Content" in result["markdown_content"]
        assert result["video_id"] == _VIDEO_ID

    async def test_returns_none_on_subprocess_exception(self):
        svc = _make_service()

        with patch("subprocess.run", side_effect=Exception("subprocess crash")):
            result = await svc._try_langextract_fallback(_VIDEO_URL)

        assert result is None

    async def test_text_truncated_to_4000(self):
        cache = _make_cache_service(video_id=_VIDEO_ID)
        svc = _make_service(cache=cache)

        long_text = "x" * 5000
        output = json.dumps({"result": {"text": long_text}}).encode()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = output + b"\n"

        with patch("subprocess.run", return_value=mock_proc):
            result = await svc._try_langextract_fallback(_VIDEO_URL)

        assert len(result["markdown_content"]) <= 4050  # some overhead for heading


# ===========================================================================
# cleanup
# ===========================================================================

class TestCleanup:
    async def test_cleanup_calls_processor_close(self):
        svc = _make_service()
        mock_proc = MagicMock()
        mock_proc.close = AsyncMock()
        svc._processor_singleton = mock_proc

        await svc.cleanup()

        mock_proc.close.assert_awaited_once()

    async def test_cleanup_with_no_singleton(self):
        svc = _make_service()
        assert svc._processor_singleton is None
        # Should not raise
        await svc.cleanup()

    async def test_cleanup_with_processor_without_close(self):
        svc = _make_service()
        mock_proc = MagicMock(spec=["process_video"])  # No close method
        svc._processor_singleton = mock_proc
        # Should not raise
        await svc.cleanup()

    async def test_cleanup_exception_does_not_propagate(self):
        svc = _make_service()
        mock_proc = MagicMock()
        mock_proc.close = AsyncMock(side_effect=RuntimeError("close error"))
        svc._processor_singleton = mock_proc
        # Should not raise
        await svc.cleanup()
