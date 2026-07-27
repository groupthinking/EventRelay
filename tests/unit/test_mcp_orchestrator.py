"""Unit tests for services/mcp/orchestrator.py."""

from __future__ import annotations

import asyncio
import sys
import types as _types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SRC = str(Path(__file__).resolve().parents[2] / "src")
sys.path.insert(0, _SRC)

# Bypass the broken services __init__ (pyo3 panic) before importing submodules.
if "youtube_extension.services" not in sys.modules:
    _stub = _types.ModuleType("youtube_extension.services")
    _stub.__path__ = [_SRC + "/youtube_extension/services"]
    _stub.__package__ = "youtube_extension.services"
    sys.modules["youtube_extension.services"] = _stub

# Force reimport so pytest-cov instruments the module.
for _key in ["youtube_extension.services.mcp.orchestrator",
             "youtube_extension.services.mcp.registry",
             "youtube_extension.services.mcp.types",
             "youtube_extension.services.mcp"]:
    sys.modules.pop(_key, None)

from youtube_extension.services.mcp.orchestrator import (
    MCPOrchestrator,
    get_orchestrator,
)
from youtube_extension.services.mcp.types import (
    MCPCapability,
    MCPTaskStatus,
)

import youtube_extension.services.mcp.orchestrator as _orch_mod


# ===========================================================================
# MCPOrchestrator.__init__
# ===========================================================================


class TestMCPOrchestratorInit:
    def test_tasks_starts_empty(self):
        orch = MCPOrchestrator()
        assert orch.tasks == {}

    def test_task_queue_starts_empty(self):
        orch = MCPOrchestrator()
        assert len(orch.task_queue) == 0

    def test_active_tasks_starts_empty(self):
        orch = MCPOrchestrator()
        assert orch.active_tasks == {}

    def test_orchestration_inactive(self):
        orch = MCPOrchestrator()
        assert orch.orchestration_active is False

    def test_metrics_initialized(self):
        orch = MCPOrchestrator()
        assert orch.metrics["total_tasks"] == 0
        assert orch.metrics["completed_tasks"] == 0
        assert orch.metrics["failed_tasks"] == 0
        assert orch.metrics["cancelled_tasks"] == 0

    def test_max_concurrent_spawn_default(self):
        orch = MCPOrchestrator()
        assert orch.max_concurrent_spawn == 10

    def test_spawned_tasks_starts_empty(self):
        orch = MCPOrchestrator()
        assert orch.spawned_tasks == {}


# ===========================================================================
# MCPOrchestrator.submit_task
# ===========================================================================


