"""Unit tests for VideoSource, ProcessingStage, VideoMetadata, TranscriptSegment, VideoContent."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.processors.strategies import (
    ProcessingStage,
    TranscriptSegment,
    VideoContent,
    VideoMetadata,
    VideoSource,
    get_strategy,
    register_strategy,
)

# ===========================================================================
# VideoSource enum
# ===========================================================================


class TestVideoSourceEnum:
    def test_youtube_value(self):
        assert VideoSource.YOUTUBE.value == "youtube"

    def test_vimeo_value(self):
        assert VideoSource.VIMEO.value == "vimeo"

    def test_local_file_value(self):
        assert VideoSource.LOCAL_FILE.value == "local"

    def test_url_value(self):
        assert VideoSource.URL.value == "url"

    def test_has_four_members(self):
        assert len(VideoSource) == 4


# ===========================================================================
# ProcessingStage enum
# ===========================================================================


class TestProcessingStageEnum:
    def test_extraction_value(self):
        assert ProcessingStage.EXTRACTION.value == "extraction"

    def test_transcription_value(self):
        assert ProcessingStage.TRANSCRIPTION.value == "transcription"

    def test_analysis_value(self):
        assert ProcessingStage.ANALYSIS.value == "analysis"

    def test_transfer_value(self):
        assert ProcessingStage.TRANSFER.value == "transfer"

    def test_complete_value(self):
        assert ProcessingStage.COMPLETE.value == "complete"

    def test_has_five_members(self):
        assert len(ProcessingStage) == 5


# ===========================================================================
# VideoMetadata dataclass
# ===========================================================================


def _make_metadata(**kwargs):
    defaults = dict(
        video_id="abc123",
        title="Test Video",
        description="A test",
        duration=120,
        upload_date="2024-01-01",
        uploader="TestUser",
        view_count=1000,
    )
    defaults.update(kwargs)
    return VideoMetadata(**defaults)


class TestVideoMetadata:
    def test_required_fields_stored(self):
        m = _make_metadata()
        assert m.video_id == "abc123"
        assert m.title == "Test Video"
        assert m.duration == 120

    def test_like_count_defaults_none(self):
        assert _make_metadata().like_count is None

    def test_comment_count_defaults_none(self):
        assert _make_metadata().comment_count is None

    def test_tags_defaults_none(self):
        assert _make_metadata().tags is None

    def test_thumbnail_url_defaults_empty(self):
        assert _make_metadata().thumbnail_url == ""

    def test_language_defaults_en(self):
        assert _make_metadata().language == "en"

    def test_source_defaults_youtube(self):
        assert _make_metadata().source == VideoSource.YOUTUBE

    def test_explicit_fields(self):
        m = _make_metadata(like_count=500, comment_count=100, language="fr")
        assert m.like_count == 500
        assert m.comment_count == 100
        assert m.language == "fr"


# ===========================================================================
# TranscriptSegment dataclass
# ===========================================================================


class TestTranscriptSegment:
    def test_end_calculated_when_none(self):
        seg = TranscriptSegment(text="Hello", start=5.0, duration=3.0)
        assert seg.end == 8.0

    def test_explicit_end_preserved(self):
        seg = TranscriptSegment(text="Hello", start=5.0, duration=3.0, end=10.0)
        assert seg.end == 10.0

    def test_text_stored(self):
        seg = TranscriptSegment(text="Test text", start=0.0, duration=2.0)
        assert seg.text == "Test text"

    def test_start_stored(self):
        seg = TranscriptSegment(text="hi", start=12.5, duration=1.0)
        assert seg.start == 12.5

    def test_duration_stored(self):
        seg = TranscriptSegment(text="hi", start=0.0, duration=4.5)
        assert seg.duration == 4.5

    def test_end_zero_start(self):
        seg = TranscriptSegment(text="hi", start=0.0, duration=5.0)
        assert seg.end == 5.0

    def test_fractional_times(self):
        seg = TranscriptSegment(text="hi", start=1.5, duration=2.3)
        assert abs(seg.end - 3.8) < 1e-9


# ===========================================================================
# VideoContent dataclass
# ===========================================================================


class TestVideoContent:
    @pytest.fixture
    def content(self):
        meta = _make_metadata()
        return VideoContent(metadata=meta, transcript=[])

    def test_metadata_stored(self, content):
        assert content.metadata.video_id == "abc123"

    def test_transcript_stored(self, content):
        assert content.transcript == []

    def test_summary_defaults_none(self, content):
        assert content.summary is None

    def test_key_points_defaults_none(self, content):
        assert content.key_points is None

    def test_topics_defaults_none(self, content):
        assert content.topics is None

    def test_sentiment_defaults_none(self, content):
        assert content.sentiment is None

    def test_processing_stage_defaults_extraction(self, content):
        assert content.processing_stage == ProcessingStage.EXTRACTION

    def test_processing_time_defaults_zero(self, content):
        assert content.processing_time == 0.0

    def test_error_log_defaults_none(self, content):
        assert content.error_log is None

    def test_explicit_fields(self):
        meta = _make_metadata()
        c = VideoContent(
            metadata=meta,
            transcript=[],
            summary="A summary",
            processing_stage=ProcessingStage.COMPLETE,
            processing_time=5.5,
        )
        assert c.summary == "A summary"
        assert c.processing_stage == ProcessingStage.COMPLETE
        assert c.processing_time == 5.5


# ===========================================================================
# register_strategy / get_strategy
# ===========================================================================


class TestStrategyRegistry:
    def test_get_unknown_strategy_raises(self):
        with pytest.raises(ValueError):
            get_strategy("__nonexistent__")

    def test_registered_strategy_retrievable(self):
        @register_strategy("__test_strat__")
        class DummyStrat:
            pass

        assert get_strategy("__test_strat__") is DummyStrat

    def test_optimized_strategy_registered(self):
        from youtube_extension.processors.strategies import OptimizedStrategy
        assert get_strategy("optimized") is OptimizedStrategy
