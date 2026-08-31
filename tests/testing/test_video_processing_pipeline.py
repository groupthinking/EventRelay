"""Contract tests for the production v1 video-processing HTTP route.

The processing service is replaced at FastAPI's dependency boundary, so these
tests intentionally verify request validation, delegation, and response
passthrough.  Provider selection and retry behaviour are covered at their real
boundary in ``tests/unit/test_unified_ai_sdk.py``.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

# Import the production ASGI application.  The former ``main_v2`` import no
# longer exists; catching that ImportError silently replaced the application
# with an empty FastAPI instance and made every endpoint assertion a 404.
from src.youtube_extension.backend.api.v1 import router as router_module
from src.youtube_extension.backend.api.v1.router import get_video_processing_service
from src.youtube_extension.backend.main import app


@pytest.fixture
def video_service(monkeypatch):
    """Provide a deterministic service while exercising the real API stack."""
    # The production router's file publisher is intentionally module-global.
    # Contract tests verify HTTP delegation, not durable CloudEvent delivery;
    # disabling it here prevents hidden writes to /tmp/cloudevents.jsonl.
    monkeypatch.setattr(router_module, "_ce_publisher", None)
    service = Mock()
    service.process_video_basic = AsyncMock(
        return_value={
            "video_data": {"id": "default", "title": "Default"},
            "actions": [],
            "transcript": [],
            "processing_time": 0.1,
            "quality_score": 0.5,
        }
    )
    app.dependency_overrides[get_video_processing_service] = lambda: service
    try:
        yield service
    finally:
        app.dependency_overrides.pop(get_video_processing_service, None)


@pytest_asyncio.fixture
async def async_client(video_service):
    """Create async HTTP client for API testing (httpx >= 0.25)."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
def sample_video_url():
    """Sample YouTube video URL for testing"""
    return "https://www.youtube.com/watch?v=jNQXAC9IVRw"

@pytest.fixture
def expected_video_data():
    """Expected video data structure"""
    return {
        "id": "jNQXAC9IVRw",
        "title": "Advanced React Patterns Tutorial",
        "channel": "React Education Hub",
        "duration": "18:45",
        "view_count": 125000,
        "published_at": "2024-01-15T10:30:00Z",
        "description": "Learn advanced React patterns including HOCs, render props, and compound components",
        "category": "Education",
        "language": "en"
    }

@pytest.fixture
def expected_actions():
    """Expected actions structure"""
    return [
        {
            "id": "action_1",
            "title": "Set up React development environment",
            "description": "Install Node.js, create React app, and set up development tools",
            "category": "Setup",
            "priority": "high",
            "estimated_time": "15 minutes",
            "timestamp": 30,
            "prerequisites": [],
            "code_example": "npx create-react-app my-app\ncd my-app\nnpm start"
        },
        {
            "id": "action_2",
            "title": "Implement Higher Order Component pattern",
            "description": "Create a HOC for adding authentication logic",
            "category": "Implementation",
            "priority": "medium",
            "estimated_time": "25 minutes",
            "timestamp": 300,
            "prerequisites": ["action_1"],
            "code_example": "const withAuth = (WrappedComponent) => {\n  return (props) => {\n    // Auth logic here\n    return <WrappedComponent {...props} />;\n  };\n};"
        }
    ]

@pytest.fixture
def expected_transcript():
    """Expected transcript structure"""
    return [
        SimpleNamespace(start=0.0, duration=4.5, text="Welcome to this React patterns tutorial"),
        SimpleNamespace(start=4.5, duration=6.2, text="Today we'll learn about Higher Order Components"),
        SimpleNamespace(start=10.7, duration=5.8, text="First, let's set up our development environment"),
        SimpleNamespace(start=16.5, duration=7.1, text="We'll start by creating a new React application")
    ]

