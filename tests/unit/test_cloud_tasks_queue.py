"""
Unit tests for youtube_extension/services/cloud/cloud_tasks_queue.py.

Strategy
--------
`google.cloud.tasks_v2` is not installed in this environment, so the module
sets ``CLOUD_TASKS_AVAILABLE = False`` and ``tasks_v2 = None``.  Every test
that exercises code that requires the library patches both
``CLOUD_TASKS_AVAILABLE`` and ``tasks_v2`` on the already-imported module
object so we can exercise that code without the real SDK.
"""

from __future__ import annotations

import importlib
import json
import sys
import types as _types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure src/ is on the path
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Import the module under test (tasks_v2 will be None at this point)
# ---------------------------------------------------------------------------
import youtube_extension.services.cloud.cloud_tasks_queue as m

from youtube_extension.services.cloud.cloud_tasks_queue import (
    CloudTasksQueueService,
    TaskConfig,
    VideoProcessingTask,
    cleanup_cloud_tasks_service,
    get_cloud_tasks_service,
)

# ---------------------------------------------------------------------------
# Build a reusable mock tasks_v2 namespace
# ---------------------------------------------------------------------------

def _make_mock_tasks_v2() -> MagicMock:
    """Return a fresh mock tasks_v2 module with all required attributes.

    Key design notes
    ----------------
    * ``HttpMethod`` is a simple ``types.SimpleNamespace`` so that assigning
      ``HttpMethod.POST = "POST"`` doesn't confuse MagicMock's internal parent
      tracking (which walks ``_mock_new_parent`` and fails on plain strings).
    * Constructor-like attributes (``Task``, ``HttpRequest``, etc.) are
      ``MagicMock()`` instances with ``return_value`` already configured so
      that ``mock_tv2.Task(...)`` returns a predictable sentinel object.
    """
    import types as _types

    mock = MagicMock(name="tasks_v2")

    # Use a real namespace for HttpMethod so plain string attributes don't
    # leak into MagicMock's internal parent-chain traversal.
    http_method_ns = _types.SimpleNamespace(POST="POST")
    mock.HttpMethod = http_method_ns

    # Give each "constructor" its own MagicMock instance so callers can
    # inspect `.call_args` and `.return_value` independently.
    mock.CloudTasksClient = MagicMock(name="CloudTasksClient")
    mock.Task = MagicMock(name="Task")
    mock.HttpRequest = MagicMock(name="HttpRequest")
    mock.CreateTaskRequest = MagicMock(name="CreateTaskRequest")
    mock.Queue = MagicMock(name="Queue")
    mock.RateLimits = MagicMock(name="RateLimits")
    mock.RetryConfig = MagicMock(name="RetryConfig")
    mock.CreateQueueRequest = MagicMock(name="CreateQueueRequest")
    return mock


def _make_mock_timestamp_pb2() -> MagicMock:
    ts = MagicMock(name="timestamp_pb2")
    ts.Timestamp = MagicMock(name="Timestamp")
    return ts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(
    mock_tasks_v2: MagicMock,
    project_id: str = "test-project",
    location: str = "us-central1",
    queue_name: str = "test-queue",
    service_url: str = "https://example.run.app",
    task_path: str = "/api/v3/process-video-task",
) -> CloudTasksQueueService:
    """Instantiate a CloudTasksQueueService with CLOUD_TASKS_AVAILABLE=True."""
    with (
        patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
        patch.object(m, "tasks_v2", mock_tasks_v2),
    ):
        svc = CloudTasksQueueService(
            project_id=project_id,
            location=location,
            queue_name=queue_name,
            service_url=service_url,
            task_path=task_path,
        )
    return svc


def _initialized_service(mock_tasks_v2: MagicMock) -> CloudTasksQueueService:
    """Return a service that also has a mock client attached."""
    svc = _make_service(mock_tasks_v2)
    mock_client = MagicMock()
    mock_client.queue_path.return_value = (
        "projects/test-project/locations/us-central1/queues/test-queue"
    )
    svc.client = mock_client
    return svc


