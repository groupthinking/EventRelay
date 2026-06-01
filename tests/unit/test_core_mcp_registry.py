"""Unit tests for core MCP server_registry: enums, MCPServer, MCPServerRegistry."""

from __future__ import annotations

import importlib.util
import sys
import types as _types
from datetime import datetime, timedelta
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
    """Load module via importlib and register in sys.modules so coverage tracks it."""
    full = _SRC / rel_path
    spec = importlib.util.spec_from_file_location(canonical, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[canonical] = mod
    spec.loader.exec_module(mod)
    return mod


# Stub the broken core/mcp __init__ chain before loading server_registry.py
_inject_stub("youtube_extension.core", str(_SRC / "youtube_extension/core"))
_inject_stub("youtube_extension.core.mcp", str(_SRC / "youtube_extension/core/mcp"))

_reg_mod = _load("youtube_extension/core/mcp/server_registry.py", "youtube_extension.core.mcp.server_registry")
MCPServer = _reg_mod.MCPServer
MCPServerRegistry = _reg_mod.MCPServerRegistry
ServerCapability = _reg_mod.ServerCapability
ServerStatus = _reg_mod.ServerStatus


# ===========================================================================
# ServerStatus enum
# ===========================================================================


class TestServerStatusEnum:
    def test_online_value(self):
        assert ServerStatus.ONLINE.value == "online"

    def test_offline_value(self):
        assert ServerStatus.OFFLINE.value == "offline"

    def test_maintenance_value(self):
        assert ServerStatus.MAINTENANCE.value == "maintenance"

    def test_error_value(self):
        assert ServerStatus.ERROR.value == "error"

    def test_has_four_members(self):
        assert len(ServerStatus) == 4


# ===========================================================================
# ServerCapability enum
# ===========================================================================


class TestServerCapabilityEnum:
    def test_context_management_value(self):
        assert ServerCapability.CONTEXT_MANAGEMENT.value == "context_management"

    def test_ai_inference_value(self):
        assert ServerCapability.AI_INFERENCE.value == "ai_inference"

    def test_data_processing_value(self):
        assert ServerCapability.DATA_PROCESSING.value == "data_processing"

    def test_file_operations_value(self):
        assert ServerCapability.FILE_OPERATIONS.value == "file_operations"

    def test_networking_value(self):
        assert ServerCapability.NETWORKING.value == "networking"

    def test_monitoring_value(self):
        assert ServerCapability.MONITORING.value == "monitoring"

    def test_has_six_members(self):
        assert len(ServerCapability) == 6


# ===========================================================================
# MCPServer model
# ===========================================================================


def _make_server(**kwargs):
    defaults = dict(id="s1", name="Test Server", endpoint="http://localhost:8080")
    defaults.update(kwargs)
    return MCPServer(**defaults)


class TestMCPServer:
    def test_required_fields(self):
        s = _make_server()
        assert s.id == "s1"
        assert s.name == "Test Server"
        assert s.endpoint == "http://localhost:8080"

    def test_capabilities_defaults_empty(self):
        assert _make_server().capabilities == []

    def test_status_defaults_offline(self):
        assert _make_server().status == ServerStatus.OFFLINE

    def test_port_default(self):
        assert _make_server().port == 8000

    def test_auth_token_default_none(self):
        assert _make_server().auth_token is None

    def test_version_default(self):
        assert _make_server().version == "1.0.0"

    def test_tags_default_empty(self):
        assert _make_server().tags == []

    def test_metadata_default_empty(self):
        assert _make_server().metadata == {}

    def test_invalid_endpoint_raises(self):
        with pytest.raises(Exception):
            _make_server(endpoint="not-a-url")

    def test_https_endpoint_accepted(self):
        s = _make_server(endpoint="https://api.example.com")
        assert "https" in s.endpoint

    def test_ws_endpoint_accepted(self):
        s = _make_server(endpoint="ws://ws.example.com/socket")
        assert "ws" in s.endpoint


class TestMCPServerGetFullEndpoint:
    def test_no_port_returns_endpoint(self):
        s = _make_server(endpoint="http://localhost", port=None)
        assert s.get_full_endpoint() == "http://localhost"

    def test_port_80_not_appended(self):
        s = _make_server(endpoint="http://localhost", port=80)
        assert ":80" not in s.get_full_endpoint()

    def test_port_443_not_appended(self):
        s = _make_server(endpoint="https://example.com", port=443)
        assert ":443" not in s.get_full_endpoint()

    def test_custom_port_appended(self):
        s = _make_server(endpoint="http://localhost", port=9000)
        assert ":9000" in s.get_full_endpoint()


class TestMCPServerHasCapability:
    def test_has_capability_when_in_list(self):
        s = _make_server(capabilities=[ServerCapability.AI_INFERENCE])
        assert s.has_capability(ServerCapability.AI_INFERENCE) is True

    def test_no_capability_when_not_in_list(self):
        s = _make_server(capabilities=[])
        assert s.has_capability(ServerCapability.AI_INFERENCE) is False

    def test_other_capability_not_returned(self):
        s = _make_server(capabilities=[ServerCapability.MONITORING])
        assert s.has_capability(ServerCapability.AI_INFERENCE) is False


class TestMCPServerIsHealthy:
    def test_offline_server_not_healthy(self):
        s = _make_server(status=ServerStatus.OFFLINE)
        assert s.is_healthy() is False

    def test_online_no_health_check_not_healthy(self):
        s = _make_server(status=ServerStatus.ONLINE, last_health_check=None)
        assert s.is_healthy() is False

    def test_online_recent_health_check_healthy(self):
        s = _make_server(
            status=ServerStatus.ONLINE,
            last_health_check=datetime.utcnow(),
            health_check_interval=30,
        )
        assert s.is_healthy() is True

    def test_online_stale_health_check_not_healthy(self):
        s = _make_server(
            status=ServerStatus.ONLINE,
            last_health_check=datetime.utcnow() - timedelta(hours=1),
            health_check_interval=30,
        )
        assert s.is_healthy() is False


class TestMCPServerUpdateStatus:
    def test_updates_status(self):
        s = _make_server(status=ServerStatus.OFFLINE)
        s.update_status(ServerStatus.ONLINE)
        assert s.status == ServerStatus.ONLINE

    def test_sets_last_health_check(self):
        before = datetime.utcnow()
        s = _make_server()
        s.update_status(ServerStatus.ONLINE)
        assert s.last_health_check >= before

    def test_sets_response_time(self):
        s = _make_server()
        s.update_status(ServerStatus.ONLINE, response_time=0.123)
        assert s.response_time == 0.123

    def test_response_time_none_not_set(self):
        s = _make_server(response_time=0.5)
        s.update_status(ServerStatus.ONLINE, response_time=None)
        assert s.response_time == 0.5  # unchanged


# ===========================================================================
# MCPServerRegistry
# ===========================================================================


@pytest.fixture
def registry(tmp_path):
    config_path = str(tmp_path / "config" / "mcp_servers.json")
    return MCPServerRegistry(config_path=config_path)


class TestMCPServerRegistryInit:
    def test_servers_empty(self, registry):
        assert registry.servers == {}

    def test_monitoring_inactive(self, registry):
        assert registry.monitoring_active is False

    def test_health_check_task_none(self, registry):
        assert registry.health_check_task is None


class TestMCPServerRegistryRegister:
    def test_register_adds_server(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [])
        assert "s1" in registry.servers

    def test_register_returns_server(self, registry):
        s = registry.register_server("s1", "S1", "http://localhost:8001", [])
        assert isinstance(s, MCPServer)

    def test_duplicate_id_raises(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [])
        with pytest.raises(ValueError):
            registry.register_server("s1", "S1 Dupe", "http://localhost:8002", [])

    def test_capability_indexed(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [ServerCapability.AI_INFERENCE])
        assert "s1" in registry.capability_index.get(ServerCapability.AI_INFERENCE, set())


class TestMCPServerRegistryUnregister:
    def test_unregister_removes_server(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [])
        result = registry.unregister_server("s1")
        assert result is True
        assert "s1" not in registry.servers

    def test_unregister_unknown_returns_false(self, registry):
        assert registry.unregister_server("nonexistent") is False

    def test_unregister_removes_from_capability_index(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [ServerCapability.MONITORING])
        registry.unregister_server("s1")
        assert "s1" not in registry.capability_index.get(ServerCapability.MONITORING, set())


class TestMCPServerRegistryGetServer:
    def test_returns_server(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [])
        assert registry.get_server("s1") is not None

    def test_returns_none_for_unknown(self, registry):
        assert registry.get_server("nonexistent") is None


class TestMCPServerRegistryFindByCapability:
    def test_finds_server_with_capability(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [ServerCapability.AI_INFERENCE])
        registry.servers["s1"].status = ServerStatus.ONLINE
        registry.servers["s1"].last_health_check = datetime.utcnow()
        results = registry.find_servers_by_capability(ServerCapability.AI_INFERENCE)
        assert len(results) >= 1

    def test_empty_for_capability_without_servers(self, registry):
        results = registry.find_servers_by_capability(ServerCapability.DATA_PROCESSING)
        assert results == []


class TestMCPServerRegistryGetAllServers:
    def test_returns_all_servers(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [])
        registry.register_server("s2", "S2", "http://localhost:8002", [])
        servers = registry.get_all_servers()
        assert len(servers) == 2

    def test_empty_when_no_servers(self, registry):
        assert registry.get_all_servers() == []


class TestMCPServerRegistryGetByStatus:
    def test_returns_matching_status_servers(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [])
        registry.servers["s1"].status = ServerStatus.ONLINE
        registry.register_server("s2", "S2", "http://localhost:8002", [])
        # s2 starts OFFLINE
        result = registry.get_servers_by_status(ServerStatus.ONLINE)
        assert len(result) == 1
        assert result[0].id == "s1"

    def test_empty_when_none_match(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8001", [])
        result = registry.get_servers_by_status(ServerStatus.MAINTENANCE)
        assert result == []
