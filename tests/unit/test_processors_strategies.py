"""Unit tests for processors/strategies.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

import youtube_extension.processors.strategies as _mod
from youtube_extension.processors.strategies import (
    EnhancedStrategy,
    OptimizedStrategy,
    ParallelStrategy,
    ProcessingStage,
    ProcessorStrategy,
    TranscriptSegment,
    VideoContent,
    VideoMetadata,
    VideoSource,
    _cache,
    _processor_strategies,
    cache_get,
    cache_set,
    get_strategy,
    register_strategy,
)

_VALID_URL = "https://www.youtube.com/watch?v=auJzb1D-fag"
_VALID_ID = "auJzb1D-fag"


@pytest.fixture(autouse=True)
def _disable_external_strategy_clients(monkeypatch):
    """Pure strategy tests must not initialize Google clients or require ADC."""
    monkeypatch.setattr(_mod, "HAS_VIDEO_DEPS", False)
    monkeypatch.setattr(_mod, "HAS_AI_DEPS", False)


# ===========================================================================
# cache_get / cache_set
# ===========================================================================


class TestCacheFunctions:
    async def test_get_returns_none_on_miss(self):
        result = await cache_get("__no_such_key__")
        assert result is None

    async def test_set_then_get(self):
        await cache_set("tc_key", {"data": 42})
        result = await cache_get("tc_key")
        assert result == {"data": 42}
        del _cache["tc_key"]  # cleanup

    async def test_set_overwrites(self):
        await cache_set("tc_overwrite", {"v": 1})
        await cache_set("tc_overwrite", {"v": 2})
        assert (await cache_get("tc_overwrite")) == {"v": 2}
        del _cache["tc_overwrite"]


# ===========================================================================
# VideoSource enum
# ===========================================================================


class TestVideoSource:
    def test_youtube(self):
        assert VideoSource.YOUTUBE.value == "youtube"

    def test_vimeo(self):
        assert VideoSource.VIMEO.value == "vimeo"

    def test_local_file(self):
        assert VideoSource.LOCAL_FILE.value == "local"

    def test_url(self):
        assert VideoSource.URL.value == "url"


# ===========================================================================
# ProcessingStage enum
# ===========================================================================


class TestProcessingStage:
    def test_extraction(self):
        assert ProcessingStage.EXTRACTION.value == "extraction"

    def test_complete(self):
        assert ProcessingStage.COMPLETE.value == "complete"

    def test_analysis(self):
        assert ProcessingStage.ANALYSIS.value == "analysis"

    def test_transfer(self):
        assert ProcessingStage.TRANSFER.value == "transfer"


# ===========================================================================
# VideoMetadata dataclass
# ===========================================================================


class TestVideoMetadata:
    def test_basic_creation(self):
        m = VideoMetadata(
            video_id="abc", title="T", description="D",
            duration=60, upload_date="2024-01-01", uploader="U", view_count=1000,
        )
        assert m.video_id == "abc"
        assert m.title == "T"
        assert m.duration == 60

    def test_defaults(self):
        m = VideoMetadata(
            video_id="x", title="t", description="",
            duration=0, upload_date="", uploader="", view_count=0,
        )
        assert m.like_count is None
        assert m.comment_count is None
        assert m.thumbnail_url == ""
        assert m.language == "en"
        assert m.source == VideoSource.YOUTUBE


# ===========================================================================
# TranscriptSegment dataclass (from strategies, not videopack)
# ===========================================================================


class TestTranscriptSegmentStrategies:
    def test_end_defaults_to_start_plus_duration(self):
        seg = TranscriptSegment(text="hi", start=0.0, duration=5.0)
        assert seg.end == 5.0

    def test_explicit_end_preserved(self):
        seg = TranscriptSegment(text="hi", start=1.0, duration=2.0, end=99.0)
        assert seg.end == 99.0

    def test_text_stored(self):
        seg = TranscriptSegment(text="hello world", start=0.0, duration=3.0)
        assert seg.text == "hello world"


# ===========================================================================
# VideoContent dataclass
# ===========================================================================


class TestVideoContent:
    def _meta(self):
        return VideoMetadata(
            video_id="v", title="t", description="",
            duration=0, upload_date="", uploader="", view_count=0,
        )

    def test_processing_stage_default(self):
        vc = VideoContent(metadata=self._meta(), transcript=[])
        assert vc.processing_stage == ProcessingStage.EXTRACTION

    def test_summary_defaults_none(self):
        vc = VideoContent(metadata=self._meta(), transcript=[])
        assert vc.summary is None

    def test_processing_time_default(self):
        vc = VideoContent(metadata=self._meta(), transcript=[])
        assert vc.processing_time == 0.0


# ===========================================================================
# register_strategy / get_strategy
# ===========================================================================


class TestRegisterStrategy:
    def test_decorator_registers_class(self):
        @register_strategy("_test_reg")
        class _MyStrat(ProcessorStrategy):
            async def process_video(self, url, options=None):
                return {}
        assert get_strategy("_test_reg") is _MyStrat

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            get_strategy("__nonexistent__")

    def test_built_in_strategies_registered(self):
        assert "optimized" in _processor_strategies
        assert "parallel" in _processor_strategies
        assert "enhanced" in _processor_strategies


# ===========================================================================
# ProcessorStrategy.process_batch
# ===========================================================================


class TestProcessorStrategyBatch:
    async def test_batch_calls_process_video_for_each(self):
        calls = []

        class _Counted(ProcessorStrategy):
            async def process_video(self, url, options=None):
                calls.append(url)
                return {"url": url}

        strat = _Counted()
        urls = ["https://www.youtube.com/watch?v=aaaaaaaaaaa", "https://www.youtube.com/watch?v=bbbbbbbbbbb"]
        results = await strat.process_batch(urls)
        assert len(results) == 2
        assert set(calls) == set(urls)

    async def test_batch_returns_list(self):
        class _Noop(ProcessorStrategy):
            async def process_video(self, url, options=None):
                return {"ok": True}

        results = await _Noop().process_batch(["u1", "u2", "u3"])
        assert isinstance(results, list)
        assert len(results) == 3


# ===========================================================================
# OptimizedStrategy
# ===========================================================================


class TestOptimizedStrategyInit:
    def test_default_config_empty(self):
        opt = OptimizedStrategy()
        assert opt.config == {}

    def test_custom_config_stored(self):
        opt = OptimizedStrategy({"key": "val"})
        assert opt.config["key"] == "val"

    def test_stats_initialized(self):
        opt = OptimizedStrategy()
        assert opt.processing_stats["cache_hits"] == 0
        assert opt.processing_stats["cache_misses"] == 0
        assert opt.processing_stats["total_processed"] == 0

    def test_enhanced_strategy_initially_none(self):
        opt = OptimizedStrategy()
        assert opt._enhanced_strategy is None


class TestOptimizedStrategyProcessVideo:
    async def test_returns_dict(self):
        result = await OptimizedStrategy().process_video(_VALID_URL)
        assert isinstance(result, dict)

    async def test_increments_cache_misses(self):
        opt = OptimizedStrategy()
        await opt.process_video(_VALID_URL)
        assert opt.processing_stats["cache_misses"] == 1

    async def test_increments_total_processed(self):
        opt = OptimizedStrategy()
        await opt.process_video(_VALID_URL)
        assert opt.processing_stats["total_processed"] == 1

    async def test_adds_optimization_metadata(self):
        result = await OptimizedStrategy().process_video(_VALID_URL)
        assert result.get("optimization_applied") is True
        assert "processing_id" in result

    async def test_cache_hit_increments_counter(self):
        opt = OptimizedStrategy()
        cache_key = f"optimized_video:{__import__('hashlib').sha256(_VALID_URL.encode()).hexdigest()}"
        _cache[cache_key] = {"cached": True}
        try:
            result = await opt.process_video(_VALID_URL)
            assert result == {"cached": True}
            assert opt.processing_stats["cache_hits"] == 1
        finally:
            del _cache[cache_key]

    async def test_cache_disabled_skips_hit(self):
        opt = OptimizedStrategy({"enable_intelligent_caching": False})
        cache_key = f"optimized_video:{__import__('hashlib').sha256(_VALID_URL.encode()).hexdigest()}"
        _cache[cache_key] = {"cached": True}
        try:
            await opt.process_video(_VALID_URL)
            assert opt.processing_stats["cache_hits"] == 0
        finally:
            del _cache[cache_key]


# ===========================================================================
# ParallelStrategy
# ===========================================================================


class TestParallelStrategyInit:
    def test_default_max_workers(self):
        par = ParallelStrategy()
        assert par.max_workers == 4

    def test_custom_max_workers(self):
        par = ParallelStrategy({"max_workers": 2})
        assert par.max_workers == 2

    def test_enhanced_strategy_initially_none(self):
        par = ParallelStrategy()
        assert par._enhanced_strategy is None


class TestParallelStrategyProcessVideo:
    async def test_returns_dict(self):
        result = await ParallelStrategy().process_video(_VALID_URL)
        assert isinstance(result, dict)

    async def test_adds_parallel_metadata(self):
        result = await ParallelStrategy().process_video(_VALID_URL)
        assert result.get("parallel_processed") is True
        assert "processing_id" in result

    async def test_adds_max_workers(self):
        par = ParallelStrategy({"max_workers": 3})
        result = await par.process_video(_VALID_URL)
        assert result.get("max_workers") == 3


class TestParallelStrategyProcessBatch:
    async def test_batch_returns_list(self):
        par = ParallelStrategy()
        results = await par.process_batch([_VALID_URL, _VALID_URL])
        assert isinstance(results, list)
        assert len(results) == 2

    async def test_empty_batch_returns_empty(self):
        par = ParallelStrategy()
        results = await par.process_batch([])
        assert results == []


# ===========================================================================
# EnhancedStrategy
# ===========================================================================


class TestEnhancedStrategyInit:
    def test_config_stored(self):
        enh = EnhancedStrategy({"setting": True})
        assert enh.config["setting"] is True

    def test_default_config_empty(self):
        enh = EnhancedStrategy()
        assert enh.config == {}

    def test_no_video_client_without_deps(self):
        with patch.object(_mod, "HAS_VIDEO_DEPS", False), \
             patch.object(_mod, "HAS_AI_DEPS", False):
            enh = EnhancedStrategy()
        assert not hasattr(enh, "video_client")


class TestEnhancedStrategyProcessVideo:
    async def test_returns_dict(self):
        result = await EnhancedStrategy().process_video(_VALID_URL)
        assert isinstance(result, dict)

    async def test_error_log_present_without_deps(self):
        result = await EnhancedStrategy().process_video(_VALID_URL)
        assert "error_log" in result
        assert len(result["error_log"]) > 0

    async def test_metadata_present(self):
        result = await EnhancedStrategy().process_video(_VALID_URL)
        assert "metadata" in result

    async def test_processing_stage_in_result(self):
        result = await EnhancedStrategy().process_video(_VALID_URL)
        assert "processing_stage" in result
