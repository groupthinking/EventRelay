"""Unit tests for all Pydantic models in backend.api.v1.models."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.api.v1.models import (
    AgentDispatchRequest,
    AgentDispatchResponse,
    AgentExecution,
    AgentStatus,
    AgentStatusResponse,
    ApiResponse,
    CacheStats,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    EventExtractRequest,
    EventExtractResponse,
    ExtractedEvent,
    FeedbackRequest,
    FeedbackResponse,
    GeminiBatchRequest,
    GeminiBatchResponse,
    GeminiCacheRequest,
    GeminiCacheResponse,
    GeminiTokenRequest,
    GeminiTokenResponse,
    HealthResponse,
    JobStatus,
    MarkdownRequest,
    MarkdownResponse,
    TranscriptActionRequest,
    TranscriptActionResponse,
    VideoClipOptions,
    VideoJobStatusResponse,
    VideoProcessJobRequest,
    VideoProcessJobResponse,
    VideoProcessingRequest,
    VideoProcessingResponse,
    VideoToSoftwareRequest,
    VideoToSoftwareResponse,
)

_VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
_VALID_SHORT = "https://youtu.be/dQw4w9WgXcQ"


# ===========================================================================
# Enums
# ===========================================================================


class TestJobStatus:
    def test_all_values(self):
        values = {s.value for s in JobStatus}
        assert values == {"pending", "downloading", "transcribing", "extracting", "complete", "failed"}

    def test_str_enum(self):
        assert JobStatus.pending == "pending"


class TestAgentStatus:
    def test_all_values(self):
        values = {s.value for s in AgentStatus}
        assert values == {"queued", "running", "complete", "failed"}


# ===========================================================================
# ApiResponse
# ===========================================================================


class TestApiResponse:
    def test_success_factory(self):
        r = ApiResponse.success({"result": 42})
        assert r.status == "success"
        assert r.data == {"result": 42}
        assert r.error is None

    def test_fail_factory(self):
        r = ApiResponse.fail("Not found", detail="Resource missing")
        assert r.status == "error"
        assert r.error == "Not found"
        assert r.detail == "Resource missing"

    def test_request_id_auto_generated(self):
        r = ApiResponse.success(None)
        assert r.request_id.startswith("req_")

    def test_timestamp_auto_set(self):
        r = ApiResponse.success(None)
        assert isinstance(r.timestamp, datetime)

    def test_data_defaults_none(self):
        r = ApiResponse(status="success")
        assert r.data is None


# ===========================================================================
# VideoProcessJobRequest
# ===========================================================================


class TestVideoProcessJobRequest:
    def test_valid_url_accepted(self):
        r = VideoProcessJobRequest(video_url=_VALID_URL)
        assert r.video_url == _VALID_URL

    def test_short_url_accepted(self):
        r = VideoProcessJobRequest(video_url=_VALID_SHORT)
        assert r.video_url == _VALID_SHORT

    def test_invalid_url_raises(self):
        with pytest.raises(ValidationError, match="Invalid YouTube URL"):
            VideoProcessJobRequest(video_url="https://vimeo.com/123456")

    def test_language_defaults_en(self):
        r = VideoProcessJobRequest(video_url=_VALID_URL)
        assert r.language == "en"

    def test_options_defaults_empty_dict(self):
        r = VideoProcessJobRequest(video_url=_VALID_URL)
        assert r.options == {}


# ===========================================================================
# VideoProcessJobResponse
# ===========================================================================


class TestVideoProcessJobResponse:
    def test_fields_stored(self):
        r = VideoProcessJobResponse(job_id="job-1", video_url=_VALID_URL)
        assert r.job_id == "job-1"
        assert r.video_url == _VALID_URL

    def test_status_defaults_pending(self):
        r = VideoProcessJobResponse(job_id="j", video_url=_VALID_URL)
        assert r.status == JobStatus.pending


# ===========================================================================
# VideoJobStatusResponse
# ===========================================================================


class TestVideoJobStatusResponse:
    def test_required_fields(self):
        r = VideoJobStatusResponse(job_id="j1", status=JobStatus.complete)
        assert r.job_id == "j1"
        assert r.status == JobStatus.complete

    def test_progress_defaults_zero(self):
        r = VideoJobStatusResponse(job_id="j", status=JobStatus.pending)
        assert r.progress == 0.0

    def test_optional_fields_default_none(self):
        r = VideoJobStatusResponse(job_id="j", status=JobStatus.pending)
        assert r.transcript is None
        assert r.metadata is None
        assert r.error is None


# ===========================================================================
# ExtractedEvent
# ===========================================================================


class TestExtractedEvent:
    def test_required_fields(self):
        e = ExtractedEvent(type="action", title="Set up account")
        assert e.type == "action"
        assert e.title == "Set up account"

    def test_id_auto_generated(self):
        e = ExtractedEvent(type="mention", title="Tool")
        assert e.id.startswith("evt_")

    def test_confidence_defaults_one(self):
        e = ExtractedEvent(type="insight", title="Tip")
        assert e.confidence == 1.0

    def test_confidence_constrained(self):
        with pytest.raises(ValidationError):
            ExtractedEvent(type="x", title="t", confidence=1.5)


# ===========================================================================
# EventExtractRequest / Response
# ===========================================================================


class TestEventExtractRequest:
    def test_all_optional(self):
        r = EventExtractRequest()
        assert r.job_id is None
        assert r.transcript is None

    def test_fields_stored(self):
        r = EventExtractRequest(job_id="j1", transcript="Hello world")
        assert r.job_id == "j1"
        assert r.transcript == "Hello world"


class TestEventExtractResponse:
    def test_events_default_empty(self):
        r = EventExtractResponse()
        assert r.events == []

    def test_event_count_default_zero(self):
        r = EventExtractResponse()
        assert r.event_count == 0


# ===========================================================================
# AgentDispatchRequest / Response / AgentExecution
# ===========================================================================


class TestAgentDispatchRequest:
    def test_events_default_empty(self):
        r = AgentDispatchRequest()
        assert r.events == []

    def test_agent_types_default_none(self):
        r = AgentDispatchRequest()
        assert r.agent_types is None


class TestAgentExecution:
    def test_required_agent_type(self):
        e = AgentExecution(agent_type="summarizer")
        assert e.agent_type == "summarizer"

    def test_status_defaults_queued(self):
        e = AgentExecution(agent_type="analyzer")
        assert e.status == AgentStatus.queued

    def test_agent_id_auto_generated(self):
        e = AgentExecution(agent_type="x")
        assert e.agent_id.startswith("agent_")

    def test_progress_constrained(self):
        with pytest.raises(ValidationError):
            AgentExecution(agent_type="x", progress=101.0)


class TestAgentDispatchResponse:
    def test_dispatch_id_auto_generated(self):
        r = AgentDispatchResponse()
        assert r.dispatch_id.startswith("dsp_")

    def test_executions_default_empty(self):
        r = AgentDispatchResponse()
        assert r.executions == []


# ===========================================================================
# ChatRequest / ChatResponse
# ===========================================================================


class TestChatRequest:
    def test_query_alias(self):
        r = ChatRequest.model_validate({"query": "Hello"})
        assert r.message == "Hello"

    def test_context_defaults(self):
        r = ChatRequest.model_validate({"query": "hi"})
        assert r.context == "tooltip-assistant"

    def test_session_id_defaults(self):
        r = ChatRequest.model_validate({"query": "hi"})
        assert r.session_id == "default"

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest.model_validate({"query": ""})


class TestChatResponse:
    def test_required_fields(self):
        r = ChatResponse(
            response="Hello",
            status="success",
            session_id="s1",
            timestamp=datetime.utcnow(),
        )
        assert r.response == "Hello"
        assert r.status == "success"


# ===========================================================================
# VideoProcessingRequest
# ===========================================================================


class TestVideoProcessingRequest:
    def test_valid_url_accepted(self):
        r = VideoProcessingRequest(video_url=_VALID_URL)
        assert r.video_url == _VALID_URL

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError, match="Invalid YouTube URL"):
            VideoProcessingRequest(video_url="not-a-url")

    def test_embed_url_accepted(self):
        r = VideoProcessingRequest(
            video_url="https://www.youtube.com/embed/dQw4w9WgXcQ"
        )
        assert "embed" in r.video_url


# ===========================================================================
# MarkdownRequest
# ===========================================================================


class TestMarkdownRequest:
    def test_valid_url_accepted(self):
        r = MarkdownRequest(video_url=_VALID_URL)
        assert r.video_url == _VALID_URL

    def test_force_regenerate_defaults_false(self):
        r = MarkdownRequest(video_url=_VALID_URL)
        assert r.force_regenerate is False

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError):
            MarkdownRequest(video_url="ftp://youtube.com/watch?v=aaaaaaaaaaa")


# ===========================================================================
# VideoClipOptions
# ===========================================================================


class TestVideoClipOptions:
    def test_all_optional(self):
        opts = VideoClipOptions()
        assert opts.start_seconds is None
        assert opts.end_seconds is None
        assert opts.fps is None

    def test_valid_clip_range(self):
        opts = VideoClipOptions(start_seconds=10.0, end_seconds=30.0)
        assert opts.start_seconds == 10.0
        assert opts.end_seconds == 30.0

    def test_end_before_start_raises(self):
        with pytest.raises(ValidationError, match="end_seconds must be greater"):
            VideoClipOptions(start_seconds=30.0, end_seconds=10.0)

    def test_fps_constrained_to_30(self):
        with pytest.raises(ValidationError):
            VideoClipOptions(fps=60.0)

    def test_valid_fps(self):
        opts = VideoClipOptions(fps=24.0)
        assert opts.fps == 24.0


# ===========================================================================
# TranscriptActionRequest / Response
# ===========================================================================


class TestTranscriptActionRequest:
    def test_required_video_url(self):
        r = TranscriptActionRequest(video_url=_VALID_URL)
        assert r.video_url == _VALID_URL

    def test_language_defaults_en(self):
        r = TranscriptActionRequest(video_url=_VALID_URL)
        assert r.language == "en"

    def test_video_options_default_none(self):
        r = TranscriptActionRequest(video_url=_VALID_URL)
        assert r.video_options is None


class TestTranscriptActionResponse:
    def _make(self, **kw):
        defaults = dict(
            success=True,
            video_url=_VALID_URL,
            metadata={},
            transcript={},
            outputs={},
            orchestration_meta={},
        )
        return TranscriptActionResponse(**{**defaults, **kw})

    def test_required_fields_stored(self):
        r = self._make()
        assert r.success is True
        assert r.video_url == _VALID_URL

    def test_errors_default_empty(self):
        assert self._make().errors == []

    def test_async_processing_default_false(self):
        assert self._make().async_processing is False

    def test_job_status_default_none(self):
        assert self._make().job_status is None

    def test_job_status_accepts_enum(self):
        r = self._make(job_status=JobStatus.complete)
        assert r.job_status == JobStatus.complete


# ===========================================================================
# VideoToSoftwareRequest
# ===========================================================================


class TestVideoToSoftwareRequest:
    def test_valid_request(self):
        r = VideoToSoftwareRequest.model_validate({"url": _VALID_URL})
        assert r.video_url == _VALID_URL

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError, match="Invalid YouTube URL"):
            VideoToSoftwareRequest.model_validate({"url": "https://example.com"})

    def test_invalid_project_type_rejected(self):
        with pytest.raises(ValidationError):
            VideoToSoftwareRequest.model_validate(
                {"url": _VALID_URL, "project_type": "blockchain"}
            )

    def test_invalid_deployment_target_rejected(self):
        with pytest.raises(ValidationError):
            VideoToSoftwareRequest.model_validate(
                {"url": _VALID_URL, "deployment_target": "aws"}
            )

    def test_defaults(self):
        r = VideoToSoftwareRequest.model_validate({"url": _VALID_URL})
        assert r.project_type == "web"
        assert r.deployment_target == "vercel"


# ===========================================================================
# FeedbackRequest
# ===========================================================================


class TestFeedbackRequest:
    def test_valid_feedback_type(self):
        r = FeedbackRequest(feedback_type="quality")
        assert r.feedback_type == "quality"

    def test_invalid_feedback_type_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackRequest(feedback_type="random_type")

    def test_rating_constrained_1_to_5(self):
        with pytest.raises(ValidationError):
            FeedbackRequest(feedback_type="quality", rating=6)

    def test_rating_of_five_accepted(self):
        r = FeedbackRequest(feedback_type="general", rating=5)
        assert r.rating == 5

    def test_optional_fields_default_none(self):
        r = FeedbackRequest(feedback_type="speed")
        assert r.video_id is None
        assert r.comment is None


# ===========================================================================
# HealthResponse
# ===========================================================================


class TestHealthResponse:
    def test_required_fields(self):
        r = HealthResponse(status="healthy", timestamp=datetime.utcnow())
        assert r.status == "healthy"

    def test_components_default_empty_dict(self):
        r = HealthResponse(status="ok", timestamp=datetime.utcnow())
        assert r.components == {}

    def test_version_default_none(self):
        r = HealthResponse(status="ok", timestamp=datetime.utcnow())
        assert r.version is None


# ===========================================================================
# CacheStats
# ===========================================================================


class TestCacheStats:
    def test_required_fields(self):
        r = CacheStats(total_cached_videos=10, categories={}, total_size_mb=5.0)
        assert r.total_cached_videos == 10
        assert r.total_size_mb == 5.0

    def test_optional_timestamps_default_none(self):
        r = CacheStats(total_cached_videos=0, categories={}, total_size_mb=0.0)
        assert r.oldest_cache is None
        assert r.newest_cache is None


# ===========================================================================
# GeminiCacheRequest / Response
# ===========================================================================


class TestGeminiCacheRequest:
    def test_required_contents(self):
        r = GeminiCacheRequest(contents="Hello world")
        assert r.contents == "Hello world"

    def test_ttl_defaults_3600(self):
        r = GeminiCacheRequest(contents="x")
        assert r.ttl_seconds == 3600

    def test_generation_params_default_empty(self):
        r = GeminiCacheRequest(contents="x")
        assert r.generation_params == {}

    def test_ttl_minimum_60(self):
        with pytest.raises(ValidationError):
            GeminiCacheRequest(contents="x", ttl_seconds=30)


class TestGeminiCacheResponse:
    def test_required_success(self):
        r = GeminiCacheResponse(success=True)
        assert r.success is True

    def test_optional_defaults_none(self):
        r = GeminiCacheResponse(success=False)
        assert r.cache is None
        assert r.error is None


# ===========================================================================
# ErrorResponse
# ===========================================================================


class TestErrorResponse:
    def test_required_fields(self):
        r = ErrorResponse(error="Something went wrong", timestamp=datetime.utcnow())
        assert r.error == "Something went wrong"

    def test_optional_defaults_none(self):
        r = ErrorResponse(error="e", timestamp=datetime.utcnow())
        assert r.detail is None
        assert r.error_type is None
        assert r.path is None
