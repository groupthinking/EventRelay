"""
Tests for the EventRelay Python SDK.

These tests validate the SDK types and client logic without requiring
a running EventRelay server, using httpx's mock transport.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the SDK importable without installation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk" / "python"))

import httpx

from eventrelay_sdk import (
    AsyncEventRelayClient,
    EventRelayClient,
)
from eventrelay_sdk.types import (
    AgentDispatchRequest,
    AgentDispatchResponse,
    AgentExecution,
    AgentStatus,
    AgentStatusResponse,
    ChatRequest,
    EventExtractRequest,
    EventExtractResponse,
    ExtractedEvent,
    HealthResponse,
    JobStatus,
    TranscriptActionRequest,
    TranscriptActionResponse,
    VideoJobStatusResponse,
    VideoProcessJobRequest,
    VideoProcessJobResponse,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_VIDEO_URL = "https://www.youtube.com/watch?v=auJzb1D-fag"
TEST_JOB_ID = "job_abc123"
TEST_AGENT_ID = "agent_def456"
TEST_DISPATCH_ID = "dsp_ghi789"
TEST_API_KEY = "test-api-key"
TEST_BASE_URL = "http://localhost:8000"


def _mock_transport(responses: dict[tuple[str, str], dict]) -> httpx.MockTransport:
    """Build an httpx MockTransport from a (method, path) → response dict."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key in responses:
            return httpx.Response(200, json=responses[key])
        return httpx.Response(404, json={"detail": "Not found"})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Type model tests
# ---------------------------------------------------------------------------


class TestVideoModels:
    def test_video_process_request_valid(self) -> None:
        req = VideoProcessJobRequest(video_url=TEST_VIDEO_URL)
        assert req.video_url == TEST_VIDEO_URL
        assert req.language == "en"

    def test_video_process_response_parse(self) -> None:
        data = {"job_id": TEST_JOB_ID, "video_url": TEST_VIDEO_URL, "status": "pending"}
        resp = VideoProcessJobResponse.model_validate(data)
        assert resp.job_id == TEST_JOB_ID
        assert resp.status == JobStatus.pending

    def test_video_job_status_response_parse(self) -> None:
        data = {
            "job_id": TEST_JOB_ID,
            "status": "complete",
            "progress": 100.0,
            "transcript": "Hello world",
        }
        resp = VideoJobStatusResponse.model_validate(data)
        assert resp.status == JobStatus.complete
        assert resp.progress == 100.0


class TestEventModels:
    def test_event_extract_request(self) -> None:
        req = EventExtractRequest(transcript="Speaker discussed React hooks.")
        assert req.transcript == "Speaker discussed React hooks."
        assert req.job_id is None

    def test_extracted_event_parse(self) -> None:
        data = {
            "id": "evt_001",
            "type": "action",
            "title": "Build weather app",
            "confidence": 0.95,
        }
        event = ExtractedEvent.model_validate(data)
        assert event.type == "action"
        assert event.confidence == 0.95

    def test_event_extract_response_parse(self) -> None:
        data = {
            "job_id": TEST_JOB_ID,
            "events": [
                {"id": "evt_001", "type": "topic", "title": "React", "confidence": 1.0}
            ],
            "event_count": 1,
        }
        resp = EventExtractResponse.model_validate(data)
        assert resp.event_count == 1
        assert resp.events[0].title == "React"


class TestAgentModels:
    def test_agent_dispatch_request(self) -> None:
        req = AgentDispatchRequest(
            events=[{"id": "evt_001", "type": "action", "title": "Build app"}],
            agent_types=["code_generator"],
        )
        assert len(req.events) == 1
        assert req.agent_types == ["code_generator"]

    def test_agent_execution_parse(self) -> None:
        data = {
            "agent_id": TEST_AGENT_ID,
            "agent_type": "code_generator",
            "status": "queued",
            "progress": 0.0,
        }
        execution = AgentExecution.model_validate(data)
        assert execution.status == AgentStatus.queued

    def test_agent_dispatch_response_parse(self) -> None:
        data = {
            "dispatch_id": TEST_DISPATCH_ID,
            "executions": [
                {
                    "agent_id": TEST_AGENT_ID,
                    "agent_type": "code_generator",
                    "status": "queued",
                    "progress": 0.0,
                }
            ],
        }
        resp = AgentDispatchResponse.model_validate(data)
        assert resp.dispatch_id == TEST_DISPATCH_ID
        assert len(resp.executions) == 1

    def test_agent_status_response_parse(self) -> None:
        data = {
            "agent_id": TEST_AGENT_ID,
            "agent_type": "code_generator",
            "status": "complete",
            "progress": 100.0,
        }
        resp = AgentStatusResponse.model_validate(data)
        assert resp.status == AgentStatus.complete


