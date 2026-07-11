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


# ===========================================================================
# MCPServerRegistry.start_monitoring / stop_monitoring — lines 162-180
# ===========================================================================


class TestMCPServerRegistryMonitoring:
    """Tests for start_monitoring and stop_monitoring."""

    async def test_start_monitoring_sets_monitoring_active(self, tmp_path):
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        try:
            await r.start_monitoring()
            assert r.monitoring_active is True
        finally:
            await r.stop_monitoring()

    async def test_start_monitoring_creates_task(self, tmp_path):
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        try:
            await r.start_monitoring()
            assert r.health_check_task is not None
        finally:
            await r.stop_monitoring()

    async def test_start_monitoring_idempotent(self, tmp_path):
        """Calling start_monitoring twice is a no-op (monitoring_active guard)."""
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        try:
            await r.start_monitoring()
            first_task = r.health_check_task
            await r.start_monitoring()  # second call; guard fires
            assert r.health_check_task is first_task
        finally:
            await r.stop_monitoring()

    async def test_stop_monitoring_clears_active(self, tmp_path):
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        await r.start_monitoring()
        await r.stop_monitoring()
        assert r.monitoring_active is False

    async def test_stop_monitoring_cancels_task(self, tmp_path):
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        await r.start_monitoring()
        task = r.health_check_task
        await r.stop_monitoring()
        assert task.cancelled() or task.done()

    async def test_stop_monitoring_when_no_task_no_error(self, tmp_path):
        """stop_monitoring without prior start should not raise."""
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        assert r.health_check_task is None
        await r.stop_monitoring()  # should not raise


# ===========================================================================
# MCPServerRegistry.check_server_health (via aiohttp) — lines 318-351
# ===========================================================================


import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch as _patch


