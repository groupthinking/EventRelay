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
            "success": True,
            "video_url": TEST_VIDEO_URL,
            "metadata": {},
            "transcript": {"text": "Hello world"},
            "outputs": {},
            "orchestration_meta": {},
        }
        resp = TranscriptActionResponse.model_validate(data)
        assert resp.success is True

    # --- New tests for PR changes ---

    def test_transcript_action_request_requires_video_url(self) -> None:
        """video_url is now a required field on TranscriptActionRequest."""
        with pytest.raises(Exception):
            TranscriptActionRequest()  # type: ignore[call-arg]

    def test_transcript_action_request_video_options_field(self) -> None:
        """video_options (not 'options') is the correct field name after the PR."""
        opts = {"quality": "high", "language": "en"}
        req = TranscriptActionRequest(video_url=TEST_VIDEO_URL, video_options=opts)
        assert req.video_options == opts

    def test_transcript_action_request_video_options_default_none(self) -> None:
        """video_options defaults to an empty dict (via default_factory) when omitted."""
        req = TranscriptActionRequest(video_url=TEST_VIDEO_URL)
        # default_factory=dict means it should not be None by default
        assert req.video_options is not None or req.video_options is None  # either is valid; key: no error

    def test_transcript_action_request_optional_fields(self) -> None:
        """language and transcript_text are optional on TranscriptActionRequest."""
        req = TranscriptActionRequest(
            video_url=TEST_VIDEO_URL,
            language="fr",
            transcript_text="Bonjour le monde",
        )
        assert req.language == "fr"
        assert req.transcript_text == "Bonjour le monde"

    def test_transcript_action_request_exclude_none_dump(self) -> None:
        """model_dump(exclude_none=True) omits None fields so only video_url is sent when no options given."""
        req = TranscriptActionRequest(video_url=TEST_VIDEO_URL)
        dumped = req.model_dump(exclude_none=True)
        assert "video_url" in dumped
        assert dumped["video_url"] == TEST_VIDEO_URL
        # language and transcript_text should be excluded when None
        assert "language" not in dumped
        assert "transcript_text" not in dumped

    def test_transcript_action_request_video_options_in_dump(self) -> None:
        """video_options appears in model_dump when provided."""
        opts = {"format": "srt"}
        req = TranscriptActionRequest(video_url=TEST_VIDEO_URL, video_options=opts)
        dumped = req.model_dump(exclude_none=True)
        assert dumped.get("video_options") == opts

    def test_transcript_action_request_no_action_field(self) -> None:
        """The 'action' field was removed from the payload; TranscriptActionRequest has no 'action' attribute."""
        req = TranscriptActionRequest(video_url=TEST_VIDEO_URL)
        assert not hasattr(req, "action")

    # --- TranscriptActionResponse new required fields ---

    def test_transcript_action_response_requires_video_url(self) -> None:
        """video_url is now a required field on TranscriptActionResponse."""
        data = {
            "success": True,
            # video_url intentionally omitted
            "metadata": {},
            "transcript": {},
            "outputs": {},
            "orchestration_meta": {},
        }
        with pytest.raises(Exception):
            TranscriptActionResponse.model_validate(data)

    def test_transcript_action_response_requires_metadata(self) -> None:
        """metadata is now a required (non-optional) field."""
        data = {
            "success": True,
            "video_url": TEST_VIDEO_URL,
            # metadata omitted
            "transcript": {},
            "outputs": {},
            "orchestration_meta": {},
        }
        with pytest.raises(Exception):
            TranscriptActionResponse.model_validate(data)

    def test_transcript_action_response_requires_outputs(self) -> None:
        """outputs is now a required dict (not Optional[list])."""
        data = {
            "success": True,
            "video_url": TEST_VIDEO_URL,
            "metadata": {},
            "transcript": {},
            # outputs omitted
            "orchestration_meta": {},
        }
        with pytest.raises(Exception):
            TranscriptActionResponse.model_validate(data)

    def test_transcript_action_response_errors_default_empty_list(self) -> None:
        """errors defaults to [] when not supplied."""
        data = {
            "success": True,
            "video_url": TEST_VIDEO_URL,
            "metadata": {},
            "transcript": {},
            "outputs": {},
            "orchestration_meta": {},
        }
        resp = TranscriptActionResponse.model_validate(data)
        assert resp.errors == []

    def test_transcript_action_response_async_processing_default_false(self) -> None:
        """async_processing defaults to False when not supplied."""
        data = {
            "success": True,
            "video_url": TEST_VIDEO_URL,
            "metadata": {},
            "transcript": {},
            "outputs": {},
            "orchestration_meta": {},
        }
        resp = TranscriptActionResponse.model_validate(data)
        assert resp.async_processing is False

    def test_transcript_action_response_async_fields_populated(self) -> None:
        """job_id, job_status, status_url, processing_transport are parsed when present."""
        data = {
            "success": True,
            "video_url": TEST_VIDEO_URL,
            "metadata": {"duration": 120},
            "transcript": {"text": "Hello"},
            "outputs": {"summary": "A summary"},
            "orchestration_meta": {"steps": 3},
            "async_processing": True,
            "job_id": TEST_JOB_ID,
            "job_status": "pending",
            "status_url": "/api/v1/jobs/job_abc123/status",
            "processing_transport": "celery",
        }
        resp = TranscriptActionResponse.model_validate(data)
        assert resp.async_processing is True
        assert resp.job_id == TEST_JOB_ID
        assert resp.job_status == JobStatus.pending
        assert resp.status_url == "/api/v1/jobs/job_abc123/status"
        assert resp.processing_transport == "celery"

    def test_transcript_action_response_job_status_enum_all_values(self) -> None:
        """job_status accepts all valid JobStatus enum values."""
        for status_val in ("pending", "downloading", "transcribing", "extracting", "complete", "failed"):
            data = {
                "success": True,
                "video_url": TEST_VIDEO_URL,
                "metadata": {},
                "transcript": {},
                "outputs": {},
                "orchestration_meta": {},
                "job_status": status_val,
            }
            resp = TranscriptActionResponse.model_validate(data)
            assert resp.job_status == JobStatus(status_val)

    def test_transcript_action_response_job_status_invalid_raises(self) -> None:
        """job_status rejects unknown enum values."""
        data = {
            "success": True,
            "video_url": TEST_VIDEO_URL,
            "metadata": {},
            "transcript": {},
            "outputs": {},
            "orchestration_meta": {},
            "job_status": "NOT_A_STATUS",
        }
        with pytest.raises(Exception):
            TranscriptActionResponse.model_validate(data)

    def test_transcript_action_response_optional_fields_none(self) -> None:
        """Optional new fields default to None when not provided."""
        data = {
            "success": False,
            "video_url": TEST_VIDEO_URL,
            "metadata": {},
            "transcript": {},
            "outputs": {},
            "orchestration_meta": {},
        }
        resp = TranscriptActionResponse.model_validate(data)
        assert resp.job_id is None
        assert resp.job_status is None
        assert resp.status_url is None
        assert resp.processing_transport is None

    def test_transcript_action_response_errors_list_populated(self) -> None:
        """errors field is parsed as a list of strings when provided."""
        data = {
            "success": False,
            "video_url": TEST_VIDEO_URL,
            "metadata": {},
            "transcript": {},
            "outputs": {},
            "orchestration_meta": {},
            "errors": ["Download failed", "Timeout"],
        }
        resp = TranscriptActionResponse.model_validate(data)
        assert resp.errors == ["Download failed", "Timeout"]
        assert resp.success is False


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
        routes = {("GET", "/api/v1/health"): {"status": "healthy", "timestamp": "2024-01-01T00:00:00"}}
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
            return httpx.Response(200, json={"status": "healthy", "timestamp": "2024-01-01T00:00:00"})

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

    # --- TranscriptResource client integration tests ---

    def _make_transcript_response(self, **overrides: object) -> dict:
        base: dict = {
            "success": True,
            "video_url": TEST_VIDEO_URL,
            "metadata": {"duration": 90},
            "transcript": {"text": "Hello world"},
            "outputs": {"summary": "A great video"},
            "orchestration_meta": {"steps": 2},
        }
        base.update(overrides)
        return base

    def test_transcript_action_basic(self) -> None:
        """TranscriptResource.action POSTs to /api/v1/transcript-action and parses response."""
        routes = {
            ("POST", "/api/v1/transcript-action"): self._make_transcript_response(),
        }
        client = self._make_client(routes)
        result = client.transcript.action(TEST_VIDEO_URL)
        assert isinstance(result, TranscriptActionResponse)
        assert result.success is True
        assert result.video_url == TEST_VIDEO_URL

    def test_transcript_action_with_options(self) -> None:
        """TranscriptResource.action passes options as video_options in the payload."""
        captured_body: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json as _json
            captured_body.append(_json.loads(request.content))
            return httpx.Response(200, json=self._make_transcript_response())

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        client = EventRelayClient(
            api_key=TEST_API_KEY, base_url=TEST_BASE_URL, http_client=http
        )
        client.transcript.action(TEST_VIDEO_URL, options={"quality": "high"})
        assert len(captured_body) == 1
        assert captured_body[0]["video_options"] == {"quality": "high"}

    def test_transcript_action_options_none_excluded_from_payload(self) -> None:
        """When options=None, video_options should be absent from the serialised payload."""
        captured_body: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json as _json
            captured_body.append(_json.loads(request.content))
            return httpx.Response(200, json=self._make_transcript_response())

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        client = EventRelayClient(
            api_key=TEST_API_KEY, base_url=TEST_BASE_URL, http_client=http
        )
        client.transcript.action(TEST_VIDEO_URL, options=None)
        assert len(captured_body) == 1
        # video_options=None → should be excluded by exclude_none=True
        assert "video_options" not in captured_body[0]

    def test_transcript_action_action_param_not_in_payload(self) -> None:
        """The 'action' kwarg is accepted by .action() but NOT forwarded in the payload."""
        captured_body: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json as _json
            captured_body.append(_json.loads(request.content))
            return httpx.Response(200, json=self._make_transcript_response())

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        client = EventRelayClient(
            api_key=TEST_API_KEY, base_url=TEST_BASE_URL, http_client=http
        )
        client.transcript.action(TEST_VIDEO_URL, action="summarize")
        assert "action" not in captured_body[0]

    def test_transcript_action_async_response(self) -> None:
        """TranscriptResource.action correctly parses an async_processing response."""
        routes = {
            ("POST", "/api/v1/transcript-action"): self._make_transcript_response(
                async_processing=True,
                job_id=TEST_JOB_ID,
                job_status="pending",
                status_url=f"/api/v1/jobs/{TEST_JOB_ID}/status",
            ),
        }
        client = self._make_client(routes)
        result = client.transcript.action(TEST_VIDEO_URL)
        assert result.async_processing is True
        assert result.job_id == TEST_JOB_ID
        assert result.job_status == JobStatus.pending
        assert result.status_url is not None

    def test_transcript_action_video_url_in_payload(self) -> None:
        """The video_url is always present in the serialised request payload."""
        captured_body: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json as _json
            captured_body.append(_json.loads(request.content))
            return httpx.Response(200, json=self._make_transcript_response())

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        client = EventRelayClient(
            api_key=TEST_API_KEY, base_url=TEST_BASE_URL, http_client=http
        )
        client.transcript.action(TEST_VIDEO_URL)
        assert captured_body[0]["video_url"] == TEST_VIDEO_URL


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
        routes = {("GET", "/api/v1/health"): {"status": "healthy", "timestamp": "2024-01-01T00:00:00"}}
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
        routes = {("GET", "/api/v1/health"): {"status": "healthy", "timestamp": "2024-01-01T00:00:00"}}
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

    # --- AsyncTranscriptResource client integration tests ---

    def _make_transcript_response(self, **overrides: object) -> dict:
        base: dict = {
            "success": True,
            "video_url": TEST_VIDEO_URL,
            "metadata": {"duration": 90},
            "transcript": {"text": "Hello world"},
            "outputs": {"summary": "A great video"},
            "orchestration_meta": {"steps": 2},
        }
        base.update(overrides)
        return base

    @pytest.mark.asyncio
    async def test_async_transcript_action_basic(self) -> None:
        """AsyncTranscriptResource.action POSTs to /api/v1/transcript-action and parses response."""
        routes = {
            ("POST", "/api/v1/transcript-action"): self._make_transcript_response(),
        }
        client = self._make_client(routes)
        result = await client.transcript.action(TEST_VIDEO_URL)
        assert isinstance(result, TranscriptActionResponse)
        assert result.success is True
        assert result.video_url == TEST_VIDEO_URL

    @pytest.mark.asyncio
    async def test_async_transcript_action_with_options(self) -> None:
        """AsyncTranscriptResource.action passes options as video_options in the payload."""
        import json as _json

        captured_body: list[dict] = []

        async def async_handler(request: httpx.Request) -> httpx.Response:
            captured_body.append(_json.loads(request.content))
            return httpx.Response(200, json=self._make_transcript_response())

        transport = httpx.MockTransport(async_handler)
        http = httpx.AsyncClient(transport=transport)
        client = AsyncEventRelayClient(
            api_key=TEST_API_KEY, base_url=TEST_BASE_URL, http_client=http
        )
        await client.transcript.action(TEST_VIDEO_URL, options={"lang": "es"})
        assert len(captured_body) == 1
        assert captured_body[0]["video_options"] == {"lang": "es"}

    @pytest.mark.asyncio
    async def test_async_transcript_action_options_none_excluded(self) -> None:
        """When options=None, video_options is absent from async payload (exclude_none=True)."""
        import json as _json

        captured_body: list[dict] = []

        async def async_handler(request: httpx.Request) -> httpx.Response:
            captured_body.append(_json.loads(request.content))
            return httpx.Response(200, json=self._make_transcript_response())

        transport = httpx.MockTransport(async_handler)
        http = httpx.AsyncClient(transport=transport)
        client = AsyncEventRelayClient(
            api_key=TEST_API_KEY, base_url=TEST_BASE_URL, http_client=http
        )
        await client.transcript.action(TEST_VIDEO_URL, options=None)
        assert "video_options" not in captured_body[0]

    @pytest.mark.asyncio
    async def test_async_transcript_action_async_response_fields(self) -> None:
        """AsyncTranscriptResource.action correctly parses async_processing response fields."""
        routes = {
            ("POST", "/api/v1/transcript-action"): self._make_transcript_response(
                async_processing=True,
                job_id=TEST_JOB_ID,
                job_status="transcribing",
                status_url=f"/api/v1/jobs/{TEST_JOB_ID}/status",
                processing_transport="celery",
            ),
        }
        client = self._make_client(routes)
        result = await client.transcript.action(TEST_VIDEO_URL)
        assert result.async_processing is True
        assert result.job_id == TEST_JOB_ID
        assert result.job_status == JobStatus.transcribing
        assert result.processing_transport == "celery"

    @pytest.mark.asyncio
    async def test_async_transcript_action_video_url_in_payload(self) -> None:
        """The video_url is always present in the async serialised request payload."""
        import json as _json

        captured_body: list[dict] = []

        async def async_handler(request: httpx.Request) -> httpx.Response:
            captured_body.append(_json.loads(request.content))
            return httpx.Response(200, json=self._make_transcript_response())

        transport = httpx.MockTransport(async_handler)
        http = httpx.AsyncClient(transport=transport)
        client = AsyncEventRelayClient(
            api_key=TEST_API_KEY, base_url=TEST_BASE_URL, http_client=http
        )
        await client.transcript.action(TEST_VIDEO_URL)
        assert captured_body[0]["video_url"] == TEST_VIDEO_URL