class TestHealthModels:
    def test_health_response_parse(self) -> None:
        data = {"status": "healthy", "version": "2.0.0", "timestamp": "2024-01-01T00:00:00"}
        resp = HealthResponse.model_validate(data)
        assert resp.status == "healthy"
        assert resp.version == "2.0.0"


class TestChatModels:
    def test_chat_request(self) -> None:
        req = ChatRequest(query="What is this video about?")
        assert req.query == "What is this video about?"
        assert req.context == "tooltip-assistant"


class TestTranscriptModels:
    def test_transcript_action_request(self) -> None:
        req = TranscriptActionRequest(video_url=TEST_VIDEO_URL)
        assert req.video_url == TEST_VIDEO_URL

    def test_transcript_action_response_parse(self) -> None:
        data = {
            "video_url": TEST_VIDEO_URL,
            "transcript": {"text": "Hello world"},
            "actions": [],
            "status": "success",
        }
        resp = TranscriptActionResponse.model_validate(data)
        assert resp.status == "success"


# ---------------------------------------------------------------------------
# Synchronous client tests (using mock transport)
# ---------------------------------------------------------------------------


class TestEventRelayClient:
    def _make_client(self, routes: dict) -> EventRelayClient:
        transport = _mock_transport(routes)
        http = httpx.Client(transport=transport)
        return EventRelayClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
            http_client=http,
        )

    def test_client_default_base_url(self) -> None:
        client = EventRelayClient()
        assert "uvai.io" in client._base_url

    def test_client_custom_base_url(self) -> None:
        client = EventRelayClient(base_url="http://localhost:9000")
        assert client._base_url == "http://localhost:9000"

    def test_client_strips_trailing_slash(self) -> None:
        client = EventRelayClient(base_url="http://localhost:8000/")
        assert not client._base_url.endswith("/")

    def test_client_api_key_in_headers(self) -> None:
        client = EventRelayClient(api_key="secret-key")
        assert client._headers()["X-API-Key"] == "secret-key"

    def test_client_no_api_key_header_absent(self) -> None:
        client = EventRelayClient(api_key="")
        assert "X-API-Key" not in client._headers()

    def test_videos_process(self) -> None:
        routes = {
            ("POST", "/api/v1/videos/process"): {
                "job_id": TEST_JOB_ID,
                "video_url": TEST_VIDEO_URL,
                "status": "pending",
            }
        }
        client = self._make_client(routes)
        result = client.videos.process(TEST_VIDEO_URL)
        assert isinstance(result, VideoProcessJobResponse)
        assert result.job_id == TEST_JOB_ID
        assert result.status == JobStatus.pending

    def test_videos_get_status(self) -> None:
        routes = {
            ("GET", f"/api/v1/videos/{TEST_JOB_ID}/status"): {
                "job_id": TEST_JOB_ID,
                "status": "complete",
                "progress": 100.0,
            }
        }
        client = self._make_client(routes)
        result = client.videos.get_status(job_id=TEST_JOB_ID)
        assert isinstance(result, VideoJobStatusResponse)
        assert result.status == JobStatus.complete

    def test_events_extract(self) -> None:
        routes = {
            ("POST", "/api/v1/events/extract"): {
                "job_id": TEST_JOB_ID,
                "events": [
                    {"id": "evt_001", "type": "action", "title": "Build app", "confidence": 0.9}
                ],
                "event_count": 1,
            }
        }
        client = self._make_client(routes)
        result = client.events.extract(transcript="Build a React app from scratch.")
        assert isinstance(result, EventExtractResponse)
        assert result.event_count == 1
        assert result.events[0].type == "action"

    def test_agents_dispatch(self) -> None:
        routes = {
            ("POST", "/api/v1/agents/dispatch"): {
                "dispatch_id": TEST_DISPATCH_ID,
                "executions": [
                    {
                        "agent_id": TEST_AGENT_ID,
                        "agent_type": "code_generator",
                        "status": "queued",
                        "progress": 0.0,
                    }
                ],
            }
        }
        client = self._make_client(routes)
        result = client.agents.dispatch(
            events=[{"id": "evt_001", "type": "action", "title": "Build app"}]
        )
        assert isinstance(result, AgentDispatchResponse)
        assert result.dispatch_id == TEST_DISPATCH_ID
        assert len(result.executions) == 1

    def test_agents_get_status(self) -> None:
        routes = {
            ("GET", f"/api/v1/agents/{TEST_AGENT_ID}/status"): {
                "agent_id": TEST_AGENT_ID,
                "agent_type": "code_generator",
                "status": "complete",
                "progress": 100.0,
            }
        }
        client = self._make_client(routes)
        result = client.agents.get_status(TEST_AGENT_ID)
        assert isinstance(result, AgentStatusResponse)
        assert result.status == AgentStatus.complete

    def test_health_check(self) -> None:
        routes = {("GET", "/api/v1/health"): {"status": "healthy", "timestamp": "2024-01-01T00:00:00"}}
        client = self._make_client(routes)
        result = client.health.check()
        assert isinstance(result, HealthResponse)
        assert result.status == "healthy"

    def test_health_detailed(self) -> None:
        routes = {
            ("GET", "/api/v1/health/detailed"): {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00",
                "components": {"database": "ok", "cache": "ok"},
            }
        }
        client = self._make_client(routes)
        result = client.health.detailed()
        assert isinstance(result, HealthResponse)
        assert result.components is not None

    def test_client_context_manager(self) -> None:
        routes = {("GET", "/api/v1/health"): {"status": "healthy"}}
        with self._make_client(routes) as client:
            result = client.health.check()
        assert result.status == "healthy"

    def test_client_retry_on_500(self) -> None:
        """Client should retry on 500 and succeed on subsequent attempt."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return httpx.Response(500)
            return httpx.Response(200, json={"status": "healthy"})

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        client = EventRelayClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
            http_client=http,
            max_retries=2,
        )
        result = client.health.check()
        assert result.status == "healthy"
        assert call_count == 2

    def test_client_raises_on_404(self) -> None:
        """Client should raise immediately on non-retryable error codes."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"detail": "Not found"})

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        client = EventRelayClient(base_url=TEST_BASE_URL, http_client=http)
        with pytest.raises(httpx.HTTPStatusError):
            client.health.check()


