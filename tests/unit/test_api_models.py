"""
Unit tests for API v1 Pydantic models — validators, serialization, and edge cases.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.api.v1.models import (
    AgentDispatchRequest,
    AgentExecution,
    AgentStatus,
    ApiResponse,
    EventExtractRequest,
    ExtractedEvent,
    FeedbackRequest,
    GeminiBatchRequest,
    GeminiCacheRequest,
    JobStatus,
    MarkdownRequest,
    TranscriptActionRequest,
    VideoClipOptions,
    VideoProcessingRequest,
    VideoProcessJobRequest,
    VideoToSoftwareRequest,
)


# ===========================================================================
# ApiResponse
# ===========================================================================


class TestApiResponse:
    def test_success_sets_status_and_data(self):
        r = ApiResponse.success({"key": "value"})
        assert r.status == "success"
        assert r.data == {"key": "value"}
        assert r.error is None

    def test_fail_sets_status_and_error(self):
        r = ApiResponse.fail("Something broke", detail="stack trace here")
        assert r.status == "error"
        assert r.error == "Something broke"
        assert r.detail == "stack trace here"
        assert r.data is None

    def test_success_with_none_data(self):
        r = ApiResponse.success(None)
        assert r.status == "success"

    def test_request_id_auto_generated(self):
        r1 = ApiResponse.success({})
        r2 = ApiResponse.success({})
        assert r1.request_id != r2.request_id
        assert r1.request_id.startswith("req_")


# ===========================================================================
# JobStatus / AgentStatus enums
# ===========================================================================


class TestEnums:
    def test_job_status_values(self):
        assert JobStatus.pending == "pending"
        assert JobStatus.downloading == "downloading"
        assert JobStatus.transcribing == "transcribing"
        assert JobStatus.complete == "complete"
        assert JobStatus.failed == "failed"

    def test_agent_status_values(self):
        assert AgentStatus.queued == "queued"
        assert AgentStatus.running == "running"
        assert AgentStatus.complete == "complete"
        assert AgentStatus.failed == "failed"


# ===========================================================================
# VideoProcessingRequest
# ===========================================================================


class TestVideoProcessingRequest:
    _VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_valid_youtube_url_accepted(self):
        req = VideoProcessingRequest(video_url=self._VALID_URL)
        assert req.video_url == self._VALID_URL

    def test_youtu_be_short_url_accepted(self):
        req = VideoProcessingRequest(video_url="https://youtu.be/dQw4w9WgXcQ")
        assert "dQw4w9WgXcQ" in req.video_url

    def test_embed_url_accepted(self):
        req = VideoProcessingRequest(
            video_url="https://www.youtube.com/embed/dQw4w9WgXcQ"
        )
        assert req.video_url is not None

    def test_non_youtube_url_rejected(self):
        with pytest.raises(ValidationError, match="Invalid YouTube URL"):
            VideoProcessingRequest(video_url="https://vimeo.com/123456789")

    def test_plain_string_rejected(self):
        with pytest.raises(ValidationError):
            VideoProcessingRequest(video_url="not a url at all")

    def test_missing_video_id_rejected(self):
        with pytest.raises(ValidationError):
            VideoProcessingRequest(video_url="https://www.youtube.com/watch?v=short")

    def test_empty_url_rejected(self):
        with pytest.raises(ValidationError):
            VideoProcessingRequest(video_url="")

    def test_options_default_to_empty_dict(self):
        req = VideoProcessingRequest(video_url=self._VALID_URL)
        assert req.options == {}


# ===========================================================================
# VideoProcessJobRequest
# ===========================================================================


class TestVideoProcessJobRequest:
    _VALID_URL = "https://www.youtube.com/watch?v=abcdefghijk"

    def test_valid_request_accepted(self):
        req = VideoProcessJobRequest(video_url=self._VALID_URL)
        assert req.video_url == self._VALID_URL

    def test_language_defaults_to_en(self):
        req = VideoProcessJobRequest(video_url=self._VALID_URL)
        assert req.language == "en"

    def test_invalid_url_raises(self):
        with pytest.raises(ValidationError, match="Invalid YouTube URL"):
            VideoProcessJobRequest(video_url="https://not-youtube.com/watch?v=12345678901")

    def test_options_defaults_to_empty(self):
        req = VideoProcessJobRequest(video_url=self._VALID_URL)
        assert req.options == {} or req.options is None


# ===========================================================================
# MarkdownRequest
# ===========================================================================


class TestMarkdownRequest:
    _VALID_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

    def test_valid_url_accepted(self):
        req = MarkdownRequest(video_url=self._VALID_URL)
        assert req.video_url == self._VALID_URL

    def test_force_regenerate_defaults_false(self):
        req = MarkdownRequest(video_url=self._VALID_URL)
        assert req.force_regenerate is False

    def test_invalid_url_raises(self):
        with pytest.raises(ValidationError):
            MarkdownRequest(video_url="https://notyt.com/watch?v=jNQXAC9IVRw")


# ===========================================================================
# VideoToSoftwareRequest
# ===========================================================================


class TestVideoToSoftwareRequest:
    _VALID_URL = "https://www.youtube.com/watch?v=bMknfKXIFA8"

    def test_valid_request_accepted(self):
        req = VideoToSoftwareRequest(url=self._VALID_URL)
        assert req.video_url == self._VALID_URL

    def test_default_project_type_is_web(self):
        req = VideoToSoftwareRequest(url=self._VALID_URL)
        assert req.project_type == "web"

    def test_default_deployment_target_is_vercel(self):
        req = VideoToSoftwareRequest(url=self._VALID_URL)
        assert req.deployment_target == "vercel"

    def test_valid_project_types_accepted(self):
        for ptype in ["web", "api", "ml", "mobile", "desktop"]:
            req = VideoToSoftwareRequest(url=self._VALID_URL, project_type=ptype)
            assert req.project_type == ptype

    def test_invalid_project_type_rejected(self):
        with pytest.raises(ValidationError, match="Project type must be one of"):
            VideoToSoftwareRequest(url=self._VALID_URL, project_type="blockchain")

    def test_valid_deployment_targets_accepted(self):
        for target in ["vercel", "github", "cursor", "claude", "gemini"]:
            req = VideoToSoftwareRequest(url=self._VALID_URL, deployment_target=target)
            assert req.deployment_target == target

    def test_invalid_deployment_target_rejected(self):
        with pytest.raises(ValidationError, match="Deployment target must be one of"):
            VideoToSoftwareRequest(url=self._VALID_URL, deployment_target="aws")

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError):
            VideoToSoftwareRequest(url="https://not-youtube.com/video/123")

    def test_features_default_to_empty_list(self):
        req = VideoToSoftwareRequest(url=self._VALID_URL)
        assert req.features == []


# ===========================================================================
# VideoClipOptions
# ===========================================================================


class TestVideoClipOptions:
    def test_valid_options_accepted(self):
        opts = VideoClipOptions(start_seconds=10.0, end_seconds=60.0, fps=5.0)
        assert opts.start_seconds == 10.0
        assert opts.end_seconds == 60.0

    def test_end_before_start_rejected(self):
        with pytest.raises(ValidationError, match="end_seconds must be greater than start_seconds"):
            VideoClipOptions(start_seconds=60.0, end_seconds=10.0)

    def test_end_equal_to_start_rejected(self):
        with pytest.raises(ValidationError):
            VideoClipOptions(start_seconds=30.0, end_seconds=30.0)

    def test_fps_above_30_rejected(self):
        with pytest.raises(ValidationError):
            VideoClipOptions(fps=31.0)

    def test_fps_zero_rejected(self):
        with pytest.raises(ValidationError):
            VideoClipOptions(fps=0.0)

    def test_negative_start_rejected(self):
        with pytest.raises(ValidationError):
            VideoClipOptions(start_seconds=-1.0)

    def test_all_fields_optional(self):
        opts = VideoClipOptions()
        assert opts.start_seconds is None
        assert opts.end_seconds is None
        assert opts.fps is None

    def test_end_without_start_allowed(self):
        opts = VideoClipOptions(end_seconds=30.0)
        assert opts.end_seconds == 30.0


# ===========================================================================
# TranscriptActionRequest
# ===========================================================================


class TestTranscriptActionRequest:
    _VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_minimal_request_accepted(self):
        req = TranscriptActionRequest(video_url=self._VALID_URL)
        assert req.video_url == self._VALID_URL

    def test_language_defaults_to_en(self):
        req = TranscriptActionRequest(video_url=self._VALID_URL)
        assert req.language == "en"

    def test_with_transcript_text(self):
        req = TranscriptActionRequest(
            video_url=self._VALID_URL,
            transcript_text="Hello world transcript",
        )
        assert req.transcript_text == "Hello world transcript"

    def test_with_video_options(self):
        opts = VideoClipOptions(start_seconds=0.0, end_seconds=120.0)
        req = TranscriptActionRequest(video_url=self._VALID_URL, video_options=opts)
        assert req.video_options.end_seconds == 120.0


# ===========================================================================
# FeedbackRequest
# ===========================================================================


class TestFeedbackRequest:
    def test_valid_feedback_accepted(self):
        req = FeedbackRequest(feedback_type="quality")
        assert req.feedback_type == "quality"

    def test_all_valid_feedback_types_accepted(self):
        for ftype in ["quality", "accuracy", "speed", "feature_request", "bug_report", "general"]:
            req = FeedbackRequest(feedback_type=ftype)
            assert req.feedback_type == ftype

    def test_invalid_feedback_type_rejected(self):
        with pytest.raises(ValidationError, match="Feedback type must be one of"):
            FeedbackRequest(feedback_type="complaint")

    def test_rating_range_valid(self):
        for rating in [1, 2, 3, 4, 5]:
            req = FeedbackRequest(feedback_type="quality", rating=rating)
            assert req.rating == rating

    def test_rating_zero_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackRequest(feedback_type="quality", rating=0)

    def test_rating_above_five_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackRequest(feedback_type="quality", rating=6)

    def test_comment_max_length_enforced(self):
        with pytest.raises(ValidationError):
            FeedbackRequest(feedback_type="general", comment="x" * 1001)

    def test_comment_at_max_length_accepted(self):
        req = FeedbackRequest(feedback_type="general", comment="x" * 1000)
        assert len(req.comment) == 1000

    def test_optional_fields_default_none(self):
        req = FeedbackRequest(feedback_type="general")
        assert req.video_id is None
        assert req.rating is None
        assert req.comment is None
        assert req.user_id is None


# ===========================================================================
# GeminiCacheRequest
# ===========================================================================


class TestGeminiCacheRequest:
    def test_valid_request_with_string_contents(self):
        req = GeminiCacheRequest(contents="Analyze this video")
        assert req.contents == "Analyze this video"
        assert req.ttl_seconds == 3600

    def test_valid_request_with_dict_contents(self):
        req = GeminiCacheRequest(contents={"role": "user", "text": "hello"})
        assert isinstance(req.contents, dict)

    def test_ttl_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            GeminiCacheRequest(contents="hello", ttl_seconds=59)

    def test_ttl_at_minimum_accepted(self):
        req = GeminiCacheRequest(contents="hello", ttl_seconds=60)
        assert req.ttl_seconds == 60


# ===========================================================================
# GeminiBatchRequest
# ===========================================================================


class TestGeminiBatchRequest:
    def test_valid_batch_request(self):
        req = GeminiBatchRequest(requests=[{"prompt": "hello"}])
        assert len(req.requests) == 1
        assert req.wait is False

    def test_empty_requests_rejected(self):
        with pytest.raises(ValidationError):
            GeminiBatchRequest(requests=[])

    def test_poll_interval_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            GeminiBatchRequest(requests=[{"p": "x"}], poll_interval=0.0)

    def test_timeout_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            GeminiBatchRequest(requests=[{"p": "x"}], timeout=0.5)


# ===========================================================================
# EventExtractRequest
# ===========================================================================


class TestEventExtractRequest:
    def test_with_job_id_only(self):
        req = EventExtractRequest(job_id="job_abc123")
        assert req.job_id == "job_abc123"
        assert req.transcript is None

    def test_with_transcript_only(self):
        req = EventExtractRequest(transcript="Build a FastAPI app with auth.")
        assert req.transcript is not None

    def test_both_fields_none_allowed(self):
        req = EventExtractRequest()
        assert req.job_id is None
        assert req.transcript is None


# ===========================================================================
# AgentDispatchRequest
# ===========================================================================


class TestAgentDispatchRequest:
    def test_with_events_list(self):
        req = AgentDispatchRequest(events=[{"id": "evt_1", "type": "action", "title": "Do thing"}])
        assert len(req.events) == 1

    def test_empty_events_allowed(self):
        req = AgentDispatchRequest()
        assert req.events == []

    def test_with_transcript(self):
        req = AgentDispatchRequest(transcript="Build a Docker container and deploy it.")
        assert "Docker" in req.transcript

    def test_agent_types_optional(self):
        req = AgentDispatchRequest()
        assert req.agent_types is None


# ===========================================================================
# ExtractedEvent
# ===========================================================================


class TestExtractedEvent:
    def test_auto_generated_id(self):
        e1 = ExtractedEvent(type="action", title="Do something")
        e2 = ExtractedEvent(type="topic", title="Learn something")
        assert e1.id != e2.id
        assert e1.id.startswith("evt_")

    def test_confidence_default(self):
        event = ExtractedEvent(type="action", title="Do it")
        assert event.confidence == 1.0

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            ExtractedEvent(type="action", title="Do it", confidence=1.5)

    def test_negative_confidence_rejected(self):
        with pytest.raises(ValidationError):
            ExtractedEvent(type="action", title="Do it", confidence=-0.1)


# ===========================================================================
# AgentExecution
# ===========================================================================


class TestAgentExecution:
    def test_auto_generated_agent_id(self):
        ex = AgentExecution(agent_type="analyzer")
        assert ex.agent_id.startswith("agent_")

    def test_default_status_queued(self):
        ex = AgentExecution(agent_type="analyzer")
        assert ex.status == AgentStatus.queued

    def test_progress_clamped_at_100(self):
        with pytest.raises(ValidationError):
            AgentExecution(agent_type="x", progress=101.0)

    def test_progress_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            AgentExecution(agent_type="x", progress=-1.0)