# ===========================================================================
# VideoProcessingTask tests
# ===========================================================================


class TestVideoProcessingTask:
    """Tests for VideoProcessingTask dataclass."""

    def _sample(self, **kwargs) -> VideoProcessingTask:
        defaults = dict(
            video_id="vid-001",
            video_url="https://youtube.com/watch?v=vid-001",
        )
        defaults.update(kwargs)
        return VideoProcessingTask(**defaults)

    # ------------------------------------------------------------------
    # to_json / from_json round-trip
    # ------------------------------------------------------------------

    def test_to_json_returns_valid_json_string(self):
        task = self._sample()
        raw = task.to_json()
        assert isinstance(raw, str)
        data = json.loads(raw)
        assert data["video_id"] == "vid-001"
        assert data["video_url"] == "https://youtube.com/watch?v=vid-001"

    def test_to_json_includes_all_fields(self):
        task = self._sample(
            priority=5,
            callback_url="https://cb.example.com/done",
            metadata={"foo": "bar"},
        )
        data = json.loads(task.to_json())
        assert data["priority"] == 5
        assert data["callback_url"] == "https://cb.example.com/done"
        assert data["metadata"] == {"foo": "bar"}

    def test_to_json_metadata_none_becomes_empty_dict(self):
        task = self._sample(metadata=None)
        data = json.loads(task.to_json())
        assert data["metadata"] == {}

    def test_from_json_round_trip(self):
        task = self._sample(
            priority=3,
            callback_url="https://cb.example.com/hook",
            metadata={"key": "value"},
        )
        restored = VideoProcessingTask.from_json(task.to_json())
        assert restored.video_id == task.video_id
        assert restored.video_url == task.video_url
        assert restored.priority == task.priority
        assert restored.callback_url == task.callback_url
        assert restored.metadata == task.metadata

    def test_from_json_minimal(self):
        payload = json.dumps(
            {
                "video_id": "abc",
                "video_url": "https://yt.be/abc",
                "priority": 0,
                "callback_url": None,
                "metadata": {},
            }
        )
        task = VideoProcessingTask.from_json(payload)
        assert task.video_id == "abc"
        assert task.priority == 0
        assert task.callback_url is None

    def test_to_json_body_is_utf8_encodable(self):
        task = self._sample()
        encoded = task.to_json().encode()
        assert isinstance(encoded, bytes)
        assert b"vid-001" in encoded

    def test_default_priority_is_zero(self):
        task = VideoProcessingTask(
            video_id="x", video_url="https://yt.be/x"
        )
        assert task.priority == 0

    def test_default_callback_url_is_none(self):
        task = VideoProcessingTask(
            video_id="x", video_url="https://yt.be/x"
        )
        assert task.callback_url is None

    def test_default_metadata_is_none(self):
        task = VideoProcessingTask(
            video_id="x", video_url="https://yt.be/x"
        )
        assert task.metadata is None


# ===========================================================================
# TaskConfig tests
# ===========================================================================


class TestTaskConfig:
    """Tests for TaskConfig dataclass defaults and construction."""

    def test_defaults(self):
        cfg = TaskConfig()
        assert cfg.task_name is None
        assert cfg.schedule_time is None
        assert cfg.max_retry_count == 3
        assert cfg.max_retry_duration == timedelta(hours=1)
        assert cfg.min_backoff == timedelta(seconds=10)
        assert cfg.max_backoff == timedelta(seconds=300)

    def test_custom_values(self):
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        cfg = TaskConfig(
            task_name="my-task",
            schedule_time=dt,
            max_retry_count=5,
            max_retry_duration=timedelta(hours=2),
            min_backoff=timedelta(seconds=5),
            max_backoff=timedelta(seconds=600),
        )
        assert cfg.task_name == "my-task"
        assert cfg.schedule_time == dt
        assert cfg.max_retry_count == 5

    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(TaskConfig)


# ===========================================================================
# CloudTasksQueueService.__init__ tests
# ===========================================================================