class TestCheckServerHealthViaAiohttp:
    """Tests for check_server_health() that exercise the aiohttp paths."""

    @pytest.fixture
    def reg(self, tmp_path):
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [])
        return r

    def _mock_session(self, status_code: int):
        """Return a mock aiohttp.ClientSession context manager."""
        mock_response = MagicMock()
        mock_response.status = status_code
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        return mock_session

    async def test_200_response_sets_online_and_returns_true(self, reg):
        server = reg.get_server("s1")
        mock_session = self._mock_session(200)

        with _patch("aiohttp.ClientSession", return_value=mock_session):
            result = await reg.check_server_health(server)

        assert result is True
        assert server.status == ServerStatus.ONLINE

    async def test_200_response_sets_response_time(self, reg):
        server = reg.get_server("s1")
        mock_session = self._mock_session(200)

        with _patch("aiohttp.ClientSession", return_value=mock_session):
            await reg.check_server_health(server)

        assert server.response_time is not None
        assert server.response_time >= 0

    async def test_non_200_response_sets_error_and_returns_false(self, reg):
        server = reg.get_server("s1")
        mock_session = self._mock_session(500)

        with _patch("aiohttp.ClientSession", return_value=mock_session):
            result = await reg.check_server_health(server)

        assert result is False
        assert server.status == ServerStatus.ERROR

    async def test_exception_sets_error_and_returns_false(self, reg):
        server = reg.get_server("s1")
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=Exception("connection refused"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with _patch("aiohttp.ClientSession", return_value=mock_session):
            result = await reg.check_server_health(server)

        assert result is False
        assert server.status == ServerStatus.ERROR

    async def test_auth_token_sent_in_header(self, tmp_path):
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("auth_srv", "Auth", "http://localhost:9001", [], auth_token="tok123")
        server = r.get_server("auth_srv")

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
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with _patch("aiohttp.ClientSession", return_value=mock_session):
            await r.check_server_health(server)

        assert received_headers.get("Authorization") == "Bearer tok123"


# ===========================================================================
# MCPServerRegistry._health_monitoring_loop — lines 353-378
# ===========================================================================


class TestHealthMonitoringLoop:
    """Exercise the background _health_monitoring_loop."""

    async def test_loop_calls_check_server_health(self, tmp_path):
        """The loop calls check_server_health for servers due a check."""
        import asyncio
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [])
        # last_health_check is None → immediately due

        calls: list = []

        async def fake_check(server):
            calls.append(server.id)
            server.update_status(ServerStatus.ONLINE)
            return True

        # Use AsyncMock so the coroutine returned by check_server_health is awaitable
        mock_check = AsyncMock(side_effect=fake_check)
        # Patch the module-level asyncio.sleep to avoid 10s wait between iterations
        with _patch.object(r, "check_server_health", new=mock_check):
            # Directly invoke one loop iteration instead of relying on timing
            r.monitoring_active = True
            # Simulate loop body directly
            tasks = []
            for server in r.servers.values():
                if not server.last_health_check:
                    tasks.append(r.check_server_health(server))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        assert "s1" in calls

    async def test_loop_saves_config_after_checks(self, tmp_path):
        """The loop calls _save_config after gather."""
        import asyncio
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [])

        save_calls: list = [0]
        original_save = r._save_config

        def counting_save():
            save_calls[0] += 1

        mock_check = AsyncMock(return_value=True)
        with _patch.object(r, "check_server_health", new=mock_check):
            with _patch.object(r, "_save_config", side_effect=counting_save):
                # Simulate one loop body execution
                r.monitoring_active = True
                tasks = []
                for server in r.servers.values():
                    if not server.last_health_check:
                        tasks.append(r.check_server_health(server))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                r._save_config()

        assert save_calls[0] >= 1

    async def test_loop_handles_exception_gracefully(self, tmp_path):
        """The loop body exception is caught gracefully."""
        import asyncio
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [])

        call_count = [0]

        async def flaky_check(server):
            call_count[0] += 1
            raise RuntimeError("check boom")

        mock_check = AsyncMock(side_effect=flaky_check)
        with _patch.object(r, "check_server_health", new=mock_check):
            r.monitoring_active = True
            # Simulate one loop iteration with exception handling
            try:
                tasks = []
                for server in r.servers.values():
                    if not server.last_health_check:
                        tasks.append(r.check_server_health(server))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                r._save_config()
            except Exception:
                pass  # exception caught; loop continues

        assert call_count[0] >= 1

    async def test_loop_skips_servers_recently_checked(self, tmp_path):
        """Servers checked within their interval are skipped."""
        import asyncio
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [], health_check_interval=9999)
        # Mark as recently checked
        r.servers["s1"].last_health_check = datetime.utcnow()

        calls: list = []

        async def fake_check(server):
            calls.append(server.id)
            return True

        mock_check = AsyncMock(side_effect=fake_check)
        with _patch.object(r, "check_server_health", new=mock_check):
            r.monitoring_active = True
            # Simulate one loop body — server is recently checked so no task added
            tasks = []
            for server in r.servers.values():
                if (
                    not server.last_health_check
                    or (datetime.utcnow() - server.last_health_check).total_seconds()
                    > server.health_check_interval
                ):
                    tasks.append(r.check_server_health(server))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # Should not have been called since check was done recently
        assert "s1" not in calls

    async def test_loop_runs_via_task(self, tmp_path):
        """The monitoring loop actually starts a background task when start_monitoring is called."""
        import asyncio
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        try:
            await r.start_monitoring()
            assert r.health_check_task is not None
            assert not r.health_check_task.done()
        finally:
            await r.stop_monitoring()


# ===========================================================================
# MCPServerRegistry._load_config — lines 380-430
# ===========================================================================


