"""Unit tests for services/cloud/cloud_video_processor.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Evict any MagicMock stub that test_cloud_routes.py may have registered via
# sys.modules.setdefault() during pytest collection (which runs before tests
# execute). The parent package youtube_extension.services.cloud is a real
# module (imported by router.py), so Python can still locate the real file.
# ---------------------------------------------------------------------------
_cvp_key = "youtube_extension.services.cloud.cloud_video_processor"
if isinstance(sys.modules.get(_cvp_key), MagicMock):
    del sys.modules[_cvp_key]

# ---------------------------------------------------------------------------
# Module-level import alias (resolved once; importable in all tests)
# ---------------------------------------------------------------------------
import youtube_extension.services.cloud.cloud_video_processor as _mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_firestore_service(state=None):
    """Return an AsyncMock-based firestore service."""
    svc = MagicMock()
    svc.create_state = AsyncMock(return_value=None)
    svc.get_state = AsyncMock(return_value=state)
    svc.update_state = AsyncMock(return_value=None)
    return svc


def _make_tasks_service(task_id="task-123"):
    """Return a mock cloud tasks service."""
    svc = MagicMock()
    svc.enqueue_video_processing = AsyncMock(return_value=task_id)
    svc.enqueue_batch = AsyncMock(return_value=[task_id])
    return svc


def _make_vertex_service(response_text="AI summary"):
    """Return a mock vertex AI service."""
    from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse

    svc = MagicMock()
    svc.analyze_transcript = AsyncMock(
        return_value=AgentResponse(
            text=response_text,
            metadata={},
            usage={"total_tokens": 50},
        )
    )
    return svc


def _make_completed_state(video_id="auJzb1D-fag", video_url="https://youtube.com/watch?v=auJzb1D-fag"):
    """Return a VideoProcessingState that looks 'completed'."""
    from youtube_extension.services.cloud.firestore_state import VideoProcessingState

    return VideoProcessingState(
        video_id=video_id,
        video_url=video_url,
        status="completed",
        current_stage="complete",
        metadata={"title": "Cached Video"},
        transcript={"text": "cached transcript"},
        ai_analysis={"summary": "cached summary"},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure the module-level singleton is cleared between tests."""
    _mod._cloud_video_processor = None
    yield
    _mod._cloud_video_processor = None


@pytest.fixture()
def mock_services():
    """Patch the three cloud service factory functions used inside the module."""
    firestore_svc = _make_firestore_service()
    tasks_svc = _make_tasks_service()
    vertex_svc = _make_vertex_service()

    with (
        patch.object(_mod, "get_firestore_service", new=AsyncMock(return_value=firestore_svc)),
        patch.object(_mod, "get_cloud_tasks_service", return_value=tasks_svc),
        patch.object(_mod, "get_vertex_ai_service", return_value=vertex_svc),
    ):
        yield {
            "firestore": firestore_svc,
            "tasks": tasks_svc,
            "vertex": vertex_svc,
        }


@pytest.fixture()
def processor(mock_services):
    """Return a fully-enabled CloudNativeVideoProcessor with all services mocked."""
    from youtube_extension.services.cloud.cloud_video_processor import (
        CloudNativeVideoProcessor,
    )

    return CloudNativeVideoProcessor(
        enable_queue=True,
        enable_state=True,
        enable_vertex_ai=True,
    )


# ---------------------------------------------------------------------------
# 1. VideoProcessingResult dataclass
# ---------------------------------------------------------------------------

