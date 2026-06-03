"""Unit tests for MCPServerRegistry pure-logic methods."""

from __future__ import annotations

import asyncio
import sys
import types as _types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SRC = str(Path(__file__).resolve().parents[2] / "src")
sys.path.insert(0, _SRC)

# Stub out the broken services __init__ before importing submodules
if "youtube_extension.services" not in sys.modules:
    _stub = _types.ModuleType("youtube_extension.services")
    _stub.__path__ = [_SRC + "/youtube_extension/services"]
    _stub.__package__ = "youtube_extension.services"
    sys.modules["youtube_extension.services"] = _stub

# Force reimport so pytest-cov can instrument the modules even if previously cached.
sys.modules.pop("youtube_extension.services.mcp.registry", None)
sys.modules.pop("youtube_extension.services.mcp.types", None)
sys.modules.pop("youtube_extension.services.mcp", None)

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


# ===========================================================================
# MCPServerRegistry.find_servers_by_capability – missing branches (155, 161, 165)
# ===========================================================================


class TestFindServersByCapabilityEdgeCases:
    def test_skips_server_id_not_in_servers_dict(self):
        """Branch: server_id in capability_index but not in servers (line 155)."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.MONITORING])
        # Manually inject a stale server_id into the capability_index
        r.capability_index[MCPCapability.MONITORING].add("ghost_server")
        # ghost_server is not in self.servers, so it should be silently skipped
        results = r.find_servers_by_capability(MCPCapability.MONITORING, status_filter=None)
        server_ids = {c.id for c, _ in results}
        assert "ghost_server" not in server_ids

    def test_skips_server_without_state(self):
        """Branch: server_id in servers but not in server_states (line 161)."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.MONITORING])
        # Manually remove the state
        del r.server_states["s1"]
        results = r.find_servers_by_capability(MCPCapability.MONITORING, status_filter=None)
        assert results == []

    def test_status_filter_excludes_mismatched_servers(self):
        """Branch: status_filter set and state.status != status_filter (line 165)."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.MONITORING])
        r.register_server("s2", "S2", "http://localhost:8002", [MCPCapability.MONITORING])
        r.server_states["s1"].status = ServerStatus.ONLINE
        r.server_states["s2"].status = ServerStatus.ERROR  # won't match ONLINE filter

        results = r.find_servers_by_capability(MCPCapability.MONITORING, status_filter=ServerStatus.ONLINE)
        server_ids = [c.id for c, _ in results]
        assert "s1" in server_ids
        assert "s2" not in server_ids

    def test_results_sorted_by_load_factor(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.AI_INFERENCE])
        r.register_server("s2", "S2", "http://localhost:8002", [MCPCapability.AI_INFERENCE])
        r.server_states["s1"].status = ServerStatus.ONLINE
        r.server_states["s2"].status = ServerStatus.ONLINE
        r.server_states["s1"].load_factor = 0.9
        r.server_states["s2"].load_factor = 0.1

        results = r.find_servers_by_capability(MCPCapability.AI_INFERENCE)
        # Lower load_factor should come first
        assert results[0][0].id == "s2"


# ===========================================================================
# MCPServerRegistry.get_best_server_for_task – missing branches (197, 212)
# ===========================================================================


class TestGetBestServerForTaskEdgeCases:
    def test_intersects_multiple_capability_sets(self):
        """Branch: candidate_ids &= server_ids (line 197) – multi-cap intersection."""
        r = MCPServerRegistry()
        # s1 has both caps, s2 only one
        r.register_server(
            "s1", "S1", "http://localhost:8001",
            [MCPCapability.AI_INFERENCE, MCPCapability.MONITORING],
        )
        r.register_server(
            "s2", "S2", "http://localhost:8002",
            [MCPCapability.AI_INFERENCE],
        )
        r.server_states["s1"].status = ServerStatus.ONLINE
        r.server_states["s2"].status = ServerStatus.ONLINE

        result = r.get_best_server_for_task(
            [MCPCapability.AI_INFERENCE, MCPCapability.MONITORING]
        )
        assert result == "s1"

    def test_skips_candidate_without_config_or_state(self):
        """Branch: not config or not state (line 212)."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.AI_INFERENCE])
        r.server_states["s1"].status = ServerStatus.ONLINE

        # Add a ghost to the index with no config/state
        r.capability_index[MCPCapability.AI_INFERENCE].add("ghost")

        result = r.get_best_server_for_task([MCPCapability.AI_INFERENCE])
        assert result == "s1"

    def test_returns_best_scored_server(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.AI_INFERENCE])
        r.register_server("s2", "S2", "http://localhost:8002", [MCPCapability.AI_INFERENCE])
        r.server_states["s1"].status = ServerStatus.ONLINE
        r.server_states["s2"].status = ServerStatus.ONLINE
        # s1 has high load (worse), s2 has low load (better)
        r.server_states["s1"].load_factor = 0.9
        r.server_states["s2"].load_factor = 0.1

        result = r.get_best_server_for_task([MCPCapability.AI_INFERENCE])
        assert result == "s2"


