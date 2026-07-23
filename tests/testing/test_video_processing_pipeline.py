"""Integration tests for the current video-processing API route.

These tests exercise the real v1 router and ``VideoProcessingService`` while
keeping network-facing processors behind a deterministic fake.  They must not
fall back to an empty FastAPI application when an import changes: a missing
production route is a collection error, not a mock success path.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport

import youtube_extension.backend.api.v1.router as router_module
from youtube_extension.backend.services.video_processing_service import (
    VideoProcessingService,
)


@pytest.fixture
def processor() -> MagicMock:
    """Return the network boundary used by the real processing service."""
    fake = MagicMock()
    fake.get_cached_result = MagicMock(return_value=None)
    fake.process_video = AsyncMock(
        return_value={
            "video_data": {"id": "auJzb1D-fag", "title": "Test Video"},
            "actions": [],
            "transcript": [],
            "processing_time": 0.01,
        }
    )
    return fake


@pytest.fixture
def video_processing_service(processor: MagicMock) -> VideoProcessingService:
    """Use the real service with deterministic processor/cache dependencies."""
    factory = MagicMock()
    factory.create_processor.return_value = processor

    cache = MagicMock()
    cache.extract_video_id.side_effect = lambda url: url.rsplit("v=", 1)[-1]

    service = VideoProcessingService(
        video_processor_factory=factory,
        cache_service=cache,
    )
    service.use_langextract_fallback = False
    return service


@pytest_asyncio.fixture
async def async_client(
    video_processing_service: VideoProcessingService,
    monkeypatch: pytest.MonkeyPatch,
):
    """Create an isolated client around the real v1 router."""
    test_app = FastAPI()
    test_app.include_router(router_module.router)
    test_app.dependency_overrides[router_module.get_video_processing_service] = lambda: (
        video_processing_service
    )

    # Route tests must not append CloudEvents to the process-wide /tmp sink.
    monkeypatch.setattr(router_module, "_ce_publisher", None)

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_video_url() -> str:
    return "https://www.youtube.com/watch?v=auJzb1D-fag"


@pytest.fixture
def expected_video_data() -> dict:
    return {
        "id": "auJzb1D-fag",
        "title": "Advanced React Patterns Tutorial",
        "channel": "React Education Hub",
        "duration": "18:45",
        "view_count": 125000,
        "published_at": "2024-01-15T10:30:00Z",
        "description": (
            "Learn advanced React patterns including HOCs, render props, "
            "and compound components"
        ),
        "category": "Education",
        "language": "en",
    }


@pytest.fixture
def expected_actions() -> list[dict]:
    return [
        {
            "id": "action_1",
            "title": "Set up React development environment",
            "description": (
                "Install Node.js, create React app, and set up development tools"
            ),
            "category": "Setup",
            "priority": "high",
            "estimated_time": "15 minutes",
            "timestamp": 30,
            "prerequisites": [],
            "code_example": "npx create-react-app my-app\ncd my-app\nnpm start",
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
            "code_example": (
                "const withAuth = (WrappedComponent) => {\n"
                "  return (props) => {\n"
                "    return <WrappedComponent {...props} />;\n"
                "  };\n"
                "};"
            ),
        },
    ]


@pytest.fixture
def expected_transcript() -> list[dict]:
    return [
        {
            "start": 0.0,
            "duration": 4.5,
            "text": "Welcome to this React patterns tutorial",
        },
        {
            "start": 4.5,
            "duration": 6.2,
            "text": "Today we'll learn about Higher Order Components",
        },
        {
            "start": 10.7,
            "duration": 5.8,
            "text": "First, let's set up our development environment",
        },
        {
            "start": 16.5,
            "duration": 7.1,
            "text": "We'll start by creating a new React application",
        },
    ]


class TestVideoProcessingPipeline:
    """Exercise the real route/service contract with external I/O isolated."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_pipeline_success(
        self,
        async_client,
        processor,
        sample_video_url,
        expected_video_data,
        expected_actions,
        expected_transcript,
    ):
        processor.process_video.return_value = {
            "video_id": expected_video_data["id"],
            "video_data": expected_video_data,
            "actions": expected_actions,
            "transcript": expected_transcript,
            "processing_time": 0.25,
        }

        response = await async_client.post(
            "/api/v1/process-video",
            json={
                "video_url": sample_video_url,
                "options": {
                    "quality": "high",
                    "generate_actions": True,
                    "include_transcript": True,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["video_data"]["id"] == "auJzb1D-fag"
        assert data["video_data"]["title"] == expected_video_data["title"]
        assert data["video_data"]["duration"] == expected_video_data["duration"]
        assert len(data["actions"]) == 2
        assert data["actions"][0]["priority"] == "high"
        assert len(data["transcript"]) == 4
        assert data["transcript"][0]["text"] == expected_transcript[0]["text"]
        assert data["quality_score"] == pytest.approx(0.9)
        assert data["processing_time"] == pytest.approx(0.25)
        processor.process_video.assert_awaited_once_with(sample_video_url)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_with_caching(
        self,
        async_client,
        processor,
        sample_video_url,
    ):
        processor.get_cached_result.return_value = {
            "video_data": {"id": "cached_video", "title": "Cached Video"},
            "actions": [{"id": "cached_action", "title": "Cached Action"}],
            "transcript": [{"text": "Cached transcript"}],
            "processing_time": 0.1,
            "quality_score": 0.95,
            "cached": True,
        }

        response = await async_client.post(
            "/api/v1/process-video",
            json={"video_url": sample_video_url},
        )

        assert response.status_code == 200
        assert response.json()["cached"] is True
        assert response.json()["processing_time"] == pytest.approx(0.1)
        processor.process_video.assert_not_awaited()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_error_is_sanitized(
        self,
        async_client,
        processor,
        sample_video_url,
    ):
        processor.process_video.side_effect = RuntimeError(
            "upstream response contained credentials"
        )

        response = await async_client.post(
            "/api/v1/process-video",
            json={"video_url": sample_video_url},
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
        assert "credentials" not in response.text

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_partial_result(
        self,
        async_client,
        processor,
        sample_video_url,
        expected_video_data,
    ):
        processor.process_video.return_value = {
            "video_id": expected_video_data["id"],
            "video_data": expected_video_data,
            "actions": [],
            "transcript": [],
            "processing_time": 0.2,
            "errors": ["Transcript unavailable"],
        }

        response = await async_client.post(
            "/api/v1/process-video",
            json={"video_url": sample_video_url},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["video_data"]["id"] == "auJzb1D-fag"
        assert data["transcript"] == []
        assert data["actions"] == []
        assert data["errors"] == ["Transcript unavailable"]
        assert data["quality_score"] == pytest.approx(0.2)


class TestActionRouteIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_action_status_update(self, async_client):
        repository = MagicMock()
        repository.update.return_value = True

        with patch.object(
            router_module,
            "ActionRepository",
            return_value=repository,
        ):
            response = await async_client.put(
                "/api/v1/actions/action_123",
                json={
                    "completed": True,
                    "notes": "Completed successfully",
                },
            )

        assert response.status_code == 200
        assert response.json() == {"success": True}
        repository.update.assert_called_once_with(
            "action_123",
            completed=True,
            notes="Completed successfully",
        )


class TestPerformanceIntegration:
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_video_processing(
        self,
        async_client,
        processor,
    ):
        video_ids = [f"testvideo0{number}" for number in range(1, 6)]
        video_urls = [
            f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids
        ]

        async def process_video(url: str) -> dict:
            await asyncio.sleep(0)
            video_id = url.rsplit("v=", 1)[-1]
            return {
                "video_data": {"id": video_id, "title": "Test Video"},
                "actions": [],
                "transcript": [],
                "processing_time": 0.01,
            }

        processor.process_video.side_effect = process_video

        responses = await asyncio.gather(
            *(
                async_client.post(
                    "/api/v1/process-video",
                    json={"video_url": url},
                )
                for url in video_urls
            )
        )

        assert [response.status_code for response in responses] == [200] * 5
        assert {response.json()["video_data"]["id"] for response in responses} == set(
            video_ids
        )
        assert processor.process_video.await_count == 5


class TestQualityAssessmentIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_high_quality_processing_detection(
        self,
        async_client,
        processor,
        sample_video_url,
    ):
        processor.process_video.return_value = {
            "video_data": {
                "id": "auJzb1D-fag",
                "title": "Comprehensive Programming Tutorial",
                "channel": "Education Hub",
                "duration": "25:30",
                "view_count": 250000,
            },
            "actions": [
                {
                    "id": "action_1",
                    "title": "Setup Development Environment",
                    "description": "Detailed setup instructions",
                },
                {
                    "id": "action_2",
                    "title": "Implement Core Features",
                    "description": "Step-by-step implementation guide",
                },
            ],
            "transcript": [
                {"text": "Welcome to this tutorial", "start": 0, "duration": 3},
                {"text": "We'll cover everything", "start": 3, "duration": 4},
            ],
            "processing_time": 45.2,
        }

        response = await async_client.post(
            "/api/v1/process-video",
            json={"video_url": sample_video_url},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quality_score"] == pytest.approx(0.9)
        assert len(data["actions"]) == 2
        assert len(data["transcript"]) == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_result_receives_low_quality_score(
        self,
        async_client,
        processor,
        sample_video_url,
    ):
        processor.process_video.return_value = {
            "video_data": {"id": "auJzb1D-fag", "title": "Unknown Video"},
            "actions": [],
            "transcript": [],
            "processing_time": 0.001,
            "errors": ["No usable transcript or actions"],
        }

        response = await async_client.post(
            "/api/v1/process-video",
            json={
                "video_url": sample_video_url,
                "options": {"quality": "standard"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quality_score"] == pytest.approx(0.2)
        assert data["actions"] == []
        assert data["transcript"] == []


class TestErrorRecoveryIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_degraded_processor_result_is_preserved(
        self,
        async_client,
        processor,
        sample_video_url,
    ):
        processor.process_video.return_value = {
            "video_data": {"id": "auJzb1D-fag", "title": "Fallback Metadata"},
            "actions": [],
            "transcript": [{"text": "Recovered transcript"}],
            "processing_time": 0.3,
            "errors": ["AI analysis unavailable"],
        }

        response = await async_client.post(
            "/api/v1/process-video",
            json={"video_url": sample_video_url},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["video_data"]["title"] == "Fallback Metadata"
        assert data["errors"] == ["AI analysis unavailable"]
        assert data["quality_score"] == pytest.approx(0.7)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_timeout_returns_sanitized_server_error(
        self,
        async_client,
        processor,
        sample_video_url,
    ):
        processor.process_video.side_effect = asyncio.TimeoutError(
            "processor timed out after 30 seconds"
        )

        response = await async_client.post(
            "/api/v1/process-video",
            json={
                "video_url": sample_video_url,
                "options": {"timeout": 30},
            },
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
        assert "30 seconds" not in response.text
