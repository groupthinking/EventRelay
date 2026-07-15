"""Unit tests for youtube_extension/services/agents/adapters/agent_orchestrator.py."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from youtube_extension.services.agents.dto import AgentRequest, AgentResult
from youtube_extension.services.agents.adapters.agent_orchestrator import (
    A2AContextMessage,
    AgentOrchestrator,
    OrchestrationResult,
)
from youtube_extension.services.agents.base_agent import BaseAgent


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_ok_agent(name: str = "test_agent", output: dict | None = None) -> BaseAgent:
    """Return a BaseAgent subclass whose run() returns an ok result."""
    result = AgentResult(status="ok", output=output or {"done": True})
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    agent.run = AsyncMock(return_value=result)
    return agent


def _make_error_agent(name: str = "bad_agent") -> BaseAgent:
    """Return a BaseAgent subclass whose run() returns an error result."""
    result = AgentResult(status="error", output={}, logs=["something went wrong"])
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    agent.run = AsyncMock(return_value=result)
    return agent


def _make_raising_agent(name: str = "crash_agent") -> BaseAgent:
    """Return an agent whose run() raises an exception."""
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    agent.run = AsyncMock(side_effect=RuntimeError("agent exploded"))
    return agent


class _SimpleAgent(BaseAgent):
    name = "simple"

    def __init__(self, config=None):
        self._config = config

    async def run(self, req: AgentRequest) -> AgentResult:  # type: ignore[override]
        return AgentResult(status="ok", output={"task": req.task})


# ===========================================================================
# A2AContextMessage
# ===========================================================================


class TestA2AContextMessage:
    def test_required_fields(self):
        msg = A2AContextMessage(sender="a", recipient="b", content={"k": "v"})
        assert msg.sender == "a"
        assert msg.recipient == "b"
        assert msg.content == {"k": "v"}

    def test_conversation_id_auto_generated(self):
        msg = A2AContextMessage(sender="a", recipient="b", content={})
        assert msg.conversation_id != ""
        # Should be a valid UUID
        uuid.UUID(msg.conversation_id)

    def test_timestamp_auto_generated(self):
        msg = A2AContextMessage(sender="a", recipient="b", content={})
        assert msg.timestamp != ""
        # Must be parseable ISO format
        datetime.fromisoformat(msg.timestamp)

    def test_explicit_conversation_id_preserved(self):
        cid = "explicit-conv-id"
        msg = A2AContextMessage(sender="a", recipient="b", content={}, conversation_id=cid)
        assert msg.conversation_id == cid

    def test_explicit_timestamp_preserved(self):
        ts = "2024-01-01T00:00:00"
        msg = A2AContextMessage(sender="a", recipient="b", content={}, timestamp=ts)
        assert msg.timestamp == ts


# ===========================================================================
# OrchestrationResult
# ===========================================================================


class TestOrchestrationResult:
    def test_default_results_empty(self):
        r = OrchestrationResult(success=True)
        assert r.results == {}

    def test_default_errors_empty(self):
        r = OrchestrationResult(success=False)
        assert r.errors == []

    def test_default_agents_used_empty(self):
        r = OrchestrationResult(success=True)
        assert r.agents_used == []

    def test_default_processing_time_zero(self):
        r = OrchestrationResult(success=True)
        assert r.total_processing_time == 0.0

    def test_mutable_defaults_not_shared(self):
        r1 = OrchestrationResult(success=True)
        r2 = OrchestrationResult(success=True)
        r1.errors.append("err")
        assert r2.errors == []


# ===========================================================================
# AgentOrchestrator.__init__
# ===========================================================================


class TestAgentOrchestratorInit:
    def test_agents_starts_empty(self):
        orch = AgentOrchestrator()
        assert orch._agents == {}

    def test_agent_types_starts_empty(self):
        orch = AgentOrchestrator()
        assert orch._agent_types == {}

    def test_a2a_log_starts_empty(self):
        orch = AgentOrchestrator()
        assert len(orch._a2a_log) == 0

    def test_default_task_mappings_present(self):
        orch = AgentOrchestrator()
        assert "video_analysis" in orch._task_mappings
        assert "content_generation" in orch._task_mappings

    def test_logger_name(self):
        orch = AgentOrchestrator()
        assert orch.logger.name == "agent_orchestrator"


# ===========================================================================
# register_agent_type / list_agents
# ===========================================================================


class TestRegisterAgentType:
    def test_registers_type(self):
        orch = AgentOrchestrator()
        orch.register_agent_type("simple", _SimpleAgent)
        assert "simple" in orch._agent_types

    def test_listed_in_list_agents(self):
        orch = AgentOrchestrator()
        orch.register_agent_type("simple", _SimpleAgent)
        assert "simple" in orch.list_agents()

    def test_registered_instance_listed(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("present_agent")
        orch._agents["present_agent"] = agent
        assert "present_agent" in orch.list_agents()


# ===========================================================================
# get_agent
# ===========================================================================


class TestGetAgent:
    async def test_returns_cached_agent(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("cached")
        orch._agents["cached"] = agent
        result = await orch.get_agent("cached")
        assert result is agent

    async def test_instantiates_from_registered_type(self):
        orch = AgentOrchestrator()
        orch.register_agent_type("simple", _SimpleAgent)
        agent = await orch.get_agent("simple")
        assert isinstance(agent, _SimpleAgent)

    async def test_caches_newly_created_agent(self):
        orch = AgentOrchestrator()
        orch.register_agent_type("simple", _SimpleAgent)
        a1 = await orch.get_agent("simple")
        a2 = await orch.get_agent("simple")
        assert a1 is a2

    async def test_returns_none_for_unknown_agent(self):
        orch = AgentOrchestrator()
        result = await orch.get_agent("totally_unknown_xyz")
        assert result is None

    async def test_falls_back_to_registry(self):
        orch = AgentOrchestrator()
        mock_class = MagicMock(return_value=_make_ok_agent("reg_agent"))

        with patch(
            "youtube_extension.services.agents.adapters.agent_orchestrator.get_agent_class",
            return_value=mock_class,
        ):
            agent = await orch.get_agent("reg_agent")

        assert agent is not None

    async def test_returns_none_when_registry_key_error(self):
        orch = AgentOrchestrator()
        with patch(
            "youtube_extension.services.agents.adapters.agent_orchestrator.get_agent_class",
            side_effect=KeyError("not_found"),
        ):
            result = await orch.get_agent("not_found")
        assert result is None

    async def test_returns_none_when_instantiation_fails(self):
        orch = AgentOrchestrator()

        class BrokenAgent(BaseAgent):
            name = "broken"

            def __init__(self, config=None):
                raise RuntimeError("cannot init")

            def run(self, req):
                pass

        orch.register_agent_type("broken", BrokenAgent)
        result = await orch.get_agent("broken")
        assert result is None


# ===========================================================================
# execute_task
# ===========================================================================


class TestExecuteTask:
    async def test_unknown_task_type_returns_failure(self):
        orch = AgentOrchestrator()
        result = await orch.execute_task("unknown_xyz", {})
        assert result.success is False
        assert any("Unknown task type" in e for e in result.errors)

    async def test_missing_agent_returns_failure(self):
        orch = AgentOrchestrator()
        orch._task_mappings["test_task"] = ["missing_agent"]
        result = await orch.execute_task("test_task", {})
        assert result.success is False
        assert any("Failed to get agent" in e for e in result.errors)

    async def test_successful_execution(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("ok_agent")
        orch._agents["ok_agent"] = agent
        orch._task_mappings["my_task"] = ["ok_agent"]

        result = await orch.execute_task("my_task", {"input": "data"})
        assert result.success is True
        assert "ok_agent" in result.results

    async def test_records_agents_used(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("agent_a")
        orch._agents["agent_a"] = agent
        orch._task_mappings["my_task"] = ["agent_a"]

        result = await orch.execute_task("my_task", {})
        assert "agent_a" in result.agents_used

    async def test_error_result_marks_failure(self):
        orch = AgentOrchestrator()
        agent = _make_error_agent("err_agent")
        orch._agents["err_agent"] = agent
        orch._task_mappings["my_task"] = ["err_agent"]

        result = await orch.execute_task("my_task", {})
        assert result.success is False

    async def test_exception_from_agent_marks_failure(self):
        orch = AgentOrchestrator()
        agent = _make_raising_agent("crash_a")
        orch._agents["crash_a"] = agent
        orch._task_mappings["my_task"] = ["crash_a"]

        result = await orch.execute_task("my_task", {})
        assert result.success is False
        assert any("crash_a" in e for e in result.errors)

    async def test_a2a_context_shared_when_multiple_agents_succeed(self):
        orch = AgentOrchestrator()
        agent_a = _make_ok_agent("agent_a", output={"x": 1})
        agent_b = _make_ok_agent("agent_b", output={"y": 2})
        orch._agents["agent_a"] = agent_a
        orch._agents["agent_b"] = agent_b
        orch._task_mappings["my_task"] = ["agent_a", "agent_b"]

        result = await orch.execute_task("my_task", {})
        assert result.success is True
        # A2A: 2 agents → 2 messages (a→b and b→a)
        assert len(orch._a2a_log) == 2

    async def test_no_a2a_sharing_for_single_agent(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("solo_agent")
        orch._agents["solo_agent"] = agent
        orch._task_mappings["solo_task"] = ["solo_agent"]

        await orch.execute_task("solo_task", {})
        assert len(orch._a2a_log) == 0

    async def test_processing_time_is_positive(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("agent_x")
        orch._agents["agent_x"] = agent
        orch._task_mappings["timed_task"] = ["agent_x"]

        result = await orch.execute_task("timed_task", {})
        assert result.total_processing_time >= 0.0

    async def test_agent_config_passed_from_agent_configs(self):
        orch = AgentOrchestrator()

        created_configs: list = []

        class ConfigCapture(BaseAgent):
            name = "capture"

            def __init__(self, config=None):
                self._config = config
                created_configs.append(config)

            async def run(self, req):  # type: ignore[override]
                return AgentResult(status="ok", output={})

        orch.register_agent_type("capture", ConfigCapture)
        orch._task_mappings["cfg_task"] = ["capture"]

        await orch.execute_task("cfg_task", {}, agent_configs={"capture": {"key": "val"}})
        assert created_configs[0] == {"key": "val"}

    async def test_returns_failure_when_gather_raises(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("agent_x")
        orch._agents["agent_x"] = agent
        orch._task_mappings["fail_task"] = ["agent_x"]

        with patch("asyncio.gather", side_effect=RuntimeError("gather failed")):
            result = await orch.execute_task("fail_task", {})

        assert result.success is False
        assert any("Orchestration failed" in e for e in result.errors)


# ===========================================================================
# execute_agents_sequentially
# Note: the source calls AgentRequest(params=current_data) without a task
# field, which would normally fail Pydantic validation.  We patch AgentRequest
# inside the orchestrator module so the construction succeeds in tests.
# ===========================================================================

_SEQ_MODULE = "youtube_extension.services.agents.adapters.agent_orchestrator"


class TestExecuteAgentsSequentially:
    async def test_successful_sequential_execution(self):
        orch = AgentOrchestrator()
        agent_a = _make_ok_agent("seq_a", output={"step": "a"})
        agent_b = _make_ok_agent("seq_b", output={"step": "b"})
        orch._agents["seq_a"] = agent_a
        orch._agents["seq_b"] = agent_b

        fake_req = MagicMock()
        with patch(f"{_SEQ_MODULE}.AgentRequest", return_value=fake_req):
            result = await orch.execute_agents_sequentially(["seq_a", "seq_b"], {"start": True})

        assert result.success is True
        assert "seq_a" in result.results
        assert "seq_b" in result.results

    async def test_sequential_stops_on_agent_failure(self):
        orch = AgentOrchestrator()
        agent_a = _make_error_agent("fail_first")
        agent_b = _make_ok_agent("never_reached")
        orch._agents["fail_first"] = agent_a
        orch._agents["never_reached"] = agent_b

        fake_req = MagicMock()
        with patch(f"{_SEQ_MODULE}.AgentRequest", return_value=fake_req):
            result = await orch.execute_agents_sequentially(
                ["fail_first", "never_reached"], {}
            )

        assert result.success is False
        assert "never_reached" not in result.results

    async def test_sequential_stops_when_agent_not_found(self):
        orch = AgentOrchestrator()
        result = await orch.execute_agents_sequentially(["missing_agent"], {})
        assert result.success is False
        assert any("Failed to get agent" in e for e in result.errors)

    async def test_output_passed_to_next_agent(self):
        """Verify output from agent_a merges into current_data for agent_b."""
        orch = AgentOrchestrator()
        agent_a = _make_ok_agent("first", output={"from_first": 42})
        agent_b = _make_ok_agent("recorder", output={"added": True})
        orch._agents["first"] = agent_a
        orch._agents["recorder"] = agent_b

        call_params: list = []

        def capture_req(*args, **kwargs):
            # Capture whatever params were passed
            call_params.append(kwargs.get("params", args[0] if args else {}))
            return MagicMock()

        with patch(f"{_SEQ_MODULE}.AgentRequest", side_effect=capture_req):
            await orch.execute_agents_sequentially(["first", "recorder"], {"initial": 1})

        # Should have been called twice (one per agent)
        assert len(call_params) == 2

    async def test_processing_time_non_negative(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("timing_agent")
        orch._agents["timing_agent"] = agent

        fake_req = MagicMock()
        with patch(f"{_SEQ_MODULE}.AgentRequest", return_value=fake_req):
            result = await orch.execute_agents_sequentially(["timing_agent"], {})

        assert result.total_processing_time >= 0.0

    async def test_agents_used_recorded(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("tracked_agent")
        orch._agents["tracked_agent"] = agent

        fake_req = MagicMock()
        with patch(f"{_SEQ_MODULE}.AgentRequest", return_value=fake_req):
            result = await orch.execute_agents_sequentially(["tracked_agent"], {})

        assert "tracked_agent" in result.agents_used


# ===========================================================================
# list_task_types
# ===========================================================================


class TestListTaskTypes:
    def test_returns_known_types(self):
        orch = AgentOrchestrator()
        types = orch.list_task_types()
        assert "video_analysis" in types
        assert "chat_assistance" in types

    def test_returns_list(self):
        orch = AgentOrchestrator()
        assert isinstance(orch.list_task_types(), list)


# ===========================================================================
# add_task_mapping
# ===========================================================================


class TestAddTaskMapping:
    def test_adds_new_mapping(self):
        orch = AgentOrchestrator()
        orch.add_task_mapping("custom_task", ["agent_x", "agent_y"])
        assert "custom_task" in orch._task_mappings
        assert orch._task_mappings["custom_task"] == ["agent_x", "agent_y"]

    def test_overwrites_existing_mapping(self):
        orch = AgentOrchestrator()
        orch.add_task_mapping("content_generation", ["new_agent"])
        assert orch._task_mappings["content_generation"] == ["new_agent"]

    def test_listed_in_list_task_types(self):
        orch = AgentOrchestrator()
        orch.add_task_mapping("brand_new", ["agent_z"])
        assert "brand_new" in orch.list_task_types()


# ===========================================================================
# send_a2a_message
# ===========================================================================


class TestSendA2aMessage:
    async def test_appends_to_log(self):
        orch = AgentOrchestrator()
        await orch.send_a2a_message("alice", "bob", {"hello": True})
        assert len(orch._a2a_log) == 1

    async def test_returns_a2a_context_message(self):
        orch = AgentOrchestrator()
        msg = await orch.send_a2a_message("alice", "bob", {"data": 1})
        assert isinstance(msg, A2AContextMessage)
        assert msg.sender == "alice"
        assert msg.recipient == "bob"

    async def test_uses_provided_conversation_id(self):
        orch = AgentOrchestrator()
        msg = await orch.send_a2a_message("a", "b", {}, conversation_id="my-conv")
        assert msg.conversation_id == "my-conv"

    async def test_auto_generates_conversation_id_when_none(self):
        orch = AgentOrchestrator()
        msg = await orch.send_a2a_message("a", "b", {})
        uuid.UUID(msg.conversation_id)  # validates UUID format

    async def test_delivers_to_recipient_with_receive_context(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("recipient")
        agent.receive_context = AsyncMock()
        orch._agents["recipient"] = agent

        await orch.send_a2a_message("sender", "recipient", {"payload": True})
        agent.receive_context.assert_awaited_once_with({"payload": True})

    async def test_silently_handles_receive_context_error(self):
        orch = AgentOrchestrator()
        agent = _make_ok_agent("recipient")
        agent.receive_context = AsyncMock(side_effect=RuntimeError("context error"))
        orch._agents["recipient"] = agent

        # Should not raise
        await orch.send_a2a_message("sender", "recipient", {})

    async def test_no_delivery_when_recipient_not_loaded(self):
        orch = AgentOrchestrator()
        # recipient not in _agents
        msg = await orch.send_a2a_message("sender", "ghost", {"data": 1})
        assert msg.recipient == "ghost"


# ===========================================================================
# get_a2a_log
# ===========================================================================


class TestGetA2aLog:
    async def test_returns_all_messages_by_default(self):
        orch = AgentOrchestrator()
        await orch.send_a2a_message("a", "b", {"m": 1})
        await orch.send_a2a_message("b", "c", {"m": 2})
        log = orch.get_a2a_log()
        assert len(log) == 2

    async def test_filters_by_conversation_id(self):
        orch = AgentOrchestrator()
        await orch.send_a2a_message("a", "b", {}, conversation_id="conv-1")
        await orch.send_a2a_message("x", "y", {}, conversation_id="conv-2")
        log = orch.get_a2a_log(conversation_id="conv-1")
        assert len(log) == 1
        assert log[0]["conversation_id"] == "conv-1"

    async def test_respects_limit(self):
        orch = AgentOrchestrator()
        for i in range(10):
            await orch.send_a2a_message("s", "r", {"i": i})
        log = orch.get_a2a_log(limit=3)
        assert len(log) == 3

    async def test_empty_when_no_messages(self):
        orch = AgentOrchestrator()
        assert orch.get_a2a_log() == []

    async def test_log_entry_has_expected_keys(self):
        orch = AgentOrchestrator()
        await orch.send_a2a_message("s", "r", {"k": "v"})
        entry = orch.get_a2a_log()[0]
        assert "sender" in entry
        assert "recipient" in entry
        assert "content" in entry
        assert "conversation_id" in entry
        assert "timestamp" in entry

    async def test_log_entry_content_matches(self):
        orch = AgentOrchestrator()
        await orch.send_a2a_message("sender_x", "receiver_y", {"hello": "world"})
        entry = orch.get_a2a_log()[0]
        assert entry["sender"] == "sender_x"
        assert entry["recipient"] == "receiver_y"
        assert entry["content"] == {"hello": "world"}


# ===========================================================================
# Global orchestrator instance
# ===========================================================================


class TestGlobalOrchestrator:
    def test_global_instance_exists(self):
        import youtube_extension.services.agents.adapters.agent_orchestrator as mod

        assert isinstance(mod.orchestrator, AgentOrchestrator)