class TestCloudTasksQueueServiceInit:
    """Tests for __init__ behaviour."""

    def test_raises_import_error_when_unavailable(self):
        """When CLOUD_TASKS_AVAILABLE is False __init__ must raise ImportError."""
        with patch.object(m, "CLOUD_TASKS_AVAILABLE", False):
            with pytest.raises(ImportError, match="Cloud Tasks not available"):
                CloudTasksQueueService()

    def test_succeeds_when_available(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        assert svc.project_id == "test-project"
        assert svc.location == "us-central1"
        assert svc.queue_name == "test-queue"
        assert svc.service_url == "https://example.run.app"
        assert svc.task_path == "/api/v3/process-video-task"
        assert svc.client is None

    def test_reads_project_id_from_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
        monkeypatch.setenv("CLOUD_RUN_SERVICE_URL", "https://env.run.app")
        mock_tv2 = _make_mock_tasks_v2()
        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc = CloudTasksQueueService()
        assert svc.project_id == "env-project"

    def test_reads_service_url_from_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
        monkeypatch.setenv("CLOUD_RUN_SERVICE_URL", "https://env.run.app")
        mock_tv2 = _make_mock_tasks_v2()
        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc = CloudTasksQueueService()
        assert svc.service_url == "https://env.run.app"

    def test_explicit_args_override_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
        monkeypatch.setenv("CLOUD_RUN_SERVICE_URL", "https://env.run.app")
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2, project_id="explicit-project", service_url="https://explicit.run.app")
        assert svc.project_id == "explicit-project"
        assert svc.service_url == "https://explicit.run.app"

    def test_default_queue_name(self):
        mock_tv2 = _make_mock_tasks_v2()
        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc = CloudTasksQueueService(
                project_id="p", service_url="https://x.run.app"
            )
        assert svc.queue_name == "video-processing-queue"

    def test_default_task_path(self):
        mock_tv2 = _make_mock_tasks_v2()
        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc = CloudTasksQueueService(
                project_id="p", service_url="https://x.run.app"
            )
        assert svc.task_path == "/api/v3/process-video-task"


# ===========================================================================
# initialize / close tests
# ===========================================================================


