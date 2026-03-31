from __future__ import annotations

from types import SimpleNamespace

import pytest

import youtube_extension.services.cloud.cloud_tasks_queue as cloud_tasks_queue
from src.shared.youtube import RobustYouTubeMetadata
from youtube_extension.backend.api.v1.models import TranscriptActionRequest
from youtube_extension.backend.api.v1.router import _queue_transcript_action_job
from youtube_extension.services.cloud.cloud_tasks_queue import CloudTasksQueueService
from youtube_extension.services.workflows.transcript_action_workflow import (
    TranscriptActionWorkflow,
)


class _UnexpectedYouTubeService:
    async def __aenter__(self):
        raise AssertionError("YouTube service should not be entered for playlist URLs")

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_playlist_urls_fail_fast() -> None:
    workflow = TranscriptActionWorkflow(
        youtube_service_factory=lambda: _UnexpectedYouTubeService(),
        orchestrator=SimpleNamespace(),
        speech_service=SimpleNamespace(),
    )

    with pytest.raises(ValueError, match="Playlist URLs are not supported"):
        await workflow.run("https://www.youtube.com/playlist?list=PL1234567890")


@pytest.mark.asyncio
async def test_queue_transcript_action_job_uses_cloud_tasks(monkeypatch) -> None:
    async def _fake_enqueue(self, video_task, task_config=None) -> str:
        return task_config.task_name if task_config else video_task.video_id

    monkeypatch.setattr(cloud_tasks_queue, "CLOUD_TASKS_AVAILABLE", True)
    monkeypatch.setattr(CloudTasksQueueService, "initialize", lambda self: None)
    monkeypatch.setattr(CloudTasksQueueService, "close", lambda self: None)
    monkeypatch.setattr(
        CloudTasksQueueService,
        "enqueue_video_processing",
        _fake_enqueue,
    )

    request = TranscriptActionRequest(
        video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        language="en",
    )
    metadata = RobustYouTubeMetadata(
        video_id="auJzb1D-fag",
        title="Long Video",
        description="",
        channel_id="channel",
        channel_title="Channel",
        published_at="2024-01-01T00:00:00Z",
        duration="PT16M",
        view_count=100,
        like_count=10,
        comment_count=1,
        thumbnail_urls={},
        tags=[],
        category_id="28",
        default_language="en",
        default_audio_language="en",
        live_broadcast_content="none",
        transcript_available=True,
        transcript_segments=12,
        source_api="test",
    )

    result = await _queue_transcript_action_job(
        request,
        metadata=metadata,
        http_request=SimpleNamespace(base_url="http://testserver/"),
    )

    assert result["async_processing"] is True
    assert result["processing_transport"] == "cloud_tasks"
    assert result["status_url"] == "http://testserver/api/v1/videos/" + result["job_id"] + "/status"
