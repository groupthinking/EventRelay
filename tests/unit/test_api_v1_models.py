#!/usr/bin/env python3
"""
Tests for the new Phase 1 API v1 endpoints:
  - POST /api/v1/videos/process
  - GET  /api/v1/videos/{job_id}/status
  - POST /api/v1/events/extract
  - POST /api/v1/agents/dispatch
  - GET  /api/v1/agents/{agent_id}/status
"""

import pytest

from youtube_extension.backend.api.v1.models import (
    AgentDispatchRequest,
    AgentDispatchResponse,
    AgentExecution,
    AgentStatus,
    AgentStatusResponse,
    ApiResponse,
    EventExtractRequest,
    EventExtractResponse,
    ExtractedEvent,
    JobStatus,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    VideoJobStatusResponse,
    VideoProcessJobRequest,
    VideoProcessJobResponse,
)


# ── Model validation tests ──


class TestApiResponseModel:
    def test_success(self):
        resp = ApiResponse.success({"key": "value"})
        assert resp.status == "success"
        assert resp.data == {"key": "value"}
        assert resp.error is None
        assert resp.request_id.startswith("req_")

    def test_fail(self):
        resp = ApiResponse.fail("Not found", detail="Job xyz missing")
        assert resp.status == "error"
        assert resp.error == "Not found"
        assert resp.detail == "Job xyz missing"
        assert resp.data is None


class TestVideoProcessJobRequest:
    def test_valid_url(self):
        req = VideoProcessJobRequest(
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag"
        )
        assert req.video_url == "https://www.youtube.com/watch?v=auJzb1D-fag"
        assert req.language == "en"

    def test_invalid_url(self):
        with pytest.raises(Exception):
            VideoProcessJobRequest(video_url="not-a-youtube-url")

    def test_short_url(self):
        req = VideoProcessJobRequest(
            video_url="https://youtu.be/auJzb1D-fag"
        )
        assert "youtu.be" in req.video_url


class TestVideoJobStatusResponse:
    def test_defaults(self):
        status = VideoJobStatusResponse(job_id="job_123", status=JobStatus.pending)
        assert status.progress == 0.0
        assert status.transcript is None
        assert status.error is None

    def test_complete(self):
        status = VideoJobStatusResponse(
            job_id="job_123",
            status=JobStatus.complete,
            progress=100.0,
            transcript="Hello world",
            metadata={"success": True},
        )
        assert status.status == JobStatus.complete
        assert status.transcript == "Hello world"

    def test_error_reason_field_present(self):
        """Failed jobs should be able to carry a structured error_reason slug."""
        status = VideoJobStatusResponse(
            job_id="job_fail",
            status=JobStatus.failed,
            error="Processing failed",
            error_reason="gemini_api_timeout",
        )
        assert status.error_reason == "gemini_api_timeout"

    def test_error_reason_defaults_to_none(self):
        """error_reason is optional and defaults to None (backward-compatible)."""
        status = VideoJobStatusResponse(job_id="job_ok", status=JobStatus.complete)
        assert status.error_reason is None


class TestExtractedEvent:
    def test_defaults(self):
        event = ExtractedEvent(type="action", title="Build a thing")
        assert event.id.startswith("evt_")
        assert event.confidence == 1.0
        assert event.description is None


class TestEventExtractResponse:
    def test_empty(self):
        resp = EventExtractResponse()
        assert resp.events == []
        assert resp.event_count == 0


class TestAgentExecution:
    def test_defaults(self):
        exec_ = AgentExecution(agent_type="analyzer")
        assert exec_.agent_id.startswith("agent_")
        assert exec_.status == AgentStatus.queued
        assert exec_.progress == 0.0


class TestAgentDispatchResponse:
    def test_defaults(self):
        resp = AgentDispatchResponse()
        assert resp.dispatch_id.startswith("dsp_")
        assert resp.executions == []


class TestAgentDispatchRequest:
    def test_with_events(self):
        req = AgentDispatchRequest(events=[{"id": "e1"}], agent_types=["research"])
        assert len(req.events) == 1
        assert req.transcript is None

    def test_with_transcript(self):
        req = AgentDispatchRequest(transcript="Hello world")
        assert req.transcript == "Hello world"
        assert req.events == []


class TestJobStatusEnum:
    def test_values(self):
        assert JobStatus.pending == "pending"
        assert JobStatus.complete == "complete"
        assert JobStatus.failed == "failed"


class TestAgentStatusEnum:
    def test_values(self):
        assert AgentStatus.queued == "queued"
        assert AgentStatus.running == "running"
        assert AgentStatus.complete == "complete"


class TestKnowledgeIngestModels:
    def test_knowledge_ingest_request_accepts_optional_fields(self):
        req = KnowledgeIngestRequest(text="Insight", tags=["topic"], source="job_1")
        assert req.text == "Insight"
        assert req.tags == ["topic"]
        assert req.source == "job_1"

    def test_knowledge_ingest_response_shape(self):
        resp = KnowledgeIngestResponse(
            stored=True,
            id="kb_123",
            source="job_1",
            tags=["topic"],
            message="Stored insight in knowledge base",
        )
        assert resp.stored is True
        assert resp.tags == ["topic"]