# ---------------------------------------------------------------------------
# Async client tests
# ---------------------------------------------------------------------------


class TestAsyncEventRelayClient:
    def _make_client(self, routes: dict) -> AsyncEventRelayClient:
        transport = _mock_transport(routes)
        http = httpx.AsyncClient(transport=transport)
        return AsyncEventRelayClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
            http_client=http,
        )

    @pytest.mark.asyncio
    async def test_async_health_check(self) -> None:
        routes = {("GET", "/api/v1/health"): {"status": "healthy"}}
        client = self._make_client(routes)
        result = await client.health.check()
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_async_videos_process(self) -> None:
        routes = {
            ("POST", "/api/v1/videos/process"): {
                "job_id": TEST_JOB_ID,
                "video_url": TEST_VIDEO_URL,
                "status": "pending",
            }
        }
        client = self._make_client(routes)
        result = await client.videos.process(TEST_VIDEO_URL)
        assert result.job_id == TEST_JOB_ID

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        routes = {("GET", "/api/v1/health"): {"status": "healthy"}}
        async with self._make_client(routes) as client:
            result = await client.health.check()
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_async_events_extract(self) -> None:
        routes = {
            ("POST", "/api/v1/events/extract"): {
                "events": [
                    {"id": "evt_001", "type": "topic", "title": "React", "confidence": 1.0}
                ],
                "event_count": 1,
            }
        }
        client = self._make_client(routes)
        result = await client.events.extract(transcript="Intro to React.")
        assert len(result.events) == 1

    @pytest.mark.asyncio
    async def test_async_agents_dispatch(self) -> None:
        routes = {
            ("POST", "/api/v1/agents/dispatch"): {
                "dispatch_id": TEST_DISPATCH_ID,
                "executions": [],
            }
        }
        client = self._make_client(routes)
        result = await client.agents.dispatch(transcript="Build a React app.")
        assert result.dispatch_id == TEST_DISPATCH_ID
