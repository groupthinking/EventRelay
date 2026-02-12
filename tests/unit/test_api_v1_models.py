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
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert req.video_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert req.language == "en"

    def test_invalid_url(self):
        with pytest.raises(Exception):
            VideoProcessJobRequest(video_url="not-a-youtube-url")

    def test_short_url(self):
        req = VideoProcessJobRequest(
            video_url="https://youtu.be/dQw4w9WgXcQ"
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
