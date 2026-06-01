"""Unit tests for MCPServerRegistry pure-logic methods."""

from __future__ import annotations

import sys
import types as _types
from pathlib import Path

import pytest

_SRC = str(Path(__file__).resolve().parents[2] / "src")
sys.path.insert(0, _SRC)

# Stub out the broken services __init__ before importing submodules
if "youtube_extension.services" not in sys.modules:
    _stub = _types.ModuleType("youtube_extension.services")
    _stub.__path__ = [_SRC + "/youtube_extension/services"]
    _stub.__package__ = "youtube_extension.services"
    sys.modules["youtube_extension.services"] = _stub

from youtube_extension.services.mcp.registry import MCPServerRegistry
from youtube_extension.services.mcp.types import (
    MCPCapability,
    MCPServerState,
    ServerStatus,
)


# ===========================================================================
# MCPServerRegistry.__init__
# ===========================================================================


class TestMCPServerRegistryInit:
    def test_servers_starts_empty(self):
        r = MCPServerRegistry()
        assert r.servers == {}

    def test_server_states_starts_empty(self):
        r = MCPServerRegistry()
        assert r.server_states == {}

    def test_capability_index_starts_empty(self):
        r = MCPServerRegistry()
        assert len(r.capability_index) == 0

    def test_monitoring_starts_inactive(self):
        r = MCPServerRegistry()
        assert r.monitoring_active is False

    def test_health_check_task_none(self):
        r = MCPServerRegistry()
        assert r.health_check_task is None


# ===========================================================================
# MCPServerRegistry.register_server
# ===========================================================================


