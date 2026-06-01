"""Unit tests for MCP types: enums, MCPServerConfig, MCPTask, MCPServerState."""

from __future__ import annotations

import importlib.util
import sys
import types as _types
from datetime import datetime
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))


def _inject_stub(name: str, path: str) -> None:
    if name not in sys.modules:
        stub = _types.ModuleType(name)
        stub.__path__ = [path]
        stub.__package__ = name
        sys.modules[name] = stub


def _load(rel_path: str, canonical: str):
    """Load a module via importlib and register it in sys.modules for coverage tracking."""
    full = _SRC / rel_path
    spec = importlib.util.spec_from_file_location(canonical, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[canonical] = mod
    spec.loader.exec_module(mod)
    return mod


# Stub parent packages to prevent broken __init__.py from loading
_inject_stub("youtube_extension.services", str(_SRC / "youtube_extension/services"))
_inject_stub("youtube_extension.services.mcp", str(_SRC / "youtube_extension/services/mcp"))
_inject_stub("youtube_extension.services.agents", str(_SRC / "youtube_extension/services/agents"))

_types_mod = _load("youtube_extension/services/mcp/types.py", "youtube_extension.services.mcp.types")
MCPCapability = _types_mod.MCPCapability
MCPServerConfig = _types_mod.MCPServerConfig
MCPServerState = _types_mod.MCPServerState
MCPTask = _types_mod.MCPTask
MCPTaskStatus = _types_mod.MCPTaskStatus
ServerStatus = _types_mod.ServerStatus


# ===========================================================================
# ServerStatus enum
# ===========================================================================


class TestServerStatusEnum:
    def test_online_value(self):
        assert ServerStatus.ONLINE.value == "online"

    def test_offline_value(self):
        assert ServerStatus.OFFLINE.value == "offline"

    def test_starting_value(self):
        assert ServerStatus.STARTING.value == "starting"

    def test_error_value(self):
        assert ServerStatus.ERROR.value == "error"

    def test_maintenance_value(self):
        assert ServerStatus.MAINTENANCE.value == "maintenance"

    def test_has_five_members(self):
        assert len(ServerStatus) == 5


# ===========================================================================
# MCPCapability enum
# ===========================================================================


class TestMCPCapabilityEnum:
    def test_video_transcription_value(self):
        assert MCPCapability.VIDEO_TRANSCRIPTION.value == "video_transcription"

    def test_ai_inference_value(self):
        assert MCPCapability.AI_INFERENCE.value == "ai_inference"

    def test_semantic_search_value(self):
        assert MCPCapability.SEMANTIC_SEARCH.value == "semantic_search"

    def test_data_processing_value(self):
        assert MCPCapability.DATA_PROCESSING.value == "data_processing"

    def test_file_operations_value(self):
        assert MCPCapability.FILE_OPERATIONS.value == "file_operations"

    def test_monitoring_value(self):
        assert MCPCapability.MONITORING.value == "monitoring"


# ===========================================================================
# MCPTaskStatus enum
# ===========================================================================


class TestMCPTaskStatusEnum:
    def test_pending_value(self):
        assert MCPTaskStatus.PENDING.value == "pending"

    def test_routing_value(self):
        assert MCPTaskStatus.ROUTING.value == "routing"

    def test_executing_value(self):
        assert MCPTaskStatus.EXECUTING.value == "executing"

    def test_completed_value(self):
        assert MCPTaskStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert MCPTaskStatus.FAILED.value == "failed"

    def test_cancelled_value(self):
        assert MCPTaskStatus.CANCELLED.value == "cancelled"

    def test_has_six_members(self):
        assert len(MCPTaskStatus) == 6


# ===========================================================================
# MCPServerConfig
# ===========================================================================


def _make_config(**kwargs):
    defaults = dict(
        id="server-1",
        name="Test Server",
        endpoint="http://localhost:8080",
    )
    defaults.update(kwargs)
    return MCPServerConfig(**defaults)


class TestMCPServerConfig:
    def test_required_fields_stored(self):
        c = _make_config()
        assert c.id == "server-1"
        assert c.name == "Test Server"
        assert c.endpoint == "http://localhost:8080"

    def test_capabilities_defaults_empty(self):
        assert _make_config().capabilities == []

    def test_protocol_default(self):
        assert _make_config().protocol == "http"

    def test_port_default_none(self):
        assert _make_config().port is None

    def test_auth_token_default_none(self):
        assert _make_config().auth_token is None

    def test_health_check_interval_default(self):
        assert _make_config().health_check_interval == 30

    def test_timeout_default(self):
        assert _make_config().timeout == 30

    def test_priority_default(self):
        assert _make_config().priority == 3

    def test_max_concurrent_tasks_default(self):
        assert _make_config().max_concurrent_tasks == 10

    def test_version_default(self):
        assert _make_config().version == "1.0.0"

    def test_tags_default_empty(self):
        assert _make_config().tags == []

    def test_metadata_default_empty(self):
        assert _make_config().metadata == {}

    def test_https_endpoint_accepted(self):
        c = _make_config(endpoint="https://api.example.com")
        assert "https" in c.endpoint

    def test_invalid_endpoint_raises(self):
        with pytest.raises(Exception):
            _make_config(endpoint="not-a-url")

    def test_ftp_endpoint_raises(self):
        with pytest.raises(Exception):
            _make_config(endpoint="ftp://server.com/files")

    def test_capabilities_set(self):
        caps = [MCPCapability.VIDEO_TRANSCRIPTION, MCPCapability.AI_INFERENCE]
        c = _make_config(capabilities=caps)
        assert len(c.capabilities) == 2


# ===========================================================================
# MCPTask
# ===========================================================================


def _make_task(**kwargs):
    defaults = dict(task_id="task-1", task_type="transcribe")
    defaults.update(kwargs)
    return MCPTask(**defaults)


class TestMCPTask:
    def test_required_fields_stored(self):
        t = _make_task()
        assert t.task_id == "task-1"
        assert t.task_type == "transcribe"

    def test_payload_default_empty(self):
        assert _make_task().payload == {}

    def test_requirements_default_empty(self):
        assert _make_task().requirements == []

    def test_priority_default(self):
        assert _make_task().priority == 3

    def test_timeout_default(self):
        assert _make_task().timeout == 300

    def test_retry_count_default(self):
        assert _make_task().retry_count == 3

    def test_status_default_pending(self):
        assert _make_task().status == MCPTaskStatus.PENDING

    def test_assigned_server_default_none(self):
        assert _make_task().assigned_server is None

    def test_result_default_none(self):
        assert _make_task().result is None

    def test_error_default_none(self):
        assert _make_task().error is None

    def test_created_at_auto_set(self):
        before = datetime.utcnow()
        t = _make_task()
        assert t.created_at >= before

    def test_started_at_default_none(self):
        assert _make_task().started_at is None

    def test_completed_at_default_none(self):
        assert _make_task().completed_at is None

    def test_dependencies_default_empty(self):
        assert _make_task().dependencies == []

    def test_depends_on_completion_default_true(self):
        assert _make_task().depends_on_completion is True


# ===========================================================================
# MCPServerState
# ===========================================================================


def _make_state(**kwargs):
    defaults = dict(server_id="s1", status=ServerStatus.ONLINE)
    defaults.update(kwargs)
    return MCPServerState(**defaults)


class TestMCPServerState:
    def test_required_fields_stored(self):
        s = _make_state()
        assert s.server_id == "s1"
        assert s.status == ServerStatus.ONLINE

    def test_current_tasks_default_zero(self):
        assert _make_state().current_tasks == 0

    def test_total_tasks_completed_default_zero(self):
        assert _make_state().total_tasks_completed == 0

    def test_total_tasks_failed_default_zero(self):
        assert _make_state().total_tasks_failed == 0

    def test_average_response_time_default_zero(self):
        assert _make_state().average_response_time == 0.0

    def test_load_factor_default_zero(self):
        assert _make_state().load_factor == 0.0

    def test_error_rate_default_zero(self):
        assert _make_state().error_rate == 0.0

    def test_last_health_check_default_none(self):
        assert _make_state().last_health_check is None

    def test_consecutive_failures_default_zero(self):
        assert _make_state().consecutive_failures == 0

    def test_uptime_seconds_default_zero(self):
        assert _make_state().uptime_seconds == 0

    def test_started_at_auto_set(self):
        before = datetime.utcnow()
        s = _make_state()
        assert s.started_at >= before


# ===========================================================================
# AgentRequest / AgentResult (dto module)
# ===========================================================================


_dto_mod = _load("youtube_extension/services/agents/dto.py", "youtube_extension.services.agents.dto")
AgentRequest = _dto_mod.AgentRequest
AgentResult = _dto_mod.AgentResult


class TestAgentRequest:
    def test_task_stored(self):
        r = AgentRequest(task="summarize")
        assert r.task == "summarize"

    def test_params_default_empty(self):
        r = AgentRequest(task="summarize")
        assert r.params == {}

    def test_video_pack_id_default_none(self):
        r = AgentRequest(task="summarize")
        assert r.video_pack_id is None

    def test_explicit_params(self):
        r = AgentRequest(task="summarize", params={"max_words": 100})
        assert r.params["max_words"] == 100

    def test_video_pack_id_set(self):
        r = AgentRequest(task="summarize", video_pack_id="vp-123")
        assert r.video_pack_id == "vp-123"


class TestAgentResult:
    def test_status_stored(self):
        r = AgentResult(status="ok")
        assert r.status == "ok"

    def test_output_default_empty(self):
        r = AgentResult(status="ok")
        assert r.output == {}

    def test_logs_default_empty(self):
        r = AgentResult(status="ok")
        assert r.logs == []

    def test_explicit_output(self):
        r = AgentResult(status="ok", output={"summary": "text"})
        assert r.output["summary"] == "text"

    def test_explicit_logs(self):
        r = AgentResult(status="error", logs=["Error occurred"])
        assert r.logs == ["Error occurred"]
