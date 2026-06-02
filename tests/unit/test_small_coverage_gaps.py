"""Targeted tests to cover small remaining coverage gaps."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ===========================================================================
# backend/api/mcp_bridge.py  (lines 21-40 — endpoint body)
# ===========================================================================

class TestMCPBridge:
    def _make_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from youtube_extension.backend.api.mcp_bridge import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    def test_hybrid_query_returns_200(self):
        client = self._make_client()
        resp = client.post("/mcp", json={"method": "tools/call", "params": {"name": "hybrid_query", "arguments": {"query": "hello"}}})
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        assert data["result"]["isError"] is False

    def test_hybrid_query_includes_query_in_response(self):
        client = self._make_client()
        resp = client.post("/mcp", json={"method": "tools/call", "params": {"name": "hybrid_query", "arguments": {"query": "test-query"}}})
        assert "test-query" in resp.json()["result"]["content"][0]["text"]

    def test_unknown_method_returns_404(self):
        client = self._make_client()
        resp = client.post("/mcp", json={"method": "unknown/method", "params": {}})
        assert resp.status_code == 404

    def test_unknown_tool_returns_404(self):
        client = self._make_client()
        resp = client.post("/mcp", json={"method": "tools/call", "params": {"name": "no_such_tool", "arguments": {}}})
        assert resp.status_code == 404

    def test_hybrid_query_no_arguments_still_works(self):
        client = self._make_client()
        resp = client.post("/mcp", json={"method": "tools/call", "params": {"name": "hybrid_query"}})
        assert resp.status_code == 200


# ===========================================================================
# backend/video_processor_interface.py  (lines 8-10 — Protocol class)
# ===========================================================================

class TestVideoProcessorInterface:
    def test_protocol_importable(self):
        from youtube_extension.backend.video_processor_interface import VideoProcessor
        assert VideoProcessor is not None

    def test_is_protocol(self):
        from typing import Protocol
        from youtube_extension.backend.video_processor_interface import VideoProcessor
        assert issubclass(VideoProcessor, Protocol)


# ===========================================================================
# services/agents/registry.py  (line 12 — return _REG[name])
# ===========================================================================

class TestAgentsRegistry:
    def test_get_returns_registered_class(self):
        from youtube_extension.services.agents import registry as _reg_mod
        from youtube_extension.services.agents.base_agent import BaseAgent

        class _DummyAgent(BaseAgent):
            name = "_test_dummy_agent_coverage"

            async def run(self, task, context=None):  # pragma: no cover
                return {}

        # Register and retrieve — covers the return path
        _reg_mod.register(_DummyAgent)
        result = _reg_mod.get("_test_dummy_agent_coverage")
        assert result is _DummyAgent

        # Cleanup
        del _reg_mod._REG["_test_dummy_agent_coverage"]

    def test_get_raises_key_error_for_unknown(self):
        from youtube_extension.services.agents import registry as _reg_mod
        with pytest.raises(KeyError):
            _reg_mod.get("__nonexistent__")