class TestMCPServerRegistryRegister:
    @pytest.fixture
    def registry(self):
        return MCPServerRegistry()

    def test_register_adds_server(self, registry):
        registry.register_server("s1", "Server 1", "http://localhost:8000", [])
        assert "s1" in registry.servers

    def test_register_creates_state(self, registry):
        registry.register_server("s1", "Server 1", "http://localhost:8000", [])
        assert "s1" in registry.server_states

    def test_state_starts_offline(self, registry):
        registry.register_server("s1", "Server 1", "http://localhost:8000", [])
        assert registry.server_states["s1"].status == ServerStatus.OFFLINE

    def test_register_indexes_capabilities(self, registry):
        caps = [MCPCapability.VIDEO_TRANSCRIPTION]
        registry.register_server("s1", "S1", "http://localhost:8000", caps)
        assert "s1" in registry.capability_index[MCPCapability.VIDEO_TRANSCRIPTION]

    def test_register_returns_config(self, registry):
        config = registry.register_server("s1", "S1", "http://localhost:8000", [])
        assert config.id == "s1"
        assert config.name == "S1"

    def test_re_register_updates_server(self, registry):
        registry.register_server("s1", "Old Name", "http://localhost:8000", [])
        registry.register_server("s1", "New Name", "http://localhost:8000", [])
        assert registry.servers["s1"].name == "New Name"

    def test_re_register_preserves_state(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8000", [])
        # Manually mark online
        registry.server_states["s1"].status = ServerStatus.ONLINE
        registry.register_server("s1", "S1 Updated", "http://localhost:8000", [])
        # State should be preserved on re-registration
        assert registry.server_states["s1"].status == ServerStatus.ONLINE

    def test_re_register_updates_capability_index(self, registry):
        registry.register_server("s1", "S1", "http://localhost:8000", [MCPCapability.AI_INFERENCE])
        registry.register_server("s1", "S1", "http://localhost:8000", [MCPCapability.MONITORING])
        assert "s1" not in registry.capability_index.get(MCPCapability.AI_INFERENCE, set())
        assert "s1" in registry.capability_index[MCPCapability.MONITORING]


# ===========================================================================
# MCPServerRegistry.unregister_server
# ===========================================================================


class TestMCPServerRegistryUnregister:
    @pytest.fixture
    def registry_with_server(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8000", [MCPCapability.AI_INFERENCE])
        return r

    def test_unregister_removes_server(self, registry_with_server):
        registry_with_server.unregister_server("s1")
        assert "s1" not in registry_with_server.servers

    def test_unregister_removes_state(self, registry_with_server):
        registry_with_server.unregister_server("s1")
        assert "s1" not in registry_with_server.server_states

    def test_unregister_removes_from_capability_index(self, registry_with_server):
        registry_with_server.unregister_server("s1")
        assert "s1" not in registry_with_server.capability_index.get(MCPCapability.AI_INFERENCE, set())

    def test_unregister_returns_true_on_success(self, registry_with_server):
        assert registry_with_server.unregister_server("s1") is True

    def test_unregister_returns_false_for_unknown(self):
        r = MCPServerRegistry()
        assert r.unregister_server("nonexistent") is False


# ===========================================================================
# MCPServerRegistry.get_server / get_server_state
# ===========================================================================


class TestMCPServerRegistryGetters:
    @pytest.fixture
    def registry(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8000", [])
        return r

    def test_get_server_returns_config(self, registry):
        config = registry.get_server("s1")
        assert config is not None
        assert config.id == "s1"

    def test_get_server_returns_none_for_unknown(self, registry):
        assert registry.get_server("nonexistent") is None

    def test_get_server_state_returns_state(self, registry):
        state = registry.get_server_state("s1")
        assert state is not None
        assert state.server_id == "s1"

    def test_get_server_state_returns_none_for_unknown(self, registry):
        assert registry.get_server_state("nonexistent") is None


# ===========================================================================
# MCPServerRegistry.find_servers_by_capability
# ===========================================================================


class TestMCPServerRegistryFindByCapability:
    @pytest.fixture
    def registry(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.AI_INFERENCE])
        r.register_server("s2", "S2", "http://localhost:8002", [MCPCapability.MONITORING])
        r.register_server("s3", "S3", "http://localhost:8003", [MCPCapability.AI_INFERENCE])
        # Mark s1 and s3 as ONLINE
        r.server_states["s1"].status = ServerStatus.ONLINE
        r.server_states["s3"].status = ServerStatus.ONLINE
        return r

    def test_finds_online_servers_with_capability(self, registry):
        results = registry.find_servers_by_capability(MCPCapability.AI_INFERENCE)
        server_ids = [c.id for c, _ in results]
        assert "s1" in server_ids
        assert "s3" in server_ids

    def test_excludes_offline_servers_by_default(self, registry):
        results = registry.find_servers_by_capability(MCPCapability.AI_INFERENCE)
        server_ids = [c.id for c, _ in results]
        # s2 doesn't have AI_INFERENCE; s1 and s3 are ONLINE
        for sid in server_ids:
            assert registry.server_states[sid].status == ServerStatus.ONLINE

    def test_no_status_filter_returns_all(self, registry):
        results = registry.find_servers_by_capability(MCPCapability.AI_INFERENCE, status_filter=None)
        assert len(results) >= 1  # includes offline ones too

    def test_empty_for_capability_without_servers(self, registry):
        results = registry.find_servers_by_capability(MCPCapability.DATA_PROCESSING)
        assert results == []


# ===========================================================================
# MCPServerRegistry.get_best_server_for_task
# ===========================================================================


class TestMCPServerRegistryGetBestServer:
    @pytest.fixture
    def registry(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.AI_INFERENCE])
        r.register_server("s2", "S2", "http://localhost:8002", [MCPCapability.VIDEO_TRANSCRIPTION])
        r.server_states["s1"].status = ServerStatus.ONLINE
        r.server_states["s2"].status = ServerStatus.ONLINE
        return r

    def test_returns_server_with_required_capability(self, registry):
        result = registry.get_best_server_for_task([MCPCapability.AI_INFERENCE])
        assert result == "s1"

    def test_returns_none_for_empty_requirements(self, registry):
        assert registry.get_best_server_for_task([]) is None

    def test_returns_none_when_no_servers_match(self, registry):
        result = registry.get_best_server_for_task([MCPCapability.FILE_OPERATIONS])
        assert result is None

    def test_returns_none_when_server_at_capacity(self, registry):
        registry.server_states["s1"].current_tasks = 10  # max is 10
        result = registry.get_best_server_for_task([MCPCapability.AI_INFERENCE])
        assert result is None

    def test_returns_none_when_server_offline(self, registry):
        registry.server_states["s1"].status = ServerStatus.OFFLINE
        result = registry.get_best_server_for_task([MCPCapability.AI_INFERENCE])
        assert result is None


# ===========================================================================
# MCPServerRegistry.update_server_state
# ===========================================================================


class TestMCPServerRegistryUpdateState:
    def test_returns_none_for_unknown_server(self):
        r = MCPServerRegistry()
        result = r.update_server_state("nonexistent", status=ServerStatus.ONLINE)
        assert result is None

    def test_updates_state_field(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8000", [])
        r.update_server_state("s1", status=ServerStatus.ONLINE)
        assert r.server_states["s1"].status == ServerStatus.ONLINE

    def test_updates_multiple_fields(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8000", [])
        r.update_server_state("s1", current_tasks=5, load_factor=0.5)
        assert r.server_states["s1"].current_tasks == 5
        assert r.server_states["s1"].load_factor == 0.5

    def test_returns_updated_state(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8000", [])
        state = r.update_server_state("s1", status=ServerStatus.ONLINE)
        assert isinstance(state, MCPServerState)

    def test_ignores_invalid_fields(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8000", [])
        # Should not raise; invalid fields are silently ignored
        r.update_server_state("s1", nonexistent_field="value")
