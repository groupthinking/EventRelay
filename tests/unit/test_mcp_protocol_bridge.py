"""Unit tests for core/mcp/protocol_bridge.py."""

from __future__ import annotations

import importlib.util
import sys
import types as _types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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


class TestMCPProtocolBridgeSendProtocolRequest:
    async def _connected_bridge(self, ptype=ProtocolType.MCP):
        bridge = MCPProtocolBridge()
        bridge.register_adapter(_FakeAdapter(ptype))
        await bridge.initialize_adapter(ptype, {})
        return bridge

    async def test_history_entry_redacts_raw_request_and_response(self):
        bridge = await self._connected_bridge()
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="testuser", task="test_task", intent="testing")
        await bridge.send_protocol_request(
            ProtocolType.MCP,
            {"api_key": "sk-super-secret", "prompt": "hello"},
            context=context,
        )
        details = context.history[-1]["details"]
        assert "request" not in details
        assert "response" not in details
        assert details["request_summary"]["key_count"] == 2
        assert details["response_summary"] == {
            "type": "dict", "keys": ["status"], "key_count": 1
        }
        assert "sk-super-secret" not in str(details)

    async def test_failure_history_stores_sanitized_error(self):
        class _ErrorAdapter(_FakeAdapter):
            async def send_request(self, request, context):
                raise ValueError("bad request sk-should-not-persist")

        bridge = MCPProtocolBridge()
        bridge.register_adapter(_ErrorAdapter(ProtocolType.MCP))
        bridge.bridge_status[ProtocolType.MCP] = BridgeStatus.CONNECTED
        ctx_manager = _ctx_mod.get_context_manager()
        context = ctx_manager.create_context(user="testuser", task="test_task", intent="testing")

        with pytest.raises(ValueError):
            await bridge.send_protocol_request(ProtocolType.MCP, {}, context=context)

        details = context.history[-1]["details"]
        assert details["success"] is False
        assert details["error"] == {"type": "ValueError"}
        assert "sk-should-not-persist" not in str(details)


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

    async def test_partial_pre_existing_stats_dict_does_not_raise(self):
        bridge = await self._bridge_with(
            _CapableAdapter(ProtocolType.MCP, [ServerCapability.AI_INFERENCE]),
        )
        bridge.protocol_stats[ProtocolType.MCP] = {"success": 2}
        await bridge.route_request({})
        assert bridge.protocol_stats[ProtocolType.MCP] == {
            "in_flight": 0, "success": 3, "failure": 0
        }


OpenAIAdapter = _pb_mod.OpenAIAdapter


class TestOpenAIAdapterSecurity:
    async def test_initialize_accepts_public_https_base_url(self, monkeypatch):
        monkeypatch.setattr(
            _pb_mod.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [
                (_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))
            ],
        )
        monkeypatch.setattr(_pb_mod, "_HAS_OPENAI", True)
        _pb_mod.openai = MagicMock()
        _pb_mod.openai.AsyncOpenAI = MagicMock(return_value=MagicMock())

        adapter = OpenAIAdapter()
        result = await adapter.initialize(
            {"api_key": "sk-test", "base_url": "https://proxy.example.com/v1"}
        )
        assert result is True
        assert adapter.base_url == "https://proxy.example.com/v1"

    async def test_initialize_rejects_non_string_base_url(self):
        adapter = OpenAIAdapter()
        result = await adapter.initialize({"api_key": "sk-test", "base_url": None})
        assert result is False

    async def test_initialize_rejects_loopback_ipv4(self):
        adapter = OpenAIAdapter()
        result = await adapter.initialize({"api_key": "sk-test", "base_url": "https://127.0.0.1/v1"})
        assert result is False

    async def test_initialize_rejects_loopback_ipv6(self):
        adapter = OpenAIAdapter()
        result = await adapter.initialize({"api_key": "sk-test", "base_url": "https://[::1]/v1"})
        assert result is False

    async def test_initialize_rejects_private_resolution(self, monkeypatch):
        monkeypatch.setattr(
            _pb_mod.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [
                (_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))
            ],
        )
        adapter = OpenAIAdapter()
        result = await adapter.initialize({"api_key": "sk-test", "base_url": "https://proxy.internal/v1"})
        assert result is False

    async def test_initialize_rejects_mixed_public_and_private_resolution(self, monkeypatch):
        monkeypatch.setattr(
            _pb_mod.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [
                (_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
                (_pb_mod.socket.AF_INET, _pb_mod.socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443)),
            ],
        )
        adapter = OpenAIAdapter()
        result = await adapter.initialize({"api_key": "sk-test", "base_url": "https://mixed.example/v1"})
        assert result is False

    async def test_initialize_rejects_unresolvable_host(self, monkeypatch):
        def _raise_gaierror(*args, **kwargs):
            raise _pb_mod.socket.gaierror("unresolvable")

        monkeypatch.setattr(_pb_mod.socket, "getaddrinfo", _raise_gaierror)
        adapter = OpenAIAdapter()
        result = await adapter.initialize({"api_key": "sk-test", "base_url": "https://missing.example/v1"})
        assert result is False
