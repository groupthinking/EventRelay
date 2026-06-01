"""Unit tests for core/mcp/protocol_bridge.py."""

from __future__ import annotations

import importlib.util
import sys
import types as _types
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