class TestVideoProcessingApiContract:
    """Verify the public HTTP contract against the real production router."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_process_video_forwards_url_and_options(
        self,
        async_client,
        video_service,
        sample_video_url,
        expected_video_data,
        expected_actions,
        expected_transcript,
    ):
        """The route forwards the exact request and returns the service result."""
        video_service.process_video_basic.return_value = {
            "video_data": expected_video_data,
            "actions": expected_actions,
            "transcript": [vars(segment) for segment in expected_transcript],
            "processing_time": 0.25,
            "quality_score": 0.9,
        }

        options = {
            "quality": "high",
            "generate_actions": True,
            "include_transcript": True,
        }
        response = await async_client.post("/api/v1/process-video", json={
            "video_url": sample_video_url,
            "options": options,
        })

        assert response.status_code == 200
        data = response.json()
        assert {
            "video_data",
            "actions",
            "transcript",
            "processing_time",
            "quality_score",
        } <= data.keys()
        assert data["video_data"]["id"] == "jNQXAC9IVRw"
        assert data["video_data"]["title"] == expected_video_data["title"]
        assert data["video_data"]["duration"] == expected_video_data["duration"]
        assert len(data["actions"]) == 2
        assert data["actions"][0]["priority"] == "high"
        assert len(data["transcript"]) == 4
        assert data["transcript"][0]["text"] == "Welcome to this React patterns tutorial"
        assert data["quality_score"] >= 0.8
        assert data["processing_time"] > 0
        video_service.process_video_basic.assert_awaited_once_with(
            sample_video_url, options
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cached_service_result_is_preserved(
        self, async_client, video_service, sample_video_url
    ):
        """The route does not discard cache metadata returned by the service."""
        video_service.process_video_basic.return_value = {
            "video_data": {"id": "cached_video", "title": "Cached Video"},
            "actions": [{"id": "cached_action", "title": "Cached Action"}],
            "transcript": [{"text": "Cached transcript"}],
            "processing_time": 0.1,
            "quality_score": 0.95,
            "cached": True,
        }

        response = await async_client.post("/api/v1/process-video", json={
            "video_url": sample_video_url
        })

        assert response.status_code == 200
        data = response.json()
        assert data["cached"] is True
        assert data["processing_time"] < 1.0
        video_service.process_video_basic.assert_awaited_once_with(
            sample_video_url, {}
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_degraded_service_result_is_preserved(
        self, async_client, video_service, sample_video_url
    ):
        """A successful degraded result remains a 200 response."""
        video_service.process_video_basic.return_value = {
            "video_data": {"id": "jNQXAC9IVRw", "title": "Unknown Video"},
            "actions": [],
            "transcript": [],
            "processing_time": 0.1,
            "quality_score": 0.2,
            "errors": ["Video not found"],
        }

        response = await async_client.post("/api/v1/process-video", json={
            "video_url": sample_video_url
        })

        assert response.status_code == 200
        data = response.json()
        assert data["video_data"]["id"] == "jNQXAC9IVRw"
        assert data["actions"] == []
        assert data["transcript"] == []
        assert data["quality_score"] <= 0.8
        video_service.process_video_basic.assert_awaited_once_with(
            sample_video_url, {}
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_partial_service_result_is_preserved(
        self, async_client, video_service, sample_video_url, expected_video_data
    ):
        """Partial provider output is returned without changing its contract."""
        video_service.process_video_basic.return_value = {
            "video_data": expected_video_data,
            "actions": [],
            "transcript": [],
            "processing_time": 0.2,
            "quality_score": 0.5,
            "errors": ["Transcript unavailable"],
        }

        response = await async_client.post("/api/v1/process-video", json={
            "video_url": sample_video_url
        })

        assert response.status_code == 200
        data = response.json()
        assert data["video_data"]["id"] == "jNQXAC9IVRw"
        assert data["transcript"] == []
        assert data["actions"] == []
        assert data["quality_score"] < 0.8
        video_service.process_video_basic.assert_awaited_once_with(
            sample_video_url, {}
        )

class TestDatabaseIntegration:
    """Test database integration for storing results"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_action_status_update(self, async_client):
        """The action route delegates the exact update to its repository."""
        repository = Mock()
        repository.update.return_value = {"id": "action_123", "completed": True}
        payload = {
            "completed": True,
            "notes": "Completed successfully",
        }

        with patch(
            'src.youtube_extension.backend.api.v1.router.ActionRepository',
            return_value=repository,
        ):
            response = await async_client.put("/api/v1/actions/action_123", json={
                **payload,
            })

        assert response.status_code == 200
        assert response.json() == {"success": True}
        repository.update.assert_called_once_with("action_123", **payload)