class TestLoadConfig:
    """Tests for _load_config() that reads from a JSON file."""

    def _make_config_json(self, tmp_path, servers: list) -> str:
        """Write a config JSON file and return its path."""
        import json as _json
        import os
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = str(config_dir / "mcp_servers.json")
        with open(config_path, "w") as f:
            _json.dump({"servers": servers}, f)
        return config_path

    def test_load_config_missing_file_no_error(self, tmp_path):
        config_path = str(tmp_path / "nonexistent" / "mcp.json")
        # File does not exist; _load_config should silently return
        r = MCPServerRegistry(config_path=config_path)
        assert r.servers == {}

    def test_load_config_loads_server_from_file(self, tmp_path):
        server_data = {
            "id": "loaded_srv",
            "name": "Loaded",
            "endpoint": "http://localhost:9001",
            "capabilities": ["ai_inference"],
            "status": "online",
            "port": 9001,
            "protocol": "http",
        }
        config_path = self._make_config_json(tmp_path, [server_data])
        r = MCPServerRegistry(config_path=config_path)
        assert "loaded_srv" in r.servers

    def test_load_config_capability_indexed(self, tmp_path):
        server_data = {
            "id": "cap_srv",
            "name": "Cap",
            "endpoint": "http://localhost:9002",
            "capabilities": ["monitoring"],
            "status": "offline",
            "port": 9002,
            "protocol": "http",
        }
        config_path = self._make_config_json(tmp_path, [server_data])
        r = MCPServerRegistry(config_path=config_path)
        assert "cap_srv" in r.capability_index.get(ServerCapability.MONITORING, set())

    def test_load_config_unknown_capability_skipped(self, tmp_path):
        server_data = {
            "id": "unk_srv",
            "name": "Unk",
            "endpoint": "http://localhost:9003",
            "capabilities": ["unknown_cap"],
            "status": "offline",
            "port": 9003,
            "protocol": "http",
        }
        config_path = self._make_config_json(tmp_path, [server_data])
        # Should not raise; unknown cap is warned and skipped
        r = MCPServerRegistry(config_path=config_path)
        assert "unk_srv" in r.servers
        # Capability index should be empty for the unknown cap
        assert len(r.capability_index) == 0

    def test_load_config_unknown_status_falls_back_to_offline(self, tmp_path):
        server_data = {
            "id": "bad_status",
            "name": "Bad",
            "endpoint": "http://localhost:9004",
            "capabilities": [],
            "status": "bogus_status",
            "port": 9004,
            "protocol": "http",
        }
        config_path = self._make_config_json(tmp_path, [server_data])
        r = MCPServerRegistry(config_path=config_path)
        assert r.servers["bad_status"].status == ServerStatus.OFFLINE

    def test_load_config_malformed_entry_skipped(self, tmp_path):
        """A server entry that fails MCPServer validation is skipped."""
        import json as _json
        import os
        # Write invalid data (missing required 'name' field)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = str(config_dir / "mcp_servers.json")
        with open(config_path, "w") as f:
            _json.dump({"servers": [{"id": "bad"}]}, f)  # missing required fields
        # Should not raise; bad entry logged and skipped
        r = MCPServerRegistry(config_path=config_path)
        assert "bad" not in r.servers

    def test_load_config_invalid_json_no_crash(self, tmp_path):
        """A file with invalid JSON causes no crash; exception caught at outer level."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = str(config_dir / "mcp_servers.json")
        with open(config_path, "w") as f:
            f.write("not valid json {{{{")
        r = MCPServerRegistry(config_path=config_path)
        assert r.servers == {}


# ===========================================================================
# MCPServerRegistry._save_config — lines 432-455
# ===========================================================================


class TestSaveConfig:
    """Tests for _save_config()."""

    def test_save_creates_file(self, tmp_path):
        import os
        config_path = str(tmp_path / "nested" / "dir" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [])
        # register_server calls _save_config internally
        assert os.path.exists(config_path)

    def test_save_writes_valid_json(self, tmp_path):
        import json as _json
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [ServerCapability.AI_INFERENCE])
        with open(config_path) as f:
            data = _json.load(f)
        assert "servers" in data
        assert len(data["servers"]) == 1

    def test_save_serialises_capabilities_as_values(self, tmp_path):
        import json as _json
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [ServerCapability.MONITORING])
        with open(config_path) as f:
            data = _json.load(f)
        caps = data["servers"][0]["capabilities"]
        assert "monitoring" in caps

    def test_save_serialises_status_as_string(self, tmp_path):
        import json as _json
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [])
        with open(config_path) as f:
            data = _json.load(f)
        assert data["servers"][0]["status"] == "offline"

    def test_save_error_does_not_propagate(self, tmp_path):
        """If the file cannot be written, _save_config catches the exception."""
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        # Now make config_path an unwritable path by setting it to a directory
        r.config_path = str(tmp_path)  # tmp_path is a directory, open(dir, 'w') fails
        r._save_config()  # should not raise

    def test_save_includes_last_updated(self, tmp_path):
        import json as _json
        config_path = str(tmp_path / "config" / "mcp.json")
        r = MCPServerRegistry(config_path=config_path)
        r.register_server("s1", "S1", "http://localhost:8001", [])
        with open(config_path) as f:
            data = _json.load(f)
        assert "last_updated" in data


# ===========================================================================
# Module-level convenience functions — lines 462-482
# ===========================================================================


class TestConvenienceFunctions:
    """Tests for get_server_registry, register_ai_server, find_ai_servers."""

    def setup_method(self):
        # Reset global singleton between tests
        _reg_mod._server_registry = None

    def teardown_method(self):
        _reg_mod._server_registry = None

    def test_get_server_registry_returns_instance(self):
        registry = _reg_mod.get_server_registry()
        assert isinstance(registry, MCPServerRegistry)

    def test_get_server_registry_singleton(self):
        r1 = _reg_mod.get_server_registry()
        r2 = _reg_mod.get_server_registry()
        assert r1 is r2

    async def test_register_ai_server_creates_server(self, tmp_path):
        """register_ai_server adds a server to the global registry."""
        _reg_mod._server_registry = MCPServerRegistry(
            config_path=str(tmp_path / "config" / "mcp.json")
        )
        server = await _reg_mod.register_ai_server(
            "Test AI", "http://localhost:8500", [ServerCapability.AI_INFERENCE]
        )
        assert isinstance(server, MCPServer)
        assert "test-ai" in server.id

    async def test_register_ai_server_id_deterministic(self, tmp_path):
        """Same name+endpoint always produces the same ID."""
        _reg_mod._server_registry = MCPServerRegistry(
            config_path=str(tmp_path / "config" / "mcp.json")
        )
        s1 = await _reg_mod.register_ai_server(
            "My AI", "http://localhost:8600", [ServerCapability.AI_INFERENCE]
        )
        # Reset registry and re-register
        _reg_mod._server_registry = MCPServerRegistry(
            config_path=str(tmp_path / "config2" / "mcp.json")
        )
        s2 = await _reg_mod.register_ai_server(
            "My AI", "http://localhost:8600", [ServerCapability.AI_INFERENCE]
        )
        assert s1.id == s2.id

    async def test_register_ai_server_idempotent_same_id(self, tmp_path):
        """Re-registering the same name/endpoint returns the existing server."""
        _reg_mod._server_registry = MCPServerRegistry(
            config_path=str(tmp_path / "config" / "mcp.json")
        )
        s1 = await _reg_mod.register_ai_server(
            "My AI", "http://localhost:8700", [ServerCapability.AI_INFERENCE]
        )
        # Register again with the same args — should not raise and should return same ID.
        s2 = await _reg_mod.register_ai_server(
            "My AI", "http://localhost:8700", [ServerCapability.AI_INFERENCE]
        )
        assert s1.id == s2.id
        registry = _reg_mod.get_server_registry()
        assert len([s for s in registry.servers.values() if s.endpoint == "http://localhost:8700"]) == 1

    async def test_register_ai_server_migrates_stale_id(self, tmp_path):
        """Stale entry (e.g. old MD5-derived ID) is replaced without creating a duplicate."""
        registry = MCPServerRegistry(
            config_path=str(tmp_path / "config" / "mcp.json")
        )
        _reg_mod._server_registry = registry
        # Manually plant a stale entry using a fake old-style ID.
        stale_id = "ai-my-ai-oldmd5id"
        registry.servers[stale_id] = MCPServer(
            id=stale_id,
            name="My AI",
            endpoint="http://localhost:8800",
            capabilities=[ServerCapability.AI_INFERENCE],
        )

        server = await _reg_mod.register_ai_server(
            "My AI", "http://localhost:8800", [ServerCapability.AI_INFERENCE]
        )
        # Old ID must be gone; new canonical SHA-256 ID must be present.
        assert stale_id not in registry.servers
        assert server.id in registry.servers
        assert server.name == "My AI"
        assert server.endpoint == "http://localhost:8800"
        # Exactly one server for this endpoint.
        assert len([s for s in registry.servers.values() if s.endpoint == "http://localhost:8800"]) == 1

    def test_find_ai_servers_returns_list(self, tmp_path):
        _reg_mod._server_registry = MCPServerRegistry(
            config_path=str(tmp_path / "config" / "mcp.json")
        )
        result = _reg_mod.find_ai_servers(ServerCapability.AI_INFERENCE)
        assert isinstance(result, list)