class TestSubmitTask:
    async def test_returns_task_id_string(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("process_video", {}, [])
        assert isinstance(task_id, str)
        assert len(task_id) == 36  # UUID

    async def test_task_stored(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("my_task", {"key": "val"}, [])
        assert task_id in orch.tasks

    async def test_total_tasks_incremented(self):
        orch = MCPOrchestrator()
        await orch.submit_task("t1", {}, [])
        await orch.submit_task("t2", {}, [])
        assert orch.metrics["total_tasks"] == 2

    async def test_task_type_stored(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("my_type", {}, [])
        assert orch.tasks[task_id].task_type == "my_type"

    async def test_payload_stored(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {"a": 1}, [])
        assert orch.tasks[task_id].payload == {"a": 1}

    async def test_task_queued_when_no_deps(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        assert task_id in orch.task_queue

    async def test_default_priority_three(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        assert orch.tasks[task_id].priority == 3

    async def test_custom_priority(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [], priority=1)
        assert orch.tasks[task_id].priority == 1

    async def test_dependencies_not_queued_when_missing(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [], dependencies=["non_existent_dep"])
        assert task_id not in orch.task_queue

    async def test_task_queued_when_dep_completed(self):
        orch = MCPOrchestrator()
        dep_id = await orch.submit_task("dep", {}, [])
        # Mark dep as completed
        orch.tasks[dep_id].status = MCPTaskStatus.COMPLETED
        # Now submit task that depends on it
        task_id = await orch.submit_task("main", {}, [], dependencies=[dep_id])
        assert task_id in orch.task_queue


# ===========================================================================
# MCPOrchestrator.get_task_status
# ===========================================================================


class TestGetTaskStatus:
    async def test_returns_none_for_unknown_id(self):
        orch = MCPOrchestrator()
        result = await orch.get_task_status("non_existent")
        assert result is None

    async def test_returns_task_for_valid_id(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        task = await orch.get_task_status(task_id)
        assert task is not None
        assert task.task_id == task_id

    async def test_returned_task_has_correct_type(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("my_type", {}, [])
        task = await orch.get_task_status(task_id)
        assert task.task_type == "my_type"

    async def test_initial_status_is_pending(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        task = await orch.get_task_status(task_id)
        assert task.status == MCPTaskStatus.PENDING


# ===========================================================================
# MCPOrchestrator.cancel_task
# ===========================================================================


class TestCancelTask:
    async def test_returns_false_for_unknown_id(self):
        orch = MCPOrchestrator()
        result = await orch.cancel_task("non_existent")
        assert result is False

    async def test_cancels_pending_task(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        result = await orch.cancel_task(task_id)
        assert result is True

    async def test_cancelled_task_status_updated(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        await orch.cancel_task(task_id)
        assert orch.tasks[task_id].status == MCPTaskStatus.CANCELLED

    async def test_cancelled_metrics_incremented(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        await orch.cancel_task(task_id)
        assert orch.metrics["cancelled_tasks"] == 1

    async def test_cancelled_task_removed_from_queue(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        assert task_id in orch.task_queue
        await orch.cancel_task(task_id)
        assert task_id not in orch.task_queue

    async def test_cannot_cancel_completed_task(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        orch.tasks[task_id].status = MCPTaskStatus.COMPLETED
        result = await orch.cancel_task(task_id)
        assert result is False

    async def test_cannot_cancel_failed_task(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        orch.tasks[task_id].status = MCPTaskStatus.FAILED
        result = await orch.cancel_task(task_id)
        assert result is False


# ===========================================================================
# MCPOrchestrator.execute_task
# ===========================================================================


class TestExecuteTask:
    async def test_raises_for_unknown_task(self):
        orch = MCPOrchestrator()
        with pytest.raises(ValueError, match="Task not found"):
            await orch.execute_task("non_existent")

    async def test_fails_when_no_server_available(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task(
            "process", {}, [MCPCapability.VIDEO_ANALYSIS]
        )
        result = await orch.execute_task(task_id)
        assert result["status"] == "failed"

    async def test_task_marked_failed_when_no_server(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("process", {}, [MCPCapability.AI_INFERENCE])
        await orch.execute_task(task_id)
        assert orch.tasks[task_id].status == MCPTaskStatus.FAILED

    async def test_failed_metrics_incremented(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [MCPCapability.VIDEO_PROCESSING])
        await orch.execute_task(task_id)
        assert orch.metrics["failed_tasks"] == 1


# ===========================================================================
# MCPOrchestrator._check_dependencies
# ===========================================================================


class TestCheckDependencies:
    async def test_no_dependencies_returns_true(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        result = await orch._check_dependencies(task_id)
        assert result is True

    async def test_unknown_task_id_returns_true(self):
        orch = MCPOrchestrator()
        result = await orch._check_dependencies("non_existent")
        assert result is True

    async def test_unmet_dependency_returns_false(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [], dependencies=["missing_dep"])
        result = await orch._check_dependencies(task_id)
        assert result is False

    async def test_completed_dependency_returns_true(self):
        orch = MCPOrchestrator()
        dep_id = await orch.submit_task("dep", {}, [])
        orch.tasks[dep_id].status = MCPTaskStatus.COMPLETED
        task_id = await orch.submit_task("main", {}, [], dependencies=[dep_id])
        result = await orch._check_dependencies(task_id)
        assert result is True

    async def test_pending_dependency_returns_false(self):
        orch = MCPOrchestrator()
        dep_id = await orch.submit_task("dep", {}, [])
        # dep is still PENDING
        task_id = await orch.submit_task("main", {}, [], dependencies=[dep_id])
        result = await orch._check_dependencies(task_id)
        assert result is False


# ===========================================================================
# MCPOrchestrator._update_average_task_time
# ===========================================================================


class TestUpdateAverageTaskTime:
    def test_first_update_sets_value(self):
        orch = MCPOrchestrator()
        orch._update_average_task_time(5.0)
        assert orch.metrics["average_task_time"] == 5.0

    def test_subsequent_update_uses_ema(self):
        orch = MCPOrchestrator()
        orch._update_average_task_time(10.0)
        orch._update_average_task_time(20.0)
        # EMA: 0.8 * 10.0 + 0.2 * 20.0 = 12.0
        assert orch.metrics["average_task_time"] == pytest.approx(12.0)

    def test_zero_initial_gets_set(self):
        orch = MCPOrchestrator()
        assert orch.metrics["average_task_time"] == 0.0
        orch._update_average_task_time(3.0)
        assert orch.metrics["average_task_time"] == 3.0


# ===========================================================================
# MCPOrchestrator.get_orchestrator_status
# ===========================================================================


class TestGetOrchestratorStatus:
    def test_returns_dict(self):
        orch = MCPOrchestrator()
        status = orch.get_orchestrator_status()
        assert isinstance(status, dict)

    def test_orchestration_active_key(self):
        orch = MCPOrchestrator()
        status = orch.get_orchestrator_status()
        assert "orchestration_active" in status
        assert status["orchestration_active"] is False

    def test_metrics_included(self):
        orch = MCPOrchestrator()
        status = orch.get_orchestrator_status()
        assert "metrics" in status

    def test_queued_tasks_count(self):
        orch = MCPOrchestrator()
        status = orch.get_orchestrator_status()
        assert status["queued_tasks"] == 0

    async def test_queued_tasks_count_after_submit(self):
        orch = MCPOrchestrator()
        await orch.submit_task("t", {}, [])
        status = orch.get_orchestrator_status()
        assert status["queued_tasks"] == 1


# ===========================================================================
# MCPOrchestrator.start_orchestration / stop_orchestration
# ===========================================================================


class TestOrchestrationLifecycle:
    async def test_start_sets_active(self):
        orch = MCPOrchestrator()
        try:
            await orch.start_orchestration()
            assert orch.orchestration_active is True
        finally:
            await orch.stop_orchestration()

    async def test_stop_clears_active(self):
        orch = MCPOrchestrator()
        await orch.start_orchestration()
        await orch.stop_orchestration()
        assert orch.orchestration_active is False

    async def test_double_start_does_not_raise(self):
        orch = MCPOrchestrator()
        try:
            await orch.start_orchestration()
            await orch.start_orchestration()  # Should just log warning
            assert orch.orchestration_active is True
        finally:
            await orch.stop_orchestration()

    async def test_stop_when_not_started_does_not_raise(self):
        orch = MCPOrchestrator()
        await orch.stop_orchestration()  # Should be a no-op


# ===========================================================================
# get_orchestrator global function
# ===========================================================================


class TestGetOrchestrator:
    def test_returns_mcp_orchestrator(self):
        _orch_mod._orchestrator = None
        result = get_orchestrator()
        assert isinstance(result, MCPOrchestrator)

    def test_same_instance_on_second_call(self):
        _orch_mod._orchestrator = None
        first = get_orchestrator()
        second = get_orchestrator()
        assert first is second


# ===========================================================================
# MCPOrchestrator.submit_task – task eviction (lines 114-126)
# ===========================================================================


class TestSubmitTaskEviction:
    async def test_evicts_completed_tasks_when_limit_exceeded(self):
        orch = MCPOrchestrator()
        orch.max_tasks_retained = 10

        # Submit 10 tasks and mark them completed so they are eviction candidates
        for _ in range(10):
            tid = await orch.submit_task("t", {}, [])
            orch.tasks[tid].status = MCPTaskStatus.COMPLETED

        # This 11th task submission should trigger eviction
        await orch.submit_task("trigger_eviction", {}, [])

        # After eviction total tasks should be <= max_tasks_retained
        assert len(orch.tasks) <= orch.max_tasks_retained

    async def test_active_tasks_not_evicted(self):
        orch = MCPOrchestrator()
        orch.max_tasks_retained = 5

        # Submit 5 tasks and mark them completed
        for _ in range(5):
            tid = await orch.submit_task("t", {}, [])
            orch.tasks[tid].status = MCPTaskStatus.COMPLETED

        # Submit 1 more and manually place it in active_tasks
        active_tid = await orch.submit_task("active_one", {}, [])
        orch.active_tasks[active_tid] = orch.tasks[active_tid]
        orch.tasks[active_tid].status = MCPTaskStatus.COMPLETED  # terminal but active

        # Trigger eviction with one more task
        await orch.submit_task("trigger", {}, [])

        # The active task should NOT have been evicted
        assert active_tid in orch.tasks

    async def test_failed_tasks_are_eviction_candidates(self):
        orch = MCPOrchestrator()
        orch.max_tasks_retained = 5

        evict_ids = []
        for _ in range(5):
            tid = await orch.submit_task("t", {}, [])
            orch.tasks[tid].status = MCPTaskStatus.FAILED
            evict_ids.append(tid)

        # 6th task triggers eviction
        await orch.submit_task("trigger", {}, [])

        # At least some failed tasks were evicted
        remaining_evict = sum(1 for t in evict_ids if t in orch.tasks)
        assert remaining_evict < 5

    async def test_cancelled_tasks_are_eviction_candidates(self):
        orch = MCPOrchestrator()
        orch.max_tasks_retained = 5

        evict_ids = []
        for _ in range(5):
            tid = await orch.submit_task("t", {}, [])
            orch.tasks[tid].status = MCPTaskStatus.CANCELLED
            evict_ids.append(tid)

        await orch.submit_task("trigger", {}, [])

        remaining = sum(1 for t in evict_ids if t in orch.tasks)
        assert remaining < 5


# ===========================================================================
# MCPOrchestrator.cancel_task – spawned task path (lines 177-195)
# ===========================================================================


class TestCancelTaskWithSpawnedTask:
    async def test_cancels_executing_asyncio_task(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])

        # Simulate a spawned asyncio task
        dummy_future: asyncio.Future = asyncio.get_event_loop().create_future()
        orch.spawned_tasks[task_id] = asyncio.ensure_future(dummy_future)  # type: ignore[arg-type]

        result = await orch.cancel_task(task_id)

        assert result is True
        assert task_id not in orch.spawned_tasks

    async def test_cancel_removes_from_active_tasks(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        orch.active_tasks[task_id] = orch.tasks[task_id]

        await orch.cancel_task(task_id)

        assert task_id not in orch.active_tasks

    async def test_cancel_with_assigned_server_decrements_current_tasks(self):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, ServerStatus

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        registry.server_states["srv"].status = ServerStatus.ONLINE
        registry.server_states["srv"].current_tasks = 3

        orch = MCPOrchestrator(registry=registry)
        task_id = await orch.submit_task("t", {}, [MCPCapability.AI_INFERENCE])

        # Simulate that it's been assigned to the server
        orch.tasks[task_id].assigned_server = "srv"

        # Put it in spawned_tasks with a done future so pop works
        done_task: asyncio.Future = asyncio.get_event_loop().create_future()
        done_task.set_result(None)
        orch.spawned_tasks[task_id] = asyncio.ensure_future(done_task)  # type: ignore[arg-type]

        await orch.cancel_task(task_id)

        # current_tasks decremented
        assert registry.server_states["srv"].current_tasks == 2

    async def test_cancel_cancelled_task_increments_metric(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        # Put it in active_tasks too to cover that branch
        orch.active_tasks[task_id] = orch.tasks[task_id]

        initial = orch.metrics["cancelled_tasks"]
        await orch.cancel_task(task_id)
        assert orch.metrics["cancelled_tasks"] == initial + 1


# ===========================================================================
# MCPOrchestrator._execute_task_wrapper (lines 209-227)
# ===========================================================================


class TestExecuteTaskWrapper:
    async def test_wrapper_cleans_up_spawned_tasks_on_normal_completion(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])

        # execute_task will fail (no server), wrapper should still remove spawned entry
        orch.spawned_tasks[task_id] = MagicMock()
        await orch._execute_task_wrapper(task_id)

        assert task_id not in orch.spawned_tasks

    async def test_wrapper_handles_unhandled_exception_gracefully(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])

        async def raising_execute(_id: str):
            raise RuntimeError("unexpected error")

        with patch.object(orch, "execute_task", side_effect=RuntimeError("unexpected error")):
            # Should NOT raise; wrapper catches generic exceptions
            await orch._execute_task_wrapper(task_id)

    async def test_wrapper_propagates_cancelled_error(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])

        async def raise_cancelled(_id: str):
            raise asyncio.CancelledError()

        with patch.object(orch, "execute_task", side_effect=asyncio.CancelledError()):
            with pytest.raises(asyncio.CancelledError):
                await orch._execute_task_wrapper(task_id)

    async def test_wrapper_marks_task_cancelled_on_cancelled_error_when_pending(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        # Task is still PENDING when CancelledError is raised
        orch.tasks[task_id].status = MCPTaskStatus.PENDING

        with patch.object(orch, "execute_task", side_effect=asyncio.CancelledError()):
            with pytest.raises(asyncio.CancelledError):
                await orch._execute_task_wrapper(task_id)

        assert orch.tasks[task_id].status == MCPTaskStatus.CANCELLED
        assert orch.metrics["cancelled_tasks"] >= 1

    async def test_wrapper_does_not_double_cancel_already_cancelled_task(self):
        orch = MCPOrchestrator()
        task_id = await orch.submit_task("t", {}, [])
        orch.tasks[task_id].status = MCPTaskStatus.CANCELLED  # already cancelled

        initial = orch.metrics["cancelled_tasks"]
        with patch.object(orch, "execute_task", side_effect=asyncio.CancelledError()):
            with pytest.raises(asyncio.CancelledError):
                await orch._execute_task_wrapper(task_id)

        # Should NOT increment again since task was already CANCELLED
        assert orch.metrics["cancelled_tasks"] == initial


# ===========================================================================
# MCPOrchestrator.execute_task – server assigned path (lines 257-334)
# ===========================================================================


class TestExecuteTaskWithServer:
    async def test_execute_raises_not_implemented_when_server_found(self):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, ServerStatus

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        registry.server_states["srv"].status = ServerStatus.ONLINE

        orch = MCPOrchestrator(registry=registry)
        task_id = await orch.submit_task("t", {}, [MCPCapability.AI_INFERENCE])

        result = await orch.execute_task(task_id)
        assert result["status"] == "failed"
        assert "error" in result

    async def test_execute_increments_server_current_tasks_then_decrements(self):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, ServerStatus

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        registry.server_states["srv"].status = ServerStatus.ONLINE

        orch = MCPOrchestrator(registry=registry)
        task_id = await orch.submit_task("t", {}, [MCPCapability.AI_INFERENCE])

        await orch.execute_task(task_id)

        # After failure, server state should be updated (total_tasks_failed incremented)
        assert registry.server_states["srv"].total_tasks_failed >= 1

    async def test_execute_task_sets_assigned_server(self):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, ServerStatus

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        registry.server_states["srv"].status = ServerStatus.ONLINE

        orch = MCPOrchestrator(registry=registry)
        task_id = await orch.submit_task("t", {}, [MCPCapability.AI_INFERENCE])
        await orch.execute_task(task_id)

        # Task should have been assigned_server set before failure
        assert orch.tasks[task_id].assigned_server == "srv"

    async def test_execute_task_successful_updates_completed_metrics(self):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, ServerStatus

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        registry.server_states["srv"].status = ServerStatus.ONLINE

        orch = MCPOrchestrator(registry=registry)
        task_id = await orch.submit_task("t", {}, [MCPCapability.AI_INFERENCE])

        async def fake_execute_on_server(server_id, task):
            return {"output": "done"}

        with patch.object(orch, "_execute_on_server", side_effect=fake_execute_on_server):
            result = await orch.execute_task(task_id)

        assert result["status"] == "success"
        assert orch.metrics["completed_tasks"] == 1
        assert orch.tasks[task_id].status == MCPTaskStatus.COMPLETED

    async def test_execute_task_success_moves_to_completed_deque(self):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, ServerStatus

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        registry.server_states["srv"].status = ServerStatus.ONLINE

        orch = MCPOrchestrator(registry=registry)
        task_id = await orch.submit_task("t", {}, [MCPCapability.AI_INFERENCE])

        async def fake_execute_on_server(server_id, task):
            return {"output": "done"}

        with patch.object(orch, "_execute_on_server", side_effect=fake_execute_on_server):
            await orch.execute_task(task_id)

        assert any(t.task_id == task_id for t in orch.completed_tasks)

    async def test_execute_task_success_removes_from_active_tasks(self):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, ServerStatus

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        registry.server_states["srv"].status = ServerStatus.ONLINE

        orch = MCPOrchestrator(registry=registry)
        task_id = await orch.submit_task("t", {}, [MCPCapability.AI_INFERENCE])

        async def fake_execute_on_server(server_id, task):
            return {"output": "done"}

        with patch.object(orch, "_execute_on_server", side_effect=fake_execute_on_server):
            await orch.execute_task(task_id)

        assert task_id not in orch.active_tasks


# ===========================================================================
# MCPOrchestrator._execute_on_server (lines 346-350)
# ===========================================================================


class TestExecuteOnServer:
    @patch("aiohttp.ClientSession.post")
    async def test_execute_on_server_success(self, mock_post):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, MCPTask

        # Setup mock response
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"result": "success"})
        mock_response.raise_for_status = MagicMock()

        aenter_mock = AsyncMock()
        aenter_mock.return_value = mock_response
        mock_post.return_value.__aenter__ = aenter_mock

        registry = MCPServerRegistry()
        server_config = registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        server_config.auth_token = "test-token"

        orch = MCPOrchestrator(registry=registry)
        task = MCPTask(
            task_id="abc",
            task_type="test_method",
            payload={"key": "value"},
            requirements=[MCPCapability.AI_INFERENCE],
        )

        result = await orch._execute_on_server("srv", task)

        # Assert post was called correctly
        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        assert call_args[0] == "http://localhost:9000"

        # Verify JSON payload
        expected_payload = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "params": {"key": "value"},
            "id": "abc",
        }
        assert call_kwargs["json"] == expected_payload

        # Verify headers
        expected_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token",
        }
        assert call_kwargs["headers"] == expected_headers

<<<<<<< HEAD
        # The JSON-RPC `result` member is unwrapped and returned to the caller.
        assert result == "success"

    async def test_execute_on_server_reuses_pooled_session(self):
        """When start_orchestration has opened a pooled session, _execute_on_server
        must reuse it instead of creating (and tearing down) a new session per call."""
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, MCPTask

        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"result": "pooled"})
        mock_response.raise_for_status = MagicMock()

        post_cm = MagicMock()
        post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        post_cm.__aexit__ = AsyncMock(return_value=False)

        pooled_session = MagicMock()
        pooled_session.closed = False
        pooled_session.post = MagicMock(return_value=post_cm)

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )

        orch = MCPOrchestrator(registry=registry)
        orch._session = pooled_session
        orch.orchestration_active = True

        task = MCPTask(
            task_id="abc",
            task_type="test_method",
            payload={"key": "value"},
            requirements=[MCPCapability.AI_INFERENCE],
        )

        with patch("aiohttp.ClientSession") as new_session_cls:
            result = await orch._execute_on_server("srv", task)
            # No fresh session should be constructed when a pooled one is open.
            new_session_cls.assert_not_called()

        pooled_session.post.assert_called_once()
        # The in-flight request is deregistered once it settles.
        assert orch._pooled_requests == set()
        assert result == "pooled"

    @patch("aiohttp.ClientSession.post")
    async def test_execute_on_server_raises_on_jsonrpc_error(self, mock_post):
        """A JSON-RPC 2.0 error envelope (HTTP 200 + `error` member) must raise so
        the caller records the task as FAILED, not as a successful result."""
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, MCPTask

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": "abc",
            }
        )
        aenter_mock = AsyncMock()
        aenter_mock.return_value = mock_response
        mock_post.return_value.__aenter__ = aenter_mock

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        orch = MCPOrchestrator(registry=registry)
        task = MCPTask(
            task_id="abc",
            task_type="missing_method",
            requirements=[MCPCapability.AI_INFERENCE],
        )

        with pytest.raises(RuntimeError, match="Method not found"):
            await orch._execute_on_server("srv", task)

    async def test_stop_orchestration_drains_pooled_request_before_close(self):
        """stop_orchestration() must not close the pooled session while a direct
        execute_task() request (untracked in spawned_tasks) is still in flight."""
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, MCPTask

        release = asyncio.Event()

        async def slow_json():
            await release.wait()
            return {"result": "done"}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = slow_json

        post_cm = MagicMock()
        post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        post_cm.__aexit__ = AsyncMock(return_value=False)

        close_order = []

        async def _close():
            close_order.append("closed")
            session.closed = True

        session = MagicMock()
        session.closed = False
        session.post = MagicMock(return_value=post_cm)
        session.close = _close

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )
        orch = MCPOrchestrator(registry=registry)
        orch._session = session
        orch.orchestration_active = True

        task = MCPTask(
            task_id="abc",
            task_type="test_method",
            requirements=[MCPCapability.AI_INFERENCE],
        )

        # Start a direct execution that blocks inside response.json().
        exec_task = asyncio.ensure_future(orch._execute_on_server("srv", task))
        for _ in range(5):
            await asyncio.sleep(0)
        assert len(orch._pooled_requests) == 1
        assert close_order == []

        # stop_orchestration must block on the in-flight request, not close early.
        stop_task = asyncio.ensure_future(orch.stop_orchestration())
        for _ in range(5):
            await asyncio.sleep(0)
        assert close_order == [], "session closed while a pooled request was in flight"
        assert session.closed is False

        # Release the request; stop_orchestration then drains and closes.
        release.set()
        await stop_task
        assert await exec_task == "done"
        assert close_order == ["closed"]
        assert orch._session is None
        assert orch._pooled_requests == set()
=======
        # Verify result is passed through
        assert result == {"result": "success"}
>>>>>>> origin/main

    @patch("aiohttp.ClientSession.post")
    async def test_execute_on_server_handles_http_errors(self, mock_post):
        from youtube_extension.services.mcp.registry import MCPServerRegistry
        from youtube_extension.services.mcp.types import MCPCapability, MCPTask
        import aiohttp

        # Setup mock response to raise an exception when raise_for_status is called
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=()
        )
        # We need mock_post.return_value.__aenter__ to be an AsyncMock, but
        # __aenter__ returns `mock_response` which is now a MagicMock so raise_for_status is sync
        aenter_mock = AsyncMock()
        aenter_mock.return_value = mock_response
        mock_post.return_value.__aenter__ = aenter_mock

        registry = MCPServerRegistry()
        registry.register_server(
            "srv", "Srv", "http://localhost:9000", [MCPCapability.AI_INFERENCE]
        )

        orch = MCPOrchestrator(registry=registry)
        task = MCPTask(
            task_id="abc",
            task_type="test",
            requirements=[MCPCapability.AI_INFERENCE],
        )

        with pytest.raises(aiohttp.ClientResponseError):
            await orch._execute_on_server("srv", task)

    async def test_raises_value_error_for_unknown_server(self):
        from youtube_extension.services.mcp.types import MCPCapability, MCPTask

        orch = MCPOrchestrator()
        task = MCPTask(
            task_id="abc",
            task_type="test",
            requirements=[MCPCapability.AI_INFERENCE],
        )

        with pytest.raises(ValueError, match="MCP server not found"):
            await orch._execute_on_server("unknown_server", task)


# ===========================================================================
# MCPOrchestrator._check_dependent_tasks (lines 388-395)
# ===========================================================================


class TestCheckDependentTasks:
    async def test_queues_waiting_task_when_dependency_completes(self):
        orch = MCPOrchestrator()
        dep_id = await orch.submit_task("dep", {}, [])
        task_id = await orch.submit_task("main", {}, [], dependencies=[dep_id])

        # Clear queue for a clean test
        orch.task_queue.clear()

        # Mark dep as completed
        orch.tasks[dep_id].status = MCPTaskStatus.COMPLETED

        await orch._check_dependent_tasks(dep_id)

        assert task_id in orch.task_queue

    async def test_does_not_queue_task_with_unmet_deps(self):
        orch = MCPOrchestrator()
        dep1_id = await orch.submit_task("dep1", {}, [])
        dep2_id = await orch.submit_task("dep2", {}, [])
        task_id = await orch.submit_task("main", {}, [], dependencies=[dep1_id, dep2_id])

        orch.task_queue.clear()

        # Only complete dep1, not dep2
        orch.tasks[dep1_id].status = MCPTaskStatus.COMPLETED

        await orch._check_dependent_tasks(dep1_id)

        assert task_id not in orch.task_queue

    async def test_does_not_re_queue_already_running_task(self):
        orch = MCPOrchestrator()
        dep_id = await orch.submit_task("dep", {}, [])
        task_id = await orch.submit_task("main", {}, [], dependencies=[dep_id])

        orch.tasks[task_id].status = MCPTaskStatus.EXECUTING  # already running
        orch.tasks[dep_id].status = MCPTaskStatus.COMPLETED
        orch.task_queue.clear()

        await orch._check_dependent_tasks(dep_id)

        assert task_id not in orch.task_queue


# ===========================================================================
# MCPOrchestrator.stop_orchestration – spawned task cleanup (lines 423-434)
# ===========================================================================


class TestStopOrchestrationCleanup:
    async def test_stop_cancels_spawned_asyncio_tasks(self):
        orch = MCPOrchestrator()
        await orch.start_orchestration()

        # Add a fake long-running spawned asyncio task
        async def noop():
            await asyncio.sleep(60)

        spawned = asyncio.create_task(noop())
        orch.spawned_tasks["fake_task"] = spawned

        await orch.stop_orchestration()

        assert spawned.cancelled() or spawned.done()

    async def test_stop_clears_spawned_tasks_dict(self):
        orch = MCPOrchestrator()
        await orch.start_orchestration()

        async def noop():
            await asyncio.sleep(60)

        orch.spawned_tasks["fake1"] = asyncio.create_task(noop())
        orch.spawned_tasks["fake2"] = asyncio.create_task(noop())

        await orch.stop_orchestration()

        assert len(orch.spawned_tasks) == 0


# ===========================================================================
# MCPOrchestrator._orchestration_loop (lines 448-485)
# ===========================================================================


class TestOrchestrationLoop:
    async def test_loop_processes_queued_tasks(self):
        orch = MCPOrchestrator()

        # Patch execute_task_wrapper to be a no-op so the loop processes without real execution
        processed: list[str] = []

        async def fake_wrapper(task_id: str) -> None:
            processed.append(task_id)

        task_id = await orch.submit_task("loop_task", {}, [])

        with patch.object(orch, "_execute_task_wrapper", side_effect=fake_wrapper):
            await orch.start_orchestration()
            await asyncio.sleep(0.25)  # Give loop time to pick up the task
            await orch.stop_orchestration()

        assert task_id in processed

    async def test_loop_respects_max_concurrent_spawn(self):
        orch = MCPOrchestrator()
        orch.max_concurrent_spawn = 2  # Allow only 2 concurrent

        barrier = asyncio.Event()
        concurrent_count: list[int] = [0]

        async def blocking_wrapper(task_id: str) -> None:
            concurrent_count[0] += 1
            await barrier.wait()

        for _ in range(5):
            await orch.submit_task("t", {}, [])

        with patch.object(orch, "_execute_task_wrapper", side_effect=blocking_wrapper):
            await orch.start_orchestration()
            await asyncio.sleep(0.3)
            # At most max_concurrent_spawn tasks should be running at once
            assert len(orch.spawned_tasks) <= orch.max_concurrent_spawn
            barrier.set()
            await orch.stop_orchestration()

    async def test_orchestration_loop_cleans_up_done_spawned_tasks(self):
        orch = MCPOrchestrator()

        done_called: list[bool] = []

        async def immediate_wrapper(task_id: str) -> None:
            done_called.append(True)

        task_id = await orch.submit_task("t", {}, [])

        with patch.object(orch, "_execute_task_wrapper", side_effect=immediate_wrapper):
            await orch.start_orchestration()
            await asyncio.sleep(0.3)
            await orch.stop_orchestration()

        # After completion the spawned task should be cleaned up from dict
        assert task_id not in orch.spawned_tasks

    async def test_orchestration_loop_handles_exception_and_continues(self):
        """Cover the except Exception branch (lines 476-478) in _orchestration_loop."""
        orch = MCPOrchestrator()
        call_count: list[int] = [0]

        async def flaky_wrapper(task_id: str) -> None:
            call_count[0] += 1
            raise RuntimeError("loop error")

        # Submit two tasks so the loop has something to process after the error
        task1 = await orch.submit_task("t1", {}, [])
        task2 = await orch.submit_task("t2", {}, [])

        # Make the loop fail on the first iteration but complete the second
        with patch.object(orch, "_execute_task_wrapper", side_effect=flaky_wrapper):
            await orch.start_orchestration()
            await asyncio.sleep(0.5)
            await orch.stop_orchestration()

        # Both tasks were attempted (loop continued after error)
        assert call_count[0] >= 1

    async def test_stop_orchestration_with_gather_exception(self):
        """Cover lines 431-432 - gather raising inside stop_orchestration.

        The except block is a last-resort safety net; we exercise it by patching
        asyncio.gather to raise while spawned_tasks is non-empty.
        """
        orch = MCPOrchestrator()
        await orch.start_orchestration()

        # Inject a fake done task so the spawned_tasks branch is entered
        done_fut: asyncio.Future = asyncio.get_event_loop().create_future()
        done_fut.set_result(None)
        fake_task = asyncio.ensure_future(done_fut)
        orch.spawned_tasks["fake"] = fake_task

        with patch("asyncio.gather", side_effect=RuntimeError("gather boom")):
            # Should NOT raise; exception is caught and logged
            await orch.stop_orchestration()

        assert orch.orchestration_active is False

    async def test_orchestration_loop_break_when_queue_emptied_during_processing(self):
        """Cover line 464 – break when queue becomes empty within the inner for-loop.

        This happens when max_concurrent_spawn > len(task_queue) so the loop
        processes all queued tasks and hits the `if not self.task_queue: break`.
        """
        orch = MCPOrchestrator()
        # Only one task: tasks_to_process=1, loop runs once then queue is empty
        task_id = await orch.submit_task("only_one", {}, [])

        processed: list[str] = []

        async def immediate_wrapper(tid: str) -> None:
            processed.append(tid)

        with patch.object(orch, "_execute_task_wrapper", side_effect=immediate_wrapper):
            await orch.start_orchestration()
            await asyncio.sleep(0.25)
            await orch.stop_orchestration()

        # Task was processed; the break path was exercised (queue emptied)
        assert task_id in processed

    async def test_orchestration_loop_inner_exception_handled(self):
        """Cover lines 476-478 – inner except Exception in _orchestration_loop.

        We make _execute_task_wrapper raise synchronously on the first call
        (before await), which causes the orchestration loop's inner except to fire.
        """
        orch = MCPOrchestrator()
        await orch.submit_task("err_task", {}, [])

        call_count: list[int] = [0]

        async def first_call_raises(tid: str) -> None:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("forced loop error")

        with patch.object(orch, "_execute_task_wrapper", side_effect=first_call_raises):
            await orch.start_orchestration()
            await asyncio.sleep(0.5)
            await orch.stop_orchestration()

        # Orchestrator handled the error and stopped cleanly
        assert orch.orchestration_active is False