class TestVideoProcessingResult:
    def test_required_fields(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            VideoProcessingResult,
        )

        r = VideoProcessingResult(video_id="abc", video_url="https://yt.be/abc", success=True)
        assert r.video_id == "abc"
        assert r.video_url == "https://yt.be/abc"
        assert r.success is True

    def test_optional_defaults(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            VideoProcessingResult,
        )

        r = VideoProcessingResult(video_id="x", video_url="u", success=False)
        assert r.metadata is None
        assert r.transcript is None
        assert r.ai_analysis is None
        assert r.error_message is None
        assert r.processing_time == 0.0
        assert r.from_cache is False

    def test_all_fields_set(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            VideoProcessingResult,
        )

        r = VideoProcessingResult(
            video_id="vid",
            video_url="url",
            success=True,
            metadata={"title": "t"},
            transcript={"text": "tx"},
            ai_analysis={"summary": "s"},
            error_message=None,
            processing_time=3.14,
            from_cache=True,
        )
        assert r.processing_time == pytest.approx(3.14)
        assert r.from_cache is True
        assert r.metadata["title"] == "t"

    def test_failed_result(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            VideoProcessingResult,
        )

        r = VideoProcessingResult(
            video_id="v",
            video_url="u",
            success=False,
            error_message="something went wrong",
        )
        assert r.success is False
        assert r.error_message == "something went wrong"


# ---------------------------------------------------------------------------
# 2. CloudNativeVideoProcessor.__init__
# ---------------------------------------------------------------------------