class TestVideoProcessingConcurrencyContract:
    """Verify concurrent valid requests reach the service boundary."""

    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_video_processing(self, async_client, video_service):
        """Every valid concurrent request succeeds; validation errors are failures."""
        video_urls = [
            "https://youtube.com/watch?v=test0000001",
            "https://youtube.com/watch?v=test0000002",
            "https://youtube.com/watch?v=test0000003",
            "https://youtube.com/watch?v=test0000004",
            "https://youtube.com/watch?v=test0000005",
        ]

        responses = await asyncio.gather(*(
            async_client.post(
                "/api/v1/process-video", json={"video_url": url}
            )
            for url in video_urls
        ))

        assert [response.status_code for response in responses] == [200] * 5
        assert video_service.process_video_basic.await_count == 5
        video_service.process_video_basic.assert_has_awaits(
            [call(url, {}) for url in video_urls], any_order=True
        )

class TestVideoProcessingResponseContract:
    """Verify quality fields and request validation at the HTTP boundary."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_high_quality_processing_detection(
        self, async_client, video_service, sample_video_url
    ):
        """Test detection of high-quality processing results"""
        video_service.process_video_basic.return_value = {
            "video_data": {
                "id": "test123",
                "title": "Comprehensive Programming Tutorial",
                "channel": "Education Hub",
                "duration": "25:30",
                "view_count": 250000,
            },
            "actions": [
                {
                    "id": "action_1",
                    "title": "Setup Development Environment",
                    "description": "Detailed setup instructions with code examples",
                    "code_example": "npm install\nnpm start",
                },
                {
                    "id": "action_2",
                    "title": "Implement Core Features",
                    "description": "Step-by-step implementation guide",
                    "code_example": "const component = () => { return <div>Hello</div>; };",
                },
            ],
            "transcript": [
                {"text": "Welcome to this comprehensive tutorial", "start": 0, "duration": 3},
                {"text": "We'll cover everything you need to know", "start": 3, "duration": 4},
            ],
            "processing_time": 45.2,
            "quality_score": 0.95,
            "errors": [],
        }

        response = await async_client.post("/api/v1/process-video", json={
            "video_url": sample_video_url
        })

        assert response.status_code == 200
        data = response.json()
        assert data["quality_score"] >= 0.9
        assert len(data["actions"]) == 2
        assert len(data["transcript"]) == 2
        video_service.process_video_basic.assert_awaited_once_with(
            sample_video_url, {}
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_video_url_is_rejected_before_service(
        self, async_client, video_service
    ):
        """An invalid YouTube identifier never reaches a provider."""
        response = await async_client.post("/api/v1/process-video", json={
            "video_url": "https://youtube.com/watch?v=too-short",
            "options": {"quality": "standard"},
        })

        assert response.status_code == 422
        video_service.process_video_basic.assert_not_awaited()

class TestVideoProcessingErrorContract:
    """Verify recovered results and unrecovered exceptions at the route."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_recovered_provider_result_is_returned(
        self, async_client, video_service, sample_video_url
    ):
        """A result recovered below the route is returned unchanged.

        Provider retry counts and retryable classifications are tested in
        ``tests/unit/test_unified_ai_sdk.py`` rather than mocked here.
        """
        video_service.process_video_basic.return_value = {
            "video_data": {"id": "jNQXAC9IVRw", "title": "Recovered video"},
            "actions": [],
            "transcript": [],
            "processing_time": 0.3,
            "quality_score": 0.4,
            "errors": ["Primary provider unavailable; fallback used"],
        }

        response = await async_client.post("/api/v1/process-video", json={
            "video_url": sample_video_url
        })

        assert response.status_code == 200
        assert response.json()["video_data"]["id"] == "jNQXAC9IVRw"
        video_service.process_video_basic.assert_awaited_once_with(
            sample_video_url, {}
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_timeout_recovery(self, async_client, video_service, sample_video_url):
        """Test recovery from processing timeouts"""
        video_service.process_video_basic.side_effect = asyncio.TimeoutError(
            "Processing timeout"
        )

        response = await async_client.post("/api/v1/process-video", json={
            "video_url": sample_video_url,
            "options": {"timeout": 30}
        })

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
        video_service.process_video_basic.assert_awaited_once_with(
            sample_video_url, {"timeout": 30}
        )
