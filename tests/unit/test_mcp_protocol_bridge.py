"""Unit tests for core/mcp/protocol_bridge.py."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types as _types
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

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
    full = _SRC / rel_path
    spec = importlib.util.spec_from_file_location(canonical, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[canonical] = mod
    spec.loader.exec_module(mod)
    return mod


_inject_stub("youtube_extension.core", str(_SRC / "youtube_extension/core"))
_inject_stub("youtube_extension.core.mcp", str(_SRC / "youtube_extension/core/mcp"))

_ctx_mod = _load("youtube_extension/core/mcp/context_manager.py", "youtube_extension.core.mcp.context_manager")
_reg_mod = _load("youtube_extension/core/mcp/server_registry.py", "youtube_extension.core.mcp.server_registry")
_pb_mod = _load("youtube_extension/core/mcp/protocol_bridge.py", "youtube_extension.core.mcp.protocol_bridge")

BridgeStatus = _pb_mod.BridgeStatus
MCPProtocolBridge = _pb_mod.MCPProtocolBridge
ProtocolAdapter = _pb_mod.ProtocolAdapter
ProtocolType = _pb_mod.ProtocolType
ServerCapability = _reg_mod.ServerCapability
MCPContext = _ctx_mod.MCPContext


# Minimal concrete adapter for tests
class _FakeAdapter(ProtocolAdapter):
    def __init__(self, ptype=ProtocolType.MCP):
        self._ptype = ptype

    @property
    def protocol_type(self):
        return self._ptype

    async def initialize(self, config):
        return True

    async def send_request(self, request, context):
        return {"status": "ok"}

    async def health_check(self):
        return True

    async def get_capabilities(self):
        return []


# ===========================================================================
# ProtocolType enum
# ===========================================================================


class TestProtocolType:
    def test_mcp_value(self):
        assert ProtocolType.MCP.value == "mcp"

    def test_openai_value(self):
        assert ProtocolType.OPENAI.value == "openai"

    def test_anthropic_value(self):
        assert ProtocolType.ANTHROPIC.value == "anthropic"

    def test_google_ai_value(self):
        assert ProtocolType.GOOGLE_AI.value == "google_ai"

    def test_huggingface_value(self):
        assert ProtocolType.HUGGINGFACE.value == "huggingface"

    def test_custom_value(self):
        assert ProtocolType.CUSTOM.value == "custom"

    def test_has_six_members(self):
        assert len(ProtocolType) == 6


# ===========================================================================
# BridgeStatus enum
# ===========================================================================


class TestBridgeStatus:
    def test_connected_value(self):
        assert BridgeStatus.CONNECTED.value == "connected"

    def test_disconnected_value(self):
        assert BridgeStatus.DISCONNECTED.value == "disconnected"

    def test_error_value(self):
        assert BridgeStatus.ERROR.value == "error"

    def test_maintenance_value(self):
        assert BridgeStatus.MAINTENANCE.value == "maintenance"

    def test_has_four_members(self):
        assert len(BridgeStatus) == 4


# ===========================================================================
# MCPProtocolBridge init
# ===========================================================================


class TestMCPProtocolBridgeInit:
    def test_adapters_starts_empty(self):
        bridge = MCPProtocolBridge()
        assert bridge.adapters == {}

    def test_bridge_status_starts_empty(self):
        bridge = MCPProtocolBridge()
        assert bridge.bridge_status == {}

    def test_request_handlers_initialized(self):
        bridge = MCPProtocolBridge()
        assert isinstance(bridge.request_handlers, dict)


# ===========================================================================
# MCPProtocolBridge.register_adapter
# ===========================================================================


class TestMCPProtocolBridgeRegisterAdapter:
    def test_adapter_stored(self):
        bridge = MCPProtocolBridge()
        adapter = _FakeAdapter(ProtocolType.MCP)
        bridge.register_adapter(adapter)
        assert ProtocolType.MCP in bridge.adapters

    def test_status_set_disconnected_on_register(self):
        bridge = MCPProtocolBridge()
        adapter = _FakeAdapter(ProtocolType.OPENAI)
        bridge.register_adapter(adapter)
        assert bridge.bridge_status[ProtocolType.OPENAI] == BridgeStatus.DISCONNECTED

    def test_multiple_adapters_registered(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        bridge.register_adapter(_FakeAdapter(ProtocolType.OPENAI))
        assert len(bridge.adapters) == 2


# ===========================================================================
# MCPProtocolBridge.get_bridge_status
# ===========================================================================


class TestMCPProtocolBridgeGetStatus:
    def test_returns_empty_when_no_adapters(self):
        bridge = MCPProtocolBridge()
        assert bridge.get_bridge_status() == {}

    def test_returns_copy_not_reference(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        status = bridge.get_bridge_status()
        status[ProtocolType.ANTHROPIC] = BridgeStatus.CONNECTED  # mutate copy
        assert ProtocolType.ANTHROPIC not in bridge.bridge_status


# ===========================================================================
# MCPProtocolBridge.get_available_protocols
# ===========================================================================


class TestMCPProtocolBridgeGetAvailable:
    def test_empty_when_no_adapters(self):
        bridge = MCPProtocolBridge()
        assert bridge.get_available_protocols() == []

    def test_empty_when_all_disconnected(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        assert bridge.get_available_protocols() == []

    def test_returns_connected_protocols(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        bridge.bridge_status[ProtocolType.MCP] = BridgeStatus.CONNECTED
        assert ProtocolType.MCP in bridge.get_available_protocols()


# ===========================================================================
# MCPProtocolBridge.register_request_handler
# ===========================================================================


class TestMCPProtocolBridgeRequestHandler:
    def test_handler_stored(self):
        bridge = MCPProtocolBridge()
        handler = lambda r: r
        bridge.register_request_handler("my_request", handler)
        assert "my_request" in bridge.request_handlers

    def test_handler_callable_stored(self):
        bridge = MCPProtocolBridge()
        handler = lambda r: {"result": True}
        bridge.register_request_handler("test", handler)
        assert bridge.request_handlers["test"] is handler

    def test_overwrite_existing_handler(self):
        bridge = MCPProtocolBridge()
        h1 = lambda r: "first"
        h2 = lambda r: "second"
        bridge.register_request_handler("action", h1)
        bridge.register_request_handler("action", h2)
        assert bridge.request_handlers["action"] is h2

    def test_multiple_distinct_handlers(self):
        bridge = MCPProtocolBridge()
        bridge.register_request_handler("a", lambda r: "a")
        bridge.register_request_handler("b", lambda r: "b")
        bridge.register_request_handler("c", lambda r: "c")
        assert len(bridge.request_handlers) == 3


# ===========================================================================
# MCPProtocolBridge.initialize_adapter
# ===========================================================================


class TestMCPProtocolBridgeInitializeAdapter:
    async def test_returns_false_when_no_adapter_registered(self):
        bridge = MCPProtocolBridge()
        result = await bridge.initialize_adapter(ProtocolType.MCP, {})
        assert result is False

    async def test_returns_true_when_init_succeeds(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        result = await bridge.initialize_adapter(ProtocolType.MCP, {"key": "val"})
        assert result is True

    async def test_status_connected_after_success(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        await bridge.initialize_adapter(ProtocolType.MCP, {})
        assert bridge.bridge_status[ProtocolType.MCP] == BridgeStatus.CONNECTED

    async def test_status_error_when_init_fails(self):
        class _FailAdapter(_FakeAdapter):
            async def initialize(self, config):
                return False

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FailAdapter(ProtocolType.OPENAI))
        await bridge.initialize_adapter(ProtocolType.OPENAI, {})
        assert bridge.bridge_status[ProtocolType.OPENAI] == BridgeStatus.ERROR

    async def test_status_error_when_init_raises(self):
        class _RaisingAdapter(_FakeAdapter):
            async def initialize(self, config):
                raise RuntimeError("boom")

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_RaisingAdapter(ProtocolType.ANTHROPIC))
        result = await bridge.initialize_adapter(ProtocolType.ANTHROPIC, {})
        assert result is False
        assert bridge.bridge_status[ProtocolType.ANTHROPIC] == BridgeStatus.ERROR


# ===========================================================================
# MCPProtocolBridge.send_protocol_request
# ===========================================================================


class TestMCPProtocolBridgeSendProtocolRequest:
    async def _connected_bridge(self, ptype=ProtocolType.MCP):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ptype))
        await bridge.initialize_adapter(ptype, {})
        return bridge

    async def test_raises_value_error_when_no_adapter(self):
        bridge = MCPProtocolBridge()
        with pytest.raises(ValueError, match="No adapter registered"):
            await bridge.send_protocol_request(ProtocolType.MCP, {})

    async def test_raises_runtime_error_when_not_connected(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        # Registered but not initialized => DISCONNECTED
        with pytest.raises(RuntimeError, match="not connected"):
            await bridge.send_protocol_request(ProtocolType.MCP, {})

    async def test_returns_response_from_adapter(self):
        bridge = await self._connected_bridge()
        resp = await bridge.send_protocol_request(ProtocolType.MCP, {"cmd": "test"})
        assert resp == {"status": "ok"}

    async def test_creates_context_when_none_provided(self):
        bridge = await self._connected_bridge()
        # Should not raise even without explicit context
        resp = await bridge.send_protocol_request(ProtocolType.MCP, {"cmd": "test"})
        assert resp is not None

    async def test_uses_provided_context(self):
        bridge = await self._connected_bridge()
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(
            user="testuser", task="test_task", intent="testing"
        )
        resp = await bridge.send_protocol_request(ProtocolType.MCP, {}, context=context)
        assert resp is not None

    async def test_context_metadata_set_after_request(self):
        bridge = await self._connected_bridge()
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(
            user="testuser", task="test_task", intent="testing"
        )
        await bridge.send_protocol_request(ProtocolType.MCP, {}, context=context)
        assert context.metadata.get("protocol") == "mcp"

    async def test_history_entry_added_on_success(self):
        bridge = await self._connected_bridge()
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(
            user="testuser", task="test_task", intent="testing"
        )
        await bridge.send_protocol_request(ProtocolType.MCP, {}, context=context)
        history_actions = [h["action"] for h in context.history]
        assert "protocol_request" in history_actions

    async def test_history_entry_redacts_raw_request(self):
        bridge = await self._connected_bridge()
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(
            user="testuser", task="test_task", intent="testing"
        )
        await bridge.send_protocol_request(
            ProtocolType.MCP,
            {
                "api_key": "sk-super-secret",
                "prompt": "hello",
                "sk-user-controlled-key": "value",
            },
            context=context,
        )
        last = context.history[-1]
        details = last["details"]
        # Raw request (and its secret) must not be persisted; only a summary.
        assert "request" not in details
        assert "sk-super-secret" not in str(details)
        summary = details["request_summary"]
        assert summary["keys"] == ["prompt"]
        assert "api_key" not in summary["keys"]
        assert "sk-user-controlled-key" not in str(summary)
        # The count describes only allowlisted fields, never arbitrary keys or
        # a value-dependent measure (e.g. len(str(request))).
        assert summary["key_count"] == 1
        assert "size" not in summary
        assert "response" not in details
        assert details["response_summary"] == {
            "type": "dict", "keys": ["status"], "key_count": 1
        }

    async def test_exception_propagates_and_history_records_failure(self):
        class _ErrorAdapter(_FakeAdapter):
            async def send_request(self, request, context):
                raise ValueError("bad request sk-should-not-persist")

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_ErrorAdapter(ProtocolType.MCP))
        bridge.bridge_status[ProtocolType.MCP] = BridgeStatus.CONNECTED

        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(
            user="testuser", task="test_task", intent="testing"
        )

        with pytest.raises(ValueError):
            await bridge.send_protocol_request(ProtocolType.MCP, {}, context=context)

        # History should contain the failed entry
        last = context.history[-1]
        assert last["details"]["success"] is False
        assert last["details"]["error"] == {"type": "ValueError"}
        assert "sk-should-not-persist" not in str(last["details"])

    async def test_history_failure_does_not_change_adapter_success(self) -> None:
        bridge = await self._connected_bridge()
        context = _ctx_mod.get_context_manager().create_context(
            user="testuser", task="test_task", intent="testing"
        )
        with patch.object(
            MCPContext,
            "add_history_entry",
            side_effect=RuntimeError("history unavailable"),
        ):
            response = await bridge.send_protocol_request(
                ProtocolType.MCP, {"prompt": "hello"}, context=context
            )
        assert response == {"status": "ok"}
        assert bridge.protocol_stats[ProtocolType.MCP] == {
            "in_flight": 0,
            "success": 1,
            "failure": 0,
        }

    async def test_history_failure_preserves_adapter_exception(self) -> None:
        class _ErrorAdapter(_FakeAdapter):
            async def send_request(
                self,
                request: dict[str, Any],
                context: MCPContext,
            ) -> dict[str, Any]:
                raise ValueError("adapter failed")

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_ErrorAdapter(ProtocolType.MCP))
        bridge.bridge_status[ProtocolType.MCP] = BridgeStatus.CONNECTED
        context = _ctx_mod.get_context_manager().create_context(
            user="testuser", task="test_task", intent="testing"
        )
        with patch.object(
            MCPContext,
            "add_history_entry",
            side_effect=RuntimeError("history unavailable"),
        ):
            with pytest.raises(ValueError, match="adapter failed"):
                await bridge.send_protocol_request(
                    ProtocolType.MCP, {"prompt": "hello"}, context=context
                )
        assert bridge.protocol_stats[ProtocolType.MCP] == {
            "in_flight": 0,
            "success": 0,
            "failure": 1,
        }


# ===========================================================================
# MCPProtocolBridge.route_request
# ===========================================================================


class TestMCPProtocolBridgeRouteRequest:
    async def _bridge_with_connected(self, ptype=ProtocolType.MCP):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ptype))
        await bridge.initialize_adapter(ptype, {})
        return bridge

    async def test_raises_when_no_adapters(self):
        bridge = MCPProtocolBridge()
        with pytest.raises(RuntimeError, match="No connected"):
            await bridge.route_request({})

    async def test_raises_when_preferred_not_available(self):
        bridge = await self._bridge_with_connected(ProtocolType.MCP)
        # Request OPENAI but only MCP is connected
        with pytest.raises(RuntimeError, match="No matching"):
            await bridge.route_request({}, preferred_protocols=[ProtocolType.OPENAI])

    async def test_routes_to_connected_protocol(self):
        bridge = await self._bridge_with_connected(ProtocolType.MCP)
        resp = await bridge.route_request({"cmd": "go"})
        assert resp == {"status": "ok"}

    async def test_routes_to_preferred_when_available(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        bridge.register_adapter(_FakeAdapter(ProtocolType.OPENAI))
        await bridge.initialize_adapter(ProtocolType.MCP, {})
        await bridge.initialize_adapter(ProtocolType.OPENAI, {})
        resp = await bridge.route_request(
            {}, preferred_protocols=[ProtocolType.OPENAI]
        )
        assert resp == {"status": "ok"}

    async def test_all_connected_used_when_no_preference(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        bridge.register_adapter(_FakeAdapter(ProtocolType.ANTHROPIC))
        await bridge.initialize_adapter(ProtocolType.MCP, {})
        await bridge.initialize_adapter(ProtocolType.ANTHROPIC, {})
        resp = await bridge.route_request({})
        assert resp == {"status": "ok"}


# ===========================================================================
# MCPProtocolBridge._select_protocol (intelligent routing)
# ===========================================================================


class _CapableAdapter(_FakeAdapter):
    def __init__(self, ptype, capabilities):
        super().__init__(ptype)
        self._capabilities = capabilities

    async def send_request(self, request, context):
        return {"status": "ok", "protocol": self._ptype.value}

    async def get_capabilities(self):
        return self._capabilities


class TestMCPProtocolBridgeIntelligentRouting:
    async def _bridge_with(self, *adapters):
        bridge = MCPProtocolBridge()
        for adapter in adapters:
            bridge.register_adapter(adapter)
            await bridge.initialize_adapter(adapter.protocol_type, {})
        return bridge

    async def test_routes_to_protocol_with_required_capability(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.DATA_PROCESSING]),
            _CapableAdapter(ProtocolType.OPENAI, [ServerCapability.AI_INFERENCE]),
        )
        resp = await bridge.route_request(
            {"required_capabilities": ["ai_inference"]}
        )
        assert resp["protocol"] == "openai"

    async def test_required_capabilities_are_not_forwarded(self) -> None:
        class _RecordingAdapter(_CapableAdapter):
            def __init__(self) -> None:
                super().__init__(
                    ProtocolType.OPENAI,
                    [ServerCapability.AI_INFERENCE],
                )
                self.request: Optional[dict[str, Any]] = None

            async def send_request(
                self,
                request: dict[str, Any],
                context: MCPContext,
            ) -> dict[str, Any]:
                self.request = request
                return {"status": "ok", "protocol": self._ptype.value}

        adapter = _RecordingAdapter()
        bridge = await self._bridge_with(adapter)
        response = await bridge.route_request(
            {
                "required_capabilities": [ServerCapability.AI_INFERENCE],
                "jsonrpc": "2.0",
                "method": "tools/call",
            }
        )
        assert response["status"] == "ok"
        assert adapter.request == {"jsonrpc": "2.0", "method": "tools/call"}

    async def test_accepts_server_capability_enum_values(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.DATA_PROCESSING]),
            _CapableAdapter(ProtocolType.OPENAI, [ServerCapability.AI_INFERENCE]),
        )
        resp = await bridge.route_request(
            {"required_capabilities": [ServerCapability.AI_INFERENCE]}
        )
        assert resp["protocol"] == "openai"

    async def test_raises_when_no_protocol_supports_capability(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.DATA_PROCESSING]),
        )
        with pytest.raises(RuntimeError, match="required capabilities"):
            await bridge.route_request(
                {"required_capabilities": [ServerCapability.AI_INFERENCE]}
            )

    async def test_skips_protocol_when_get_capabilities_raises(self):
        class _BrokenCapsAdapter(_CapableAdapter):
            async def get_capabilities(self):
                raise ConnectionError("unreachable")

        bridge = await self._bridge_with(
            _BrokenCapsAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
            _CapableAdapter(ProtocolType.OPENAI, [ServerCapability.AI_INFERENCE]),
        )
        resp = await bridge.route_request(
            {"required_capabilities": [ServerCapability.AI_INFERENCE]}
        )
        assert resp["protocol"] == "openai"

    async def test_skips_protocol_when_capability_discovery_times_out(self) -> None:
        class _HangingCapsAdapter(_CapableAdapter):
            async def get_capabilities(self) -> list[ServerCapability]:
                await asyncio.sleep(1)
                return [ServerCapability.AI_INFERENCE]

        bridge = await self._bridge_with(
            _HangingCapsAdapter(
                ProtocolType.MCP, [ServerCapability.AI_INFERENCE]
            ),
            _CapableAdapter(
                ProtocolType.OPENAI, [ServerCapability.AI_INFERENCE]
            ),
        )
        with patch.object(
            _pb_mod,
            "_CAPABILITY_DISCOVERY_TIMEOUT_SECONDS",
            0.001,
        ):
            response = await bridge.route_request(
                {"required_capabilities": [ServerCapability.AI_INFERENCE]}
            )
        assert response["protocol"] == "openai"

    async def test_prefers_less_loaded_protocol(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
            _CapableAdapter(ProtocolType.OPENAI, [ServerCapability.AI_INFERENCE]),
        )
        bridge.protocol_stats[ProtocolType.MCP] = {
            "in_flight": 5, "success": 10, "failure": 0
        }
        bridge.protocol_stats[ProtocolType.OPENAI] = {
            "in_flight": 1, "success": 10, "failure": 0
        }
        resp = await bridge.route_request({})
        assert resp["protocol"] == "openai"

    async def test_prefers_lower_error_rate_when_load_equal(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
            _CapableAdapter(ProtocolType.OPENAI, [ServerCapability.AI_INFERENCE]),
        )
        bridge.protocol_stats[ProtocolType.MCP] = {
            "in_flight": 0, "success": 2, "failure": 8
        }
        bridge.protocol_stats[ProtocolType.OPENAI] = {
            "in_flight": 0, "success": 9, "failure": 1
        }
        resp = await bridge.route_request({})
        assert resp["protocol"] == "openai"

    async def test_preference_order_breaks_ties(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
            _CapableAdapter(ProtocolType.OPENAI, [ServerCapability.AI_INFERENCE]),
        )
        resp = await bridge.route_request(
            {}, preferred_protocols=[ProtocolType.OPENAI, ProtocolType.MCP]
        )
        assert resp["protocol"] == "openai"

    async def test_unknown_capability_string_raises_value_error(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
        )
        with pytest.raises(ValueError, match="Unknown capability"):
            await bridge.route_request(
                {"required_capabilities": ["not_a_real_capability"]}
            )

    async def test_bare_string_required_capabilities_raises_type_error(self):
        # A bare string must not be iterated character-by-character.
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
        )
        with pytest.raises(TypeError, match="required_capabilities"):
            await bridge.route_request(
                {"required_capabilities": "ai_inference"}
            )

    async def test_stats_updated_after_successful_request(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
        )
        await bridge.route_request({})
        stats = bridge.protocol_stats[ProtocolType.MCP]
        assert stats == {"in_flight": 0, "success": 1, "failure": 0}

    async def test_stats_updated_after_failed_request(self):
        class _ErrorAdapter(_FakeAdapter):
            async def send_request(self, request, context):
                raise ValueError("bad request")

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_ErrorAdapter(ProtocolType.MCP))
        bridge.bridge_status[ProtocolType.MCP] = BridgeStatus.CONNECTED

        with pytest.raises(ValueError):
            await bridge.route_request({})

        stats = bridge.protocol_stats[ProtocolType.MCP]
        assert stats == {"in_flight": 0, "success": 0, "failure": 1}

    async def test_partial_pre_existing_stats_dict_does_not_raise(self):
        # A pre-populated stats dict missing some counters must not cause a
        # KeyError when a request increments them.
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
        )
        bridge.protocol_stats[ProtocolType.MCP] = {"success": 2}
        await bridge.route_request({})
        stats = bridge.protocol_stats[ProtocolType.MCP]
        assert stats == {"in_flight": 0, "success": 3, "failure": 0}


# ===========================================================================
# MCPProtocolBridge.health_check_all
# ===========================================================================


class TestMCPProtocolBridgeHealthCheckAll:
    async def test_empty_when_no_adapters(self):
        bridge = MCPProtocolBridge()
        results = await bridge.health_check_all()
        assert results == {}

    async def test_healthy_adapter_returns_true(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        results = await bridge.health_check_all()
        assert results[ProtocolType.MCP] is True

    async def test_status_updated_to_connected_when_healthy(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        # Status starts as DISCONNECTED
        await bridge.health_check_all()
        assert bridge.bridge_status[ProtocolType.MCP] == BridgeStatus.CONNECTED

    async def test_unhealthy_adapter_returns_false(self):
        class _UnhealthyAdapter(_FakeAdapter):
            async def health_check(self):
                return False

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_UnhealthyAdapter(ProtocolType.OPENAI))
        results = await bridge.health_check_all()
        assert results[ProtocolType.OPENAI] is False

    async def test_status_updated_to_error_when_unhealthy(self):
        class _UnhealthyAdapter(_FakeAdapter):
            async def health_check(self):
                return False

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_UnhealthyAdapter(ProtocolType.OPENAI))
        bridge.bridge_status[ProtocolType.OPENAI] = BridgeStatus.CONNECTED
        await bridge.health_check_all()
        assert bridge.bridge_status[ProtocolType.OPENAI] == BridgeStatus.ERROR

    async def test_exception_in_health_check_handled_gracefully(self):
        class _BrokenAdapter(_FakeAdapter):
            async def health_check(self):
                raise ConnectionError("unreachable")

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_BrokenAdapter(ProtocolType.ANTHROPIC))
        results = await bridge.health_check_all()
        assert results[ProtocolType.ANTHROPIC] is False
        assert bridge.bridge_status[ProtocolType.ANTHROPIC] == BridgeStatus.ERROR

    async def test_multiple_adapters_checked(self):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ProtocolType.MCP))
        bridge.register_adapter(_FakeAdapter(ProtocolType.OPENAI))
        results = await bridge.health_check_all()
        assert ProtocolType.MCP in results
        assert ProtocolType.OPENAI in results


# ===========================================================================
# Built-in adapter: OpenAIAdapter
# ===========================================================================

OpenAIAdapter = _pb_mod.OpenAIAdapter
AnthropicAdapter = _pb_mod.AnthropicAdapter
GoogleAIAdapter = _pb_mod.GoogleAIAdapter


class TestOpenAIAdapter:
    def test_protocol_type(self):
        adapter = OpenAIAdapter()
        assert adapter.protocol_type == ProtocolType.OPENAI

    async def test_initialize_returns_false_without_api_key(self, monkeypatch):
        # Ensure no key leaks in from the CI/runner environment so this asserts
        # the "no key provided anywhere" path deterministically.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        adapter = OpenAIAdapter()
        result = await adapter.initialize({})
        assert result is False

    async def test_initialize_returns_true_with_api_key(self):
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[(_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("104.18.7.192", 443))],
        ):
            result = await adapter.initialize({"api_key": "sk-test-key"})
        assert result is True

    async def test_initialize_stores_api_key(self):
        adapter = OpenAIAdapter()
        await adapter.initialize({"api_key": "sk-test", "model": "gpt-3.5"})
        assert adapter.api_key == "sk-test"
        assert adapter.model == "gpt-3.5"

    async def test_initialize_default_model(self):
        adapter = OpenAIAdapter()
        await adapter.initialize({"api_key": "sk-test"})
        assert adapter.model == "gpt-4"

    async def test_initialize_default_base_url(self):
        adapter = OpenAIAdapter()
        await adapter.initialize({"api_key": "sk-test"})
        assert adapter.base_url == "https://api.openai.com/v1"

    async def test_initialize_accepts_custom_https_base_url(self):
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[
                (
                    _pb_mod.socket.AF_INET,
                    _pb_mod.socket.SOCK_STREAM,
                    6,
                    "",
                    ("93.184.216.34", 443),
                ),
            ],
        ) as getaddrinfo:
            result = await adapter.initialize(
                {"api_key": "sk-test", "base_url": "https://proxy.example.com/v1"}
            )
        assert result is True
        assert adapter.base_url == "https://proxy.example.com/v1"
        getaddrinfo.assert_called_once_with(
            "proxy.example.com", 443, type=_pb_mod.socket.SOCK_STREAM
        )

    async def test_initialize_rejects_metadata_endpoint_base_url(self):
        adapter = OpenAIAdapter()
        result = await adapter.initialize(
            {
                "api_key": "sk-test",
                "base_url": "http://169.254.169.254/latest/meta-data/",
            }
        )
        assert result is False

    async def test_initialize_rejects_non_https_scheme_base_url(self):
        adapter = OpenAIAdapter()
        result = await adapter.initialize(
            {"api_key": "sk-test", "base_url": "file:///etc/passwd"}
        )
        assert result is False

    async def test_initialize_rejects_hostless_base_url(self):
        adapter = OpenAIAdapter()
        result = await adapter.initialize(
            {"api_key": "sk-test", "base_url": "https:///no-host"}
        )
        assert result is False

    async def test_initialize_rejects_non_string_base_url(self):
        # An explicit null/non-string base_url must be rejected cleanly rather
        # than raising TypeError out of urlparse() inside initialize().
        adapter = OpenAIAdapter()
        result = await adapter.initialize(
            {"api_key": "sk-test", "base_url": None}
        )
        assert result is False

    async def test_initialize_rejects_loopback_https_base_url(self) -> None:
        adapter = OpenAIAdapter()
        result = await adapter.initialize({"api_key": "sk-test", "base_url": "https://127.0.0.1"})
        assert result is False

    async def test_initialize_rejects_private_https_base_url(self) -> None:
        adapter = OpenAIAdapter()
        result = await adapter.initialize({"api_key": "sk-test", "base_url": "https://10.1.2.3"})
        assert result is False

    async def test_initialize_rejects_hostname_with_mixed_resolution(self) -> None:
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[
                (_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
                (_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
            ],
        ):
            result = await adapter.initialize(
                {"api_key": "sk-test", "base_url": "https://mixed.example.com/v1"}
            )
        assert result is False

    async def test_initialize_rejects_unresolvable_hostname(self) -> None:
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            side_effect=_pb_mod.socket.gaierror(),
        ):
            result = await adapter.initialize(
                {"api_key": "sk-test", "base_url": "https://does-not-resolve.example/v1"}
            )
        assert result is False

    async def test_initialize_rejects_invalid_port_without_raising(self) -> None:
        adapter = OpenAIAdapter()
        result = await adapter.initialize(
            {"api_key": "sk-test", "base_url": "https://example.com:invalid/v1"}
        )
        assert result is False

    async def test_initialize_rejects_out_of_range_port(self) -> None:
        adapter = OpenAIAdapter()
        result = await adapter.initialize(
            {"api_key": "sk-test", "base_url": "https://example.com:70000/v1"}
        )
        assert result is False

    async def test_initialize_rejects_malformed_ipv6(self) -> None:
        adapter = OpenAIAdapter()
        result = await adapter.initialize(
            {"api_key": "sk-test", "base_url": "https://[::1/v1"}
        )
        assert result is False

    async def test_initialize_rejects_malformed_dns_result(self) -> None:
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[(_pb_mod.socket.AF_INET,)],
        ):
            result = await adapter.initialize(
                {"api_key": "sk-test", "base_url": "https://malformed.example/v1"}
            )
        assert result is False

    async def test_health_check_returns_false_when_not_initialized(self):
        adapter = OpenAIAdapter()
        assert await adapter.health_check() is False

    async def test_get_capabilities_returns_ai_inference(self):
        adapter = OpenAIAdapter()
        caps = await adapter.get_capabilities()
        assert ServerCapability.AI_INFERENCE in caps

    async def test_send_request_raises_when_not_initialized(self):
        adapter = OpenAIAdapter()
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        with pytest.raises(RuntimeError, match="not initialized"):
            await adapter.send_request({"prompt": "hello"}, context)

    async def test_send_request_calls_openai_api(self):
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[(_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("104.18.7.192", 443))],
        ):
            await adapter.initialize({"api_key": "sk-test"})

        # Mock the client at the SDK boundary
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_message = MagicMock()
        mock_message.content = "Hello from GPT"

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.model = "gpt-4"
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        resp = await adapter.send_request({"prompt": "hello"}, context)

        assert resp["protocol"] == "openai"
        assert resp["content"] == "Hello from GPT"
        assert resp["model"] == "gpt-4"
        assert resp["finish_reason"] == "stop"
        assert resp["usage"]["total_tokens"] == 30
        assert resp["context_id"] == context.id

    async def test_send_request_uses_messages_field(self):
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[(_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("104.18.7.192", 443))],
        ):
            await adapter.initialize({"api_key": "sk-test"})

        mock_message = MagicMock()
        mock_message.content = "response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.model = "gpt-4"
        mock_response.choices = [mock_choice]
        mock_response.usage = None

        adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        messages = [{"role": "user", "content": "test message"}]
        resp = await adapter.send_request({"messages": messages}, context)

        call_kwargs = adapter._client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"] == messages
        assert resp["usage"] is None

    async def test_health_check_returns_true_when_api_reachable(self):
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[(_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("104.18.7.192", 443))],
        ):
            await adapter.initialize({"api_key": "sk-test"})
        adapter._client.models.retrieve = AsyncMock(return_value=MagicMock())
        assert await adapter.health_check() is True

    async def test_health_check_returns_false_on_api_error(self):
        adapter = OpenAIAdapter()
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[(_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("104.18.7.192", 443))],
        ):
            await adapter.initialize({"api_key": "sk-test"})
        adapter._client.models.retrieve = AsyncMock(side_effect=Exception("API error"))
        assert await adapter.health_check() is False


class TestAnthropicAdapter:
    def test_protocol_type(self):
        adapter = AnthropicAdapter()
        assert adapter.protocol_type == ProtocolType.ANTHROPIC

    async def test_initialize_returns_false_without_api_key(self, monkeypatch):
        # Ensure no key leaks in from the CI/runner environment so this asserts
        # the "no key provided anywhere" path deterministically.
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        adapter = AnthropicAdapter()
        result = await adapter.initialize({})
        assert result is False

    async def test_initialize_returns_true_with_api_key(self):
        adapter = AnthropicAdapter()
        result = await adapter.initialize({"api_key": "sk-ant-test"})
        assert result is True

    async def test_initialize_stores_model(self):
        adapter = AnthropicAdapter()
        await adapter.initialize({"api_key": "sk-ant-test", "model": "claude-sonnet"})
        assert adapter.model == "claude-sonnet"

    async def test_initialize_default_model(self):
        adapter = AnthropicAdapter()
        await adapter.initialize({"api_key": "sk-ant"})
        assert adapter.model == "claude-opus-4-8"

    async def test_health_check_returns_false_when_not_initialized(self):
        adapter = AnthropicAdapter()
        assert await adapter.health_check() is False

    async def test_get_capabilities_returns_ai_inference(self):
        adapter = AnthropicAdapter()
        caps = await adapter.get_capabilities()
        assert ServerCapability.AI_INFERENCE in caps

    async def test_send_request_raises_when_not_initialized(self):
        adapter = AnthropicAdapter()
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        with pytest.raises(RuntimeError, match="not initialized"):
            await adapter.send_request({"prompt": "hello"}, context)

    async def test_send_request_calls_anthropic_api(self):
        adapter = AnthropicAdapter()
        await adapter.initialize({"api_key": "sk-ant-test"})

        # Mock the client at the SDK boundary
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Hello from Claude"

        mock_usage = MagicMock()
        mock_usage.input_tokens = 15
        mock_usage.output_tokens = 25

        mock_response = MagicMock()
        mock_response.model = "claude-opus-4-8"
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = mock_usage

        adapter._client.messages.create = AsyncMock(return_value=mock_response)

        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        resp = await adapter.send_request({"prompt": "hello"}, context)

        assert resp["protocol"] == "anthropic"
        assert resp["content"] == "Hello from Claude"
        assert resp["model"] == "claude-opus-4-8"
        assert resp["stop_reason"] == "end_turn"
        assert resp["usage"]["input_tokens"] == 15
        assert resp["usage"]["output_tokens"] == 25
        assert resp["context_id"] == context.id

        # Verify adaptive thinking is passed
        call_kwargs = adapter._client.messages.create.call_args[1]
        assert call_kwargs["thinking"] == {"type": "adaptive"}

    async def test_send_request_uses_messages_field(self):
        adapter = AnthropicAdapter()
        await adapter.initialize({"api_key": "sk-ant-test"})

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "response"
        mock_usage = MagicMock()
        mock_usage.input_tokens = 5
        mock_usage.output_tokens = 10
        mock_response = MagicMock()
        mock_response.model = "claude-opus-4-8"
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = mock_usage

        adapter._client.messages.create = AsyncMock(return_value=mock_response)

        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        messages = [{"role": "user", "content": "test"}]
        await adapter.send_request({"messages": messages}, context)

        call_kwargs = adapter._client.messages.create.call_args[1]
        assert call_kwargs["messages"] == messages

    async def test_health_check_returns_true_when_api_reachable(self):
        adapter = AnthropicAdapter()
        await adapter.initialize({"api_key": "sk-ant-test"})
        adapter._client.messages.count_tokens = AsyncMock(return_value=MagicMock())
        assert await adapter.health_check() is True

    async def test_health_check_returns_false_on_api_error(self):
        adapter = AnthropicAdapter()
        await adapter.initialize({"api_key": "sk-ant-test"})
        adapter._client.messages.count_tokens = AsyncMock(side_effect=Exception("API error"))
        assert await adapter.health_check() is False


# ===========================================================================
# Built-in adapter: GoogleAIAdapter
# ===========================================================================


class TestGoogleAIAdapter:
    def test_protocol_type(self):
        adapter = GoogleAIAdapter()
        assert adapter.protocol_type == ProtocolType.GOOGLE_AI

    async def test_initialize_returns_false_without_api_key(self, monkeypatch):
        # Ensure no key leaks in from the CI/runner environment so this asserts
        # the "no key provided anywhere" path deterministically.
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        adapter = GoogleAIAdapter()
        result = await adapter.initialize({})
        assert result is False

    async def test_initialize_returns_true_with_api_key(self):
        adapter = GoogleAIAdapter()
        result = await adapter.initialize({"api_key": "google-key"})
        assert result is True

    async def test_initialize_stores_model(self):
        adapter = GoogleAIAdapter()
        await adapter.initialize({"api_key": "key", "model": "gemini-ultra"})
        assert adapter.model == "gemini-ultra"

    async def test_initialize_default_model(self):
        adapter = GoogleAIAdapter()
        await adapter.initialize({"api_key": "key"})
        assert adapter.model == "gemini-pro"

    async def test_health_check_returns_false_when_not_initialized(self):
        adapter = GoogleAIAdapter()
        assert await adapter.health_check() is False

    async def test_get_capabilities_returns_ai_inference(self):
        adapter = GoogleAIAdapter()
        caps = await adapter.get_capabilities()
        assert ServerCapability.AI_INFERENCE in caps

    async def test_send_request_raises_when_not_initialized(self):
        adapter = GoogleAIAdapter()
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        with pytest.raises(RuntimeError, match="not initialized"):
            await adapter.send_request({"prompt": "hello"}, context)

    async def test_send_request_calls_google_ai_api(self):
        adapter = GoogleAIAdapter()
        await adapter.initialize({"api_key": "google-key"})

        # Mock the client at the SDK boundary
        mock_response = MagicMock()
        mock_response.text = "Hello from Gemini"
        mock_response.candidates = []
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 8
        mock_response.usage_metadata.candidates_token_count = 12
        mock_response.usage_metadata.total_token_count = 20

        adapter._client.models.generate_content = MagicMock(return_value=mock_response)

        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        resp = await adapter.send_request({"prompt": "hello"}, context)

        assert resp["protocol"] == "google_ai"
        assert resp["content"] == "Hello from Gemini"
        assert resp["model"] == "gemini-pro"
        assert resp["usage"]["prompt_tokens"] == 8
        assert resp["usage"]["completion_tokens"] == 12
        assert resp["usage"]["total_tokens"] == 20
        assert resp["context_id"] == context.id

    async def test_send_request_flattens_messages_to_prompt(self):
        adapter = GoogleAIAdapter()
        await adapter.initialize({"api_key": "google-key"})

        mock_response = MagicMock()
        mock_response.text = "response"
        mock_response.candidates = []
        mock_response.usage_metadata = None

        adapter._client.models.generate_content = MagicMock(return_value=mock_response)

        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        messages = [
            {"role": "user", "content": "line one"},
            {"role": "assistant", "content": "line two"},
        ]
        resp = await adapter.send_request({"messages": messages}, context)

        call_kwargs = adapter._client.models.generate_content.call_args[1]
        assert "line one" in call_kwargs["contents"]
        assert "line two" in call_kwargs["contents"]
        assert resp["usage"] is None

    async def test_send_request_extracts_text_from_candidates_when_text_is_none(self):
        adapter = GoogleAIAdapter()
        await adapter.initialize({"api_key": "google-key"})

        # Simulate response.text being None but candidates having content
        mock_part = MagicMock()
        mock_part.text = "Extracted from candidate"
        mock_content = MagicMock()
        mock_content.parts = [mock_part]
        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_response = MagicMock()
        mock_response.text = None
        mock_response.candidates = [mock_candidate]
        mock_response.usage_metadata = None

        adapter._client.models.generate_content = MagicMock(return_value=mock_response)

        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="u", task="t", intent="i")
        resp = await adapter.send_request({"prompt": "hello"}, context)

        assert resp["content"] == "Extracted from candidate"

    async def test_health_check_returns_true_when_api_reachable(self):
        adapter = GoogleAIAdapter()
        await adapter.initialize({"api_key": "google-key"})
        adapter._client.models.list = MagicMock(return_value=[])
        assert await adapter.health_check() is True

    async def test_health_check_returns_false_on_api_error(self):
        adapter = GoogleAIAdapter()
        await adapter.initialize({"api_key": "google-key"})
        adapter._client.models.list = MagicMock(side_effect=Exception("API error"))
        assert await adapter.health_check() is False


# ===========================================================================
# get_protocol_bridge and send_ai_request convenience functions
# ===========================================================================

get_protocol_bridge = _pb_mod.get_protocol_bridge
send_ai_request = _pb_mod.send_ai_request


class TestGetProtocolBridge:
    def setup_method(self):
        # Reset global singleton between tests
        _pb_mod._protocol_bridge = None

    def teardown_method(self):
        _pb_mod._protocol_bridge = None

    def test_returns_mcp_protocol_bridge_instance(self):
        bridge = get_protocol_bridge()
        assert isinstance(bridge, MCPProtocolBridge)

    def test_returns_same_instance_on_second_call(self):
        b1 = get_protocol_bridge()
        b2 = get_protocol_bridge()
        assert b1 is b2

    def test_registers_openai_adapter(self):
        bridge = get_protocol_bridge()
        assert ProtocolType.OPENAI in bridge.adapters

    def test_registers_anthropic_adapter(self):
        bridge = get_protocol_bridge()
        assert ProtocolType.ANTHROPIC in bridge.adapters

    def test_registers_google_ai_adapter(self):
        bridge = get_protocol_bridge()
        assert ProtocolType.GOOGLE_AI in bridge.adapters


class TestSendAiRequest:
    def setup_method(self):
        _pb_mod._protocol_bridge = None

    def teardown_method(self):
        _pb_mod._protocol_bridge = None

    async def test_raises_when_no_protocol_connected(self):
        # Default bridge has all adapters DISCONNECTED (not yet initialized)
        with pytest.raises(RuntimeError, match="No connected"):
            await send_ai_request({"cmd": "test"})

    async def test_raises_for_specific_disconnected_protocol(self):
        with pytest.raises(RuntimeError):
            await send_ai_request({"cmd": "test"}, protocol=ProtocolType.OPENAI)

    async def test_sends_when_protocol_specified_and_connected(self):
        bridge = get_protocol_bridge()
        # Initialize OPENAI adapter with a key and mock the client
        adapter = bridge.adapters[ProtocolType.OPENAI]
        with patch.object(
            _pb_mod.socket,
            "getaddrinfo",
            return_value=[(_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("104.18.7.192", 443))],
        ):
            await adapter.initialize({"api_key": "sk-test"})
        bridge.bridge_status[ProtocolType.OPENAI] = BridgeStatus.CONNECTED

        # Mock the SDK client response
        mock_message = MagicMock()
        mock_message.content = "mocked"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.model = "gpt-4"
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

        resp = await send_ai_request({"cmd": "test"}, protocol=ProtocolType.OPENAI)
        assert resp["protocol"] == "openai"