class TestCloudNativeVideoProcessorInit:
    def test_default_flags_all_true(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor()
        assert p.enable_queue is True
        assert p.enable_state is True
        assert p.enable_vertex_ai is True

    def test_custom_flags(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor(enable_queue=False, enable_state=False, enable_vertex_ai=False)
        assert p.enable_queue is False
        assert p.enable_state is False
        assert p.enable_vertex_ai is False

    def test_mixed_flags(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor(enable_queue=True, enable_state=False, enable_vertex_ai=True)
        assert p.enable_queue is True
        assert p.enable_state is False
        assert p.enable_vertex_ai is True


# ---------------------------------------------------------------------------
# 3. _extract_video_id
# ---------------------------------------------------------------------------

class TestExtractVideoId:
    def test_full_youtube_url(self, processor):
        assert processor._extract_video_id("https://www.youtube.com/watch?v=auJzb1D-fag") == "auJzb1D-fag"

    def test_youtube_url_with_extra_params(self, processor):
        assert processor._extract_video_id("https://youtube.com/watch?v=auJzb1D-fag&t=42") == "auJzb1D-fag"

    def test_short_url(self, processor):
        assert processor._extract_video_id("https://youtu.be/auJzb1D-fag") == "auJzb1D-fag"

    def test_short_url_with_params(self, processor):
        assert processor._extract_video_id("https://youtu.be/auJzb1D-fag?t=10") == "auJzb1D-fag"

    def test_bare_id_passthrough(self, processor):
        assert processor._extract_video_id("auJzb1D-fag") == "auJzb1D-fag"


# ---------------------------------------------------------------------------
# 4. process_video_async – queue enabled
# ---------------------------------------------------------------------------

class TestProcessVideoAsync:
    async def test_returns_task_id(self, processor, mock_services):
        task_id = await processor.process_video_async("https://youtube.com/watch?v=abc123")
        assert task_id == "task-123"

    async def test_firestore_state_created(self, processor, mock_services):
        await processor.process_video_async("https://youtube.com/watch?v=abc123")
        mock_services["firestore"].create_state.assert_awaited_once_with("abc123", "https://youtube.com/watch?v=abc123")

    async def test_task_enqueued_with_correct_video(self, processor, mock_services):
        await processor.process_video_async("https://youtube.com/watch?v=abc123", priority=5)
        call_args = mock_services["tasks"].enqueue_video_processing.call_args
        task = call_args[0][0]
        assert task.video_id == "abc123"
        assert task.priority == 5

    async def test_callback_url_passed_to_task(self, processor, mock_services):
        cb = "https://myapp.com/webhook"
        await processor.process_video_async("https://youtube.com/watch?v=abc123", callback_url=cb)
        task = mock_services["tasks"].enqueue_video_processing.call_args[0][0]
        assert task.callback_url == cb

    async def test_raises_when_queue_disabled(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor(enable_queue=False)
        with pytest.raises(RuntimeError, match="Cloud Tasks queue not enabled"):
            await p.process_video_async("https://youtube.com/watch?v=abc123")

    async def test_skips_firestore_when_state_disabled(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor(enable_queue=True, enable_state=False)
        await p.process_video_async("https://youtube.com/watch?v=abc123")
        mock_services["firestore"].create_state.assert_not_awaited()


# ---------------------------------------------------------------------------
# 5. process_video_sync – cache hit
# ---------------------------------------------------------------------------

class TestProcessVideoSyncCacheHit:
    async def test_returns_from_cache(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        completed = _make_completed_state()
        mock_services["firestore"].get_state = AsyncMock(return_value=completed)
        mock_services["firestore"].create_state = AsyncMock(return_value=None)

        p = CloudNativeVideoProcessor(enable_state=True)
        result = await p.process_video_sync("https://youtube.com/watch?v=auJzb1D-fag")

        assert result.from_cache is True
        assert result.success is True
        assert result.metadata == {"title": "Cached Video"}
        assert result.transcript == {"text": "cached transcript"}
        assert result.ai_analysis == {"summary": "cached summary"}

    async def test_cache_bypassed_with_force_refresh(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        completed = _make_completed_state()
        mock_services["firestore"].get_state = AsyncMock(return_value=completed)

        p = CloudNativeVideoProcessor(enable_state=True, enable_vertex_ai=False)
        result = await p.process_video_sync(
            "https://youtube.com/watch?v=auJzb1D-fag",
            force_refresh=True,
        )
        # Should NOT use cache
        assert result.from_cache is False


# ---------------------------------------------------------------------------
# 6. process_video_sync – full pipeline
# ---------------------------------------------------------------------------

class TestProcessVideoSyncFullPipeline:
    async def test_success_result_has_all_fields(self, processor, mock_services):
        # No cached state
        mock_services["firestore"].get_state = AsyncMock(return_value=None)

        result = await processor.process_video_sync("https://youtube.com/watch?v=testid")

        assert result.success is True
        assert result.video_id == "testid"
        assert result.from_cache is False
        assert result.metadata is not None
        assert result.transcript is not None
        assert result.ai_analysis is not None
        assert result.processing_time >= 0.0

    async def test_state_updated_through_stages(self, processor, mock_services):
        mock_services["firestore"].get_state = AsyncMock(return_value=None)

        await processor.process_video_sync("https://youtube.com/watch?v=testid")

        # State updated: processing, metadata stage, transcript stage, analysis stage, completed
        update_calls = mock_services["firestore"].update_state.call_args_list
        statuses_seen = [c.kwargs.get("status") for c in update_calls if "status" in c.kwargs]
        stages_seen = [c.kwargs.get("current_stage") for c in update_calls if "current_stage" in c.kwargs]

        assert "processing" in statuses_seen
        assert "completed" in statuses_seen
        assert "metadata" in stages_seen
        assert "transcript" in stages_seen

    async def test_vertex_ai_analysis_included(self, processor, mock_services):
        mock_services["firestore"].get_state = AsyncMock(return_value=None)

        result = await processor.process_video_sync("https://youtube.com/watch?v=testid")

        assert result.ai_analysis is not None
        assert result.ai_analysis["summary"] == "AI summary"

    async def test_vertex_ai_skipped_when_disabled(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        mock_services["firestore"].get_state = AsyncMock(return_value=None)
        p = CloudNativeVideoProcessor(enable_vertex_ai=False, enable_state=True)

        result = await p.process_video_sync("https://youtube.com/watch?v=testid")

        assert result.success is True
        assert result.ai_analysis is None
        mock_services["vertex"].analyze_transcript.assert_not_awaited()

    async def test_state_disabled_skips_firestore_calls(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor(enable_state=False, enable_vertex_ai=False)

        result = await p.process_video_sync("https://youtube.com/watch?v=testid")

        assert result.success is True
        mock_services["firestore"].create_state.assert_not_awaited()
        mock_services["firestore"].update_state.assert_not_awaited()

    async def test_error_returns_failed_result(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        # Make get_state raise to trigger the except block
        mock_services["firestore"].get_state = AsyncMock(side_effect=Exception("DB offline"))

        p = CloudNativeVideoProcessor(enable_state=True)
        result = await p.process_video_sync("https://youtube.com/watch?v=failid")

        assert result.success is False
        # error_message is persisted to Firestore and echoed to clients by
        # /status and /result, so it must be sanitized: neither the request's
        # video_id nor the internal exception text may leak (CWE-209).
        assert result.error_message == "Internal server error"
        assert "failid" not in result.error_message
        assert "DB offline" not in result.error_message
        assert result.processing_time >= 0.0

    async def test_error_updates_state_to_failed(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        mock_services["firestore"].get_state = AsyncMock(side_effect=Exception("DB offline"))

        p = CloudNativeVideoProcessor(enable_state=True)
        await p.process_video_sync("https://youtube.com/watch?v=failid")

        # update_state should have been called with status='failed'
        update_calls = mock_services["firestore"].update_state.call_args_list
        failed_calls = [c for c in update_calls if c.kwargs.get("status") == "failed"]
        assert len(failed_calls) >= 1


# ---------------------------------------------------------------------------
# 7. batch_process_async
# ---------------------------------------------------------------------------

class TestBatchProcessAsync:
    async def test_returns_list_of_task_ids(self, processor, mock_services):
        urls = [
            "https://youtube.com/watch?v=vid1",
            "https://youtube.com/watch?v=vid2",
        ]
        mock_services["tasks"].enqueue_batch = AsyncMock(return_value=["t1", "t2"])
        task_ids = await processor.batch_process_async(urls)
        assert task_ids == ["t1", "t2"]

    async def test_correct_number_of_tasks_enqueued(self, processor, mock_services):
        urls = [f"https://youtube.com/watch?v=v{i}" for i in range(5)]
        mock_services["tasks"].enqueue_batch = AsyncMock(return_value=[f"t{i}" for i in range(5)])
        task_ids = await processor.batch_process_async(urls, priority=2)
        call_args = mock_services["tasks"].enqueue_batch.call_args[0][0]
        assert len(call_args) == 5

    async def test_priority_applied_to_all_tasks(self, processor, mock_services):
        urls = ["https://youtube.com/watch?v=a", "https://youtube.com/watch?v=b"]
        mock_services["tasks"].enqueue_batch = AsyncMock(return_value=["t1", "t2"])
        await processor.batch_process_async(urls, priority=9)
        tasks = mock_services["tasks"].enqueue_batch.call_args[0][0]
        assert all(t.priority == 9 for t in tasks)

    async def test_raises_when_queue_disabled(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor(enable_queue=False)
        with pytest.raises(RuntimeError, match="Cloud Tasks queue not enabled"):
            await p.batch_process_async(["https://youtube.com/watch?v=abc"])

    async def test_empty_list_calls_enqueue_batch_with_empty(self, processor, mock_services):
        mock_services["tasks"].enqueue_batch = AsyncMock(return_value=[])
        result = await processor.batch_process_async([])
        assert result == []


# ---------------------------------------------------------------------------
# 8. get_processing_status
# ---------------------------------------------------------------------------

class TestGetProcessingStatus:
    async def test_returns_state_from_firestore(self, processor, mock_services):
        from youtube_extension.services.cloud.firestore_state import (
            VideoProcessingState,
        )

        expected = VideoProcessingState(
            video_id="myid", video_url="u", status="processing", current_stage="transcript"
        )
        mock_services["firestore"].get_state = AsyncMock(return_value=expected)

        result = await processor.get_processing_status("myid")
        assert result is expected
        mock_services["firestore"].get_state.assert_awaited_once_with("myid")

    async def test_returns_none_when_not_found(self, processor, mock_services):
        mock_services["firestore"].get_state = AsyncMock(return_value=None)

        result = await processor.get_processing_status("nonexistent")
        assert result is None

    async def test_raises_when_state_disabled(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor(enable_state=False)
        with pytest.raises(RuntimeError, match="Firestore state not enabled"):
            await p.get_processing_status("anyid")


# ---------------------------------------------------------------------------
# 9. _fetch_metadata (placeholder implementation)
# ---------------------------------------------------------------------------

class TestFetchMetadata:
    async def test_returns_dict_with_expected_keys(self, processor):
        metadata = await processor._fetch_metadata("https://youtube.com/watch?v=abc")
        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert "channel" in metadata
        assert "duration" in metadata
        assert "views" in metadata

    async def test_returns_for_any_url(self, processor):
        result = await processor._fetch_metadata("https://youtu.be/xyz")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 10. _extract_transcript (placeholder implementation)
# ---------------------------------------------------------------------------

class TestExtractTranscript:
    async def test_returns_dict_with_text(self, processor):
        transcript = await processor._extract_transcript("auJzb1D-fag")
        assert isinstance(transcript, dict)
        assert "text" in transcript
        assert "language" in transcript

    async def test_language_field_is_string(self, processor):
        transcript = await processor._extract_transcript("someId")
        assert isinstance(transcript["language"], str)


# ---------------------------------------------------------------------------
# 11. _analyze_with_vertex_ai
# ---------------------------------------------------------------------------

class TestAnalyzeWithVertexAI:
    async def test_calls_analyze_transcript(self, processor, mock_services):
        metadata = {"title": "Test Video", "channel": "TC"}
        transcript = {"text": "some transcript"}

        result = await processor._analyze_with_vertex_ai("vid123", metadata, transcript)

        mock_services["vertex"].analyze_transcript.assert_awaited_once_with(
            transcript="some transcript",
            video_metadata=metadata,
        )
        assert "summary" in result
        assert result["summary"] == "AI summary"

    async def test_returns_empty_dict_when_vertex_disabled(self, mock_services):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
        )

        p = CloudNativeVideoProcessor(enable_vertex_ai=False)
        result = await p._analyze_with_vertex_ai("vid", {}, {"text": "t"})
        assert result == {}

    async def test_result_includes_model_field(self, processor, mock_services):
        result = await processor._analyze_with_vertex_ai("vid", {}, {"text": "t"})
        assert result["model"] == "vertex-ai-agent-builder"

    async def test_result_includes_timestamp(self, processor, mock_services):
        result = await processor._analyze_with_vertex_ai("vid", {}, {"text": "t"})
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

    async def test_result_includes_usage(self, processor, mock_services):
        result = await processor._analyze_with_vertex_ai("vid", {}, {"text": "t"})
        assert "usage" in result


# ---------------------------------------------------------------------------
# 12. get_cloud_video_processor singleton
# ---------------------------------------------------------------------------

class TestGetCloudVideoProcessor:
    def test_returns_instance(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            CloudNativeVideoProcessor,
            get_cloud_video_processor,
        )

        p = get_cloud_video_processor()
        assert isinstance(p, CloudNativeVideoProcessor)

    def test_returns_same_instance_on_repeated_calls(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            get_cloud_video_processor,
        )

        p1 = get_cloud_video_processor()
        p2 = get_cloud_video_processor()
        assert p1 is p2

    def test_singleton_reset_between_tests(self):
        """The autouse fixture resets _cloud_video_processor to None before each test."""
        assert _mod._cloud_video_processor is None

    def test_singleton_stored_on_module(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            get_cloud_video_processor,
        )

        p = get_cloud_video_processor()
        assert _mod._cloud_video_processor is p

    def test_new_instance_created_after_reset(self):
        from youtube_extension.services.cloud.cloud_video_processor import (
            get_cloud_video_processor,
        )

        p1 = get_cloud_video_processor()
        _mod._cloud_video_processor = None
        p2 = get_cloud_video_processor()
        assert p1 is not p2