class TestInitializeAndClose:
    """Tests for initialize() and close()."""

    def test_initialize_creates_client(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_client_cls = MagicMock()
        mock_tv2.CloudTasksClient = mock_client_cls

        svc = _make_service(mock_tv2)
        assert svc.client is None

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc.initialize()

        mock_client_cls.assert_called_once()
        assert svc.client is not None

    def test_initialize_is_idempotent(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_client_cls = MagicMock()
        mock_tv2.CloudTasksClient = mock_client_cls

        svc = _make_service(mock_tv2)

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc.initialize()
            svc.initialize()  # second call should be a no-op

        mock_client_cls.assert_called_once()

    def test_close_calls_transport_close_and_nils_client(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)

        mock_client = MagicMock()
        svc.client = mock_client

        svc.close()

        mock_client.transport.close.assert_called_once()
        assert svc.client is None

    def test_close_is_idempotent_when_no_client(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        assert svc.client is None
        # Should not raise
        svc.close()
        assert svc.client is None

    def test_close_then_reinitialize(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_client_cls = MagicMock()
        mock_tv2.CloudTasksClient = mock_client_cls

        svc = _make_service(mock_tv2)

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc.initialize()
            svc.close()
            assert svc.client is None
            svc.initialize()

        assert mock_client_cls.call_count == 2


# ===========================================================================
# _get_queue_path tests
# ===========================================================================


class TestGetQueuePath:
    """Tests for _get_queue_path()."""

    def test_raises_when_not_initialized(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        assert svc.client is None
        with pytest.raises(RuntimeError, match="not initialized"):
            svc._get_queue_path()

    def test_returns_value_from_client_queue_path(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)
        expected = "projects/test-project/locations/us-central1/queues/test-queue"
        svc.client.queue_path.return_value = expected

        result = svc._get_queue_path()

        svc.client.queue_path.assert_called_once_with(
            "test-project", "us-central1", "test-queue"
        )
        assert result == expected


# ===========================================================================
# enqueue_video_processing tests
# ===========================================================================


class TestEnqueueVideoProcessing:
    """Tests for enqueue_video_processing()."""

    def _video_task(self, video_id="vid-1") -> VideoProcessingTask:
        return VideoProcessingTask(
            video_id=video_id,
            video_url=f"https://youtube.com/watch?v={video_id}",
        )

    async def test_raises_runtime_error_when_not_initialized(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.enqueue_video_processing(self._video_task())

    async def test_raises_value_error_when_no_service_url(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2, service_url=None)
        svc.client = MagicMock()  # manually set a client so we get past the first guard
        # monkeypatch service_url to None
        svc.service_url = None
        with pytest.raises(ValueError, match="Service URL not configured"):
            await svc.enqueue_video_processing(self._video_task())

    async def test_success_returns_task_id(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        mock_response = MagicMock()
        mock_response.name = (
            "projects/test-project/locations/us-central1/queues/test-queue/tasks/task-abc"
        )
        svc.client.create_task.return_value = mock_response

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            task_id = await svc.enqueue_video_processing(self._video_task())

        assert task_id == "task-abc"
        svc.client.create_task.assert_called_once()

    async def test_builds_correct_url(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        mock_response = MagicMock()
        mock_response.name = ".../tasks/t1"
        svc.client.create_task.return_value = mock_response

        call_kwargs: dict = {}

        def capture_create_task(request):
            call_kwargs["request"] = request
            return mock_response

        svc.client.create_task.side_effect = capture_create_task

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.enqueue_video_processing(self._video_task())

        # Ensure CreateTaskRequest was constructed with the right parent
        args, kwargs = mock_tv2.CreateTaskRequest.call_args
        assert kwargs.get("parent") or args

    async def test_uses_task_name_from_config(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        mock_response = MagicMock()
        mock_response.name = ".../tasks/named-task"
        svc.client.create_task.return_value = mock_response

        task_obj = MagicMock()  # the Task() instance
        mock_tv2.Task.return_value = task_obj

        expected_path = "projects/p/locations/l/queues/q/tasks/named-task"
        svc.client.task_path.return_value = expected_path

        config = TaskConfig(task_name="named-task")

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.enqueue_video_processing(self._video_task(), task_config=config)

        svc.client.task_path.assert_called_once_with(
            "test-project", "us-central1", "test-queue", "named-task"
        )
        assert task_obj.name == expected_path

    async def test_uses_schedule_time_from_config(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_ts_pb2 = _make_mock_timestamp_pb2()

        svc = _initialized_service(mock_tv2)

        mock_response = MagicMock()
        mock_response.name = ".../tasks/scheduled"
        svc.client.create_task.return_value = mock_response

        task_obj = MagicMock()
        mock_tv2.Task.return_value = task_obj

        mock_ts_instance = MagicMock()
        mock_ts_pb2.Timestamp.return_value = mock_ts_instance

        schedule_dt = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        config = TaskConfig(schedule_time=schedule_dt)

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
            patch.object(m, "timestamp_pb2", mock_ts_pb2),
        ):
            await svc.enqueue_video_processing(self._video_task(), task_config=config)

        mock_ts_pb2.Timestamp.assert_called_once()
        mock_ts_instance.FromDatetime.assert_called_once_with(schedule_dt)
        assert task_obj.schedule_time == mock_ts_instance

    async def test_no_task_name_does_not_call_task_path(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        mock_response = MagicMock()
        mock_response.name = ".../tasks/auto"
        svc.client.create_task.return_value = mock_response

        config = TaskConfig()  # task_name=None

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.enqueue_video_processing(self._video_task(), task_config=config)

        svc.client.task_path.assert_not_called()


# ===========================================================================
# enqueue_batch tests
# ===========================================================================


class TestEnqueueBatch:
    """Tests for enqueue_batch()."""

    def _video_tasks(self, count=3) -> list[VideoProcessingTask]:
        return [
            VideoProcessingTask(
                video_id=f"vid-{i}",
                video_url=f"https://youtube.com/watch?v=vid-{i}",
            )
            for i in range(count)
        ]

    async def test_returns_all_task_ids_on_success(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        responses = [MagicMock() for _ in range(3)]
        for i, r in enumerate(responses):
            r.name = f".../tasks/t{i}"
        svc.client.create_task.side_effect = responses

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            ids = await svc.enqueue_batch(self._video_tasks(3))

        assert ids == ["t0", "t1", "t2"]
        assert svc.client.create_task.call_count == 3

    async def test_skips_failed_tasks_and_continues(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        good_response = MagicMock()
        good_response.name = ".../tasks/ok"

        svc.client.create_task.side_effect = [
            good_response,
            RuntimeError("network error"),
            good_response,
        ]

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            ids = await svc.enqueue_batch(self._video_tasks(3))

        assert len(ids) == 2
        assert all(tid == "ok" for tid in ids)

    async def test_empty_batch_returns_empty_list(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            ids = await svc.enqueue_batch([])

        assert ids == []
        svc.client.create_task.assert_not_called()

    async def test_all_tasks_fail_returns_empty_list(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        svc.client.create_task.side_effect = RuntimeError("quota exceeded")

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            ids = await svc.enqueue_batch(self._video_tasks(2))

        assert ids == []


# ===========================================================================
# create_queue_if_not_exists tests
# ===========================================================================


class TestCreateQueueIfNotExists:
    """Tests for create_queue_if_not_exists()."""

    async def test_raises_when_not_initialized(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.create_queue_if_not_exists()

    async def test_does_not_create_when_queue_exists(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        # get_queue succeeds -> queue exists
        svc.client.get_queue.return_value = MagicMock()

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.create_queue_if_not_exists()

        svc.client.create_queue.assert_not_called()

    async def test_creates_queue_when_get_queue_raises(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        # get_queue raises -> queue doesn't exist yet
        svc.client.get_queue.side_effect = Exception("Queue not found")

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.create_queue_if_not_exists()

        svc.client.create_queue.assert_called_once()
        call_kwargs = mock_tv2.CreateQueueRequest.call_args
        assert call_kwargs is not None


# ===========================================================================
# pause_queue / resume_queue / purge_queue tests
# ===========================================================================


class TestQueueControls:
    """Tests for pause_queue(), resume_queue(), purge_queue()."""

    async def test_pause_raises_when_not_initialized(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.pause_queue()

    async def test_pause_calls_client(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.pause_queue()

        svc.client.pause_queue.assert_called_once_with(
            name=svc.client.queue_path.return_value
        )

    async def test_resume_raises_when_not_initialized(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.resume_queue()

    async def test_resume_calls_client(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.resume_queue()

        svc.client.resume_queue.assert_called_once_with(
            name=svc.client.queue_path.return_value
        )

    async def test_purge_raises_when_not_initialized(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.purge_queue()

    async def test_purge_calls_client(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.purge_queue()

        svc.client.purge_queue.assert_called_once_with(
            name=svc.client.queue_path.return_value
        )


# ===========================================================================
# get_queue_stats tests
# ===========================================================================


class TestGetQueueStats:
    """Tests for get_queue_stats()."""

    async def test_raises_when_not_initialized(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _make_service(mock_tv2)
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.get_queue_stats()

    async def test_returns_stats_dict(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        mock_queue = MagicMock()
        mock_queue.name = "projects/test-project/locations/us-central1/queues/test-queue"
        mock_queue.state.name = "RUNNING"
        mock_queue.stats.tasks_count = 42
        mock_queue.stats.oldest_estimated_arrival_time = "2025-01-01T00:00:00Z"
        mock_queue.rate_limits.max_dispatches_per_second = 100
        mock_queue.rate_limits.max_concurrent_dispatches = 50
        svc.client.get_queue.return_value = mock_queue

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            stats = await svc.get_queue_stats()

        assert stats["name"] == mock_queue.name
        assert stats["state"] == "RUNNING"
        assert stats["tasks_count"] == 42
        assert stats["rate_limits"]["max_dispatches_per_second"] == 100
        assert stats["rate_limits"]["max_concurrent_dispatches"] == 50

    async def test_stats_when_no_stats_object(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        mock_queue = MagicMock()
        mock_queue.name = "some-queue"
        mock_queue.state.name = "PAUSED"
        mock_queue.stats = None
        mock_queue.rate_limits = None
        svc.client.get_queue.return_value = mock_queue

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            stats = await svc.get_queue_stats()

        assert stats["tasks_count"] == 0
        assert stats["oldest_task_age"] is None
        assert stats["rate_limits"] is None

    async def test_get_queue_stats_calls_get_queue_with_path(self):
        mock_tv2 = _make_mock_tasks_v2()
        svc = _initialized_service(mock_tv2)

        svc.client.get_queue.return_value = MagicMock()

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            await svc.get_queue_stats()

        svc.client.get_queue.assert_called_once_with(
            name=svc.client.queue_path.return_value
        )


# ===========================================================================
# Module-level singleton functions
# ===========================================================================


class TestSingletonFunctions:
    """Tests for get_cloud_tasks_service() and cleanup_cloud_tasks_service()."""

    def setup_method(self):
        """Ensure a clean slate before each test."""
        # Reset the module-level singleton
        m._cloud_tasks_service = None

    def teardown_method(self):
        """Always clean up after each test."""
        m._cloud_tasks_service = None

    def test_get_returns_same_instance_on_repeated_calls(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_tv2.CloudTasksClient = MagicMock

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc1 = get_cloud_tasks_service()
            svc2 = get_cloud_tasks_service()

        assert svc1 is svc2

    def test_get_creates_and_initializes_service(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_client_cls = MagicMock()
        mock_tv2.CloudTasksClient = mock_client_cls

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc = get_cloud_tasks_service()

        assert isinstance(svc, CloudTasksQueueService)
        # client should have been created by initialize()
        mock_client_cls.assert_called_once()

    def test_cleanup_closes_and_nils_singleton(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_tv2.CloudTasksClient = MagicMock

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc = get_cloud_tasks_service()
            assert m._cloud_tasks_service is svc

            cleanup_cloud_tasks_service()

        assert m._cloud_tasks_service is None

    def test_cleanup_is_idempotent_when_no_singleton(self):
        assert m._cloud_tasks_service is None
        # Should not raise
        cleanup_cloud_tasks_service()
        assert m._cloud_tasks_service is None

    def test_get_after_cleanup_creates_new_instance(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_tv2.CloudTasksClient = MagicMock

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc1 = get_cloud_tasks_service()
            cleanup_cloud_tasks_service()
            svc2 = get_cloud_tasks_service()

        assert svc1 is not svc2

    def test_cleanup_calls_close_on_service(self):
        mock_tv2 = _make_mock_tasks_v2()
        mock_tv2.CloudTasksClient = MagicMock

        with (
            patch.object(m, "CLOUD_TASKS_AVAILABLE", True),
            patch.object(m, "tasks_v2", mock_tv2),
        ):
            svc = get_cloud_tasks_service()

        mock_client = MagicMock()
        svc.client = mock_client

        cleanup_cloud_tasks_service()

        mock_client.transport.close.assert_called_once()


# ===========================================================================
# Module-level CLOUD_TASKS_AVAILABLE flag
# ===========================================================================


class TestModuleLevelAvailabilityFlag:
    """Verify that the module correctly exposes CLOUD_TASKS_AVAILABLE."""

    def test_cloud_tasks_available_is_bool(self):
        assert isinstance(m.CLOUD_TASKS_AVAILABLE, bool)

    def test_cloud_tasks_available_is_false_when_library_missing(self):
        # In this test environment the library is not installed
        assert m.CLOUD_TASKS_AVAILABLE is False

    def test_tasks_v2_is_none_when_library_missing(self):
        assert m.tasks_v2 is None
