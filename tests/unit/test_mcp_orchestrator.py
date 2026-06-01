"""Unit tests for services/mcp/orchestrator.py."""

from __future__ import annotations

import sys
import types as _types
from pathlib import Path

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