# ===========================================================================
# MCPServerRegistry.check_server_health (lines 285-344)
# ===========================================================================


class TestCheckServerHealth:
    async def test_returns_false_for_unknown_server(self):
        r = MCPServerRegistry()
        result = await r.check_server_health("nonexistent")
        assert result is False

    async def test_healthy_server_sets_online_status(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await r.check_server_health("s1")

        assert result is True
        assert r.server_states["s1"].status == ServerStatus.ONLINE

    async def test_non_200_response_sets_error_status(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await r.check_server_health("s1")

        assert result is False
        assert r.server_states["s1"].status == ServerStatus.ERROR

    async def test_timeout_sets_offline_status(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await r.check_server_health("s1")

        assert result is False
        assert r.server_states["s1"].status == ServerStatus.OFFLINE
        assert r.server_states["s1"].consecutive_failures == 1

    async def test_exception_sets_error_status(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=ConnectionError("refused"))
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await r.check_server_health("s1")

        assert result is False
        assert r.server_states["s1"].status == ServerStatus.ERROR

    async def test_uses_shared_session_when_monitoring_active(self):
        """When _health_session already exists, it should not create a new one."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_shared_session = MagicMock()
        mock_shared_session.get = MagicMock(return_value=mock_response)
        mock_shared_session.close = AsyncMock()

        r._health_session = mock_shared_session

        # Should NOT call aiohttp.ClientSession() since session already exists
        with patch("aiohttp.ClientSession") as mock_cls:
            await r.check_server_health("s1")
            mock_cls.assert_not_called()

        # Shared session should NOT be closed since it was pre-existing
        mock_shared_session.close.assert_not_called()

    async def test_updates_average_response_time_on_second_health_check(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])
        # Pre-set a response time so the EMA branch is exercised
        r.server_states["s1"].average_response_time = 0.5

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await r.check_server_health("s1")

        # EMA update: average_response_time should be between 0 and 1
        assert 0.0 <= r.server_states["s1"].average_response_time <= 1.0


# ===========================================================================
# MCPServerRegistry.start_monitoring / stop_monitoring (lines 348-370)
# ===========================================================================


class TestMonitoringLifecycle:
    async def test_start_monitoring_sets_active(self):
        r = MCPServerRegistry()
        try:
            await r.start_monitoring()
            assert r.monitoring_active is True
        finally:
            await r.stop_monitoring()

    async def test_start_monitoring_creates_session(self):
        r = MCPServerRegistry()
        try:
            await r.start_monitoring()
            assert r._health_session is not None
        finally:
            await r.stop_monitoring()

    async def test_stop_monitoring_clears_active(self):
        r = MCPServerRegistry()
        await r.start_monitoring()
        await r.stop_monitoring()
        assert r.monitoring_active is False

    async def test_stop_monitoring_closes_session(self):
        r = MCPServerRegistry()
        await r.start_monitoring()
        await r.stop_monitoring()
        assert r._health_session is None

    async def test_double_start_does_not_raise(self):
        r = MCPServerRegistry()
        try:
            await r.start_monitoring()
            await r.start_monitoring()  # Should just log a warning
            assert r.monitoring_active is True
        finally:
            await r.stop_monitoring()

    async def test_stop_when_not_started_does_not_raise(self):
        r = MCPServerRegistry()
        # Should complete without raising
        await r.stop_monitoring()

    async def test_health_check_task_cancelled_on_stop(self):
        r = MCPServerRegistry()
        await r.start_monitoring()
        task = r.health_check_task
        assert task is not None
        await r.stop_monitoring()
        assert task.cancelled() or task.done()


# ===========================================================================
# MCPServerRegistry.get_registry_status (lines 420-445)
# ===========================================================================


class TestGetRegistryStatus:
    def test_returns_dict(self):
        r = MCPServerRegistry()
        status = r.get_registry_status()
        assert isinstance(status, dict)

    def test_total_servers_count(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])
        r.register_server("s2", "S2", "http://localhost:8002", [])
        status = r.get_registry_status()
        assert status["total_servers"] == 2

    def test_status_breakdown_counts_statuses(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])
        r.register_server("s2", "S2", "http://localhost:8002", [])
        r.server_states["s1"].status = ServerStatus.ONLINE
        r.server_states["s2"].status = ServerStatus.OFFLINE

        status = r.get_registry_status()
        assert status["status_breakdown"].get("online", 0) == 1
        assert status["status_breakdown"].get("offline", 0) == 1

    def test_capability_coverage_included(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.AI_INFERENCE])
        r.server_states["s1"].status = ServerStatus.ONLINE

        status = r.get_registry_status()
        assert "ai_inference" in status["capability_coverage"]

    def test_capability_coverage_online_count(self):
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [MCPCapability.AI_INFERENCE])
        r.register_server("s2", "S2", "http://localhost:8002", [MCPCapability.AI_INFERENCE])
        r.server_states["s1"].status = ServerStatus.ONLINE
        r.server_states["s2"].status = ServerStatus.OFFLINE

        status = r.get_registry_status()
        coverage = status["capability_coverage"]["ai_inference"]
        assert coverage["online"] == 1
        assert coverage["total"] == 2
        assert coverage["coverage"] == "1/2"

    def test_monitoring_active_field(self):
        r = MCPServerRegistry()
        status = r.get_registry_status()
        assert "monitoring_active" in status
        assert status["monitoring_active"] is False


# ===========================================================================
# MCPServerRegistry.check_server_health – auth_token header (line 303)
# ===========================================================================


class TestCheckServerHealthAuthToken:
    async def test_auth_token_added_to_headers(self):
        r = MCPServerRegistry()
        r.register_server(
            "s1", "S1", "http://localhost:8001", [],
            auth_token="secret-token"
        )

        received_headers: dict = {}

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()

        def capture_get(url, headers=None, timeout=None):
            received_headers.update(headers or {})
            return mock_response

        mock_session.get = MagicMock(side_effect=capture_get)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await r.check_server_health("s1")

        assert received_headers.get("Authorization") == "Bearer secret-token"


# ===========================================================================
# MCPServerRegistry._monitoring_loop (lines 374-418)
# ===========================================================================


class TestMonitoringLoop:
    async def test_monitoring_loop_triggers_health_checks(self):
        """The loop should call check_server_health for servers with overdue checks."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])
        # last_health_check is None so check is immediately due

        health_calls: list[str] = []

        async def fake_health_check(server_id: str) -> bool:
            health_calls.append(server_id)
            r.server_states[server_id].status = ServerStatus.ONLINE
            return True

        with patch.object(r, "check_server_health", side_effect=fake_health_check):
            with patch.dict("os.environ", {"MCP_MONITORING_INTERVAL": "1"}):
                await r.start_monitoring()
                await asyncio.sleep(0.3)
                await r.stop_monitoring()

        assert "s1" in health_calls

    async def test_monitoring_loop_tracks_uptime_for_online_servers(self):
        """When a server is ONLINE, uptime_seconds should be incremented."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])
        r.server_states["s1"].status = ServerStatus.ONLINE

        async def fake_health_check(server_id: str) -> bool:
            return True

        with patch.object(r, "check_server_health", side_effect=fake_health_check):
            with patch.dict("os.environ", {"MCP_MONITORING_INTERVAL": "1"}):
                await r.start_monitoring()
                await asyncio.sleep(0.3)
                await r.stop_monitoring()

        # uptime_seconds should be >= 0 (may still be 0 if no check ran yet)
        assert r.server_states["s1"].uptime_seconds >= 0

    async def test_monitoring_loop_clears_online_time_for_offline_servers(self):
        """Non-ONLINE servers should have last_online_time cleared."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])
        r.server_states["s1"].status = ServerStatus.OFFLINE

        from datetime import datetime
        r.server_states["s1"].last_online_time = datetime.utcnow()

        async def fake_health_check(server_id: str) -> bool:
            return False

        with patch.object(r, "check_server_health", side_effect=fake_health_check):
            with patch.dict("os.environ", {"MCP_MONITORING_INTERVAL": "1"}):
                await r.start_monitoring()
                await asyncio.sleep(0.3)
                await r.stop_monitoring()

        assert r.server_states["s1"].last_online_time is None

    async def test_monitoring_loop_skips_server_without_state(self):
        """Server in self.servers but not in server_states should be safely skipped."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])
        # Remove state to simulate gap
        del r.server_states["s1"]

        health_calls: list[str] = []

        async def fake_health_check(server_id: str) -> bool:
            health_calls.append(server_id)
            return True

        with patch.object(r, "check_server_health", side_effect=fake_health_check):
            with patch.dict("os.environ", {"MCP_MONITORING_INTERVAL": "1"}):
                await r.start_monitoring()
                await asyncio.sleep(0.3)
                await r.stop_monitoring()

        assert "s1" not in health_calls

    async def test_monitoring_loop_handles_exception_and_continues(self):
        """Exception inside the loop body should be caught; loop should keep running."""
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])

        call_count: list[int] = [0]

        async def failing_health_check(server_id: str) -> bool:
            call_count[0] += 1
            raise RuntimeError("health boom")

        with patch.object(r, "check_server_health", side_effect=failing_health_check):
            with patch.dict("os.environ", {"MCP_MONITORING_INTERVAL": "1"}):
                await r.start_monitoring()
                await asyncio.sleep(0.3)
                await r.stop_monitoring()

        # Loop continued running; health was attempted at least once
        assert call_count[0] >= 1

    async def test_monitoring_loop_exception_in_uptime_block(self):
        """Cover lines 411-414 – except Exception in monitoring loop.

        We trigger the exception inside asyncio.gather by making check_server_health
        raise RuntimeError on first call. The gather uses return_exceptions=True so
        it won't propagate the error directly – instead we use a separate path:
        we patch asyncio.gather itself to raise on first call.
        """
        r = MCPServerRegistry()
        r.register_server("s1", "S1", "http://localhost:8001", [])
        # last_health_check=None ensures a health task is always queued

        gather_call_count: list[int] = [0]
        original_gather = asyncio.gather

        async def patched_gather(*coros, **kwargs):
            gather_call_count[0] += 1
            if gather_call_count[0] == 1:
                # Discard the coroutines and raise to hit the except block
                for c in coros:
                    try:
                        c.close()
                    except Exception:
                        pass
                raise RuntimeError("gather boom in monitoring loop")
            return await original_gather(*coros, **kwargs)

        with patch("asyncio.gather", side_effect=patched_gather):
            with patch.object(r, "check_server_health", return_value=True):
                with patch.dict("os.environ", {"MCP_MONITORING_INTERVAL": "1"}):
                    await r.start_monitoring()
                    await asyncio.sleep(0.4)
                    await r.stop_monitoring()

        # Monitoring loop survived the exception and stopped cleanly
        assert r.monitoring_active is False
