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


# ===========================================================================
# services/agents/base_agent.py  (lines 8, 15 — plan() return / act() return)
# ===========================================================================

class TestBaseAgentMethods:
    def _make_agent(self):
        import logging
        from youtube_extension.services.agents.base_agent import BaseAgent
        from youtube_extension.services.agents.dto import AgentRequest, AgentResult

        class _Concrete(BaseAgent):
            name = "_coverage_concrete"
            def run(self, req: AgentRequest) -> AgentResult:
                return AgentResult(status="ok", output={"ran": True})

        return _Concrete(), AgentRequest

    def test_plan_returns_ok_result(self):
        agent, AgentRequest = self._make_agent()
        req = AgentRequest(task="test", params={})
        result = agent.plan(req)
        assert result.status == "ok"
        assert "plan" in result.output

    def test_act_delegates_to_run(self):
        agent, AgentRequest = self._make_agent()
        req = AgentRequest(task="test", params={})
        result = agent.act(req)
        assert result.status == "ok"
        assert result.output.get("ran") is True


# ===========================================================================
# services/agents/action_implementer_agent.py — shim imports (lines 10, 15)
# services/agents/agent_orchestrator.py       — shim imports (lines 9, 13)
# services/agents/hybrid_vision_agent.py      — shim imports (lines 6, 10)
# services/agents/video_master_agent.py       — shim imports (lines 6, 10)
# ===========================================================================

class TestAgentCompatibilityShims:
    """Importing compatibility shims covers the module-level import + __all__ lines."""

    def test_action_implementer_shim_exports_class(self):
        import youtube_extension.services.agents.action_implementer_agent as shim
        assert hasattr(shim, "ActionImplementerAgent")
        assert shim.ActionImplementerAgent.__name__ == "ActionImplementerAgent"

    def test_agent_orchestrator_shim_exports_class(self):
        import youtube_extension.services.agents.agent_orchestrator as shim
        assert hasattr(shim, "AgentOrchestrator")
        assert shim.AgentOrchestrator.__name__ == "AgentOrchestrator"

    def test_hybrid_vision_agent_shim_exports_class(self):
        import youtube_extension.services.agents.hybrid_vision_agent as shim
        assert hasattr(shim, "HybridVisionAgent")
        assert shim.HybridVisionAgent.__name__ == "HybridVisionAgent"

    def test_video_master_agent_shim_exports_class(self):
        import youtube_extension.services.agents.video_master_agent as shim
        assert hasattr(shim, "VideoMasterAgent")
        assert shim.VideoMasterAgent.__name__ == "VideoMasterAgent"


# ===========================================================================
# services/agents/adapters/action_implementer_agent.py  (line 357 — else branch)
# _calculate_total_time: when total_minutes < 60, returns f"{minutes}m"
# ===========================================================================

class TestCalculateTotalTimeElseBranch:
    def _make_agent(self):
        from youtube_extension.services.agents.adapters.action_implementer_agent import ActionImplementerAgent
        return ActionImplementerAgent()

    def test_calculate_total_time_zero_actions_returns_minutes_only(self):
        agent = self._make_agent()
        result = agent._calculate_total_time([], [])
        assert result == "0m"

    def test_calculate_total_time_few_actions_under_one_hour(self):
        agent = self._make_agent()
        result = agent._calculate_total_time([{"id": "p1"}], [])
        assert result == "30m"
        assert "h" not in result


# ===========================================================================
# services/agents/monitor.py  (lines 47-49, 67-68 — exception handlers)
# ===========================================================================

class TestMonitorExceptionHandlers:
    def test_monitor_file_access_exception_is_silenced(self, monkeypatch):
        import youtube_extension.services.agents.monitor as _mon

        def _raise():
            raise RuntimeError("boom from test")

        monkeypatch.setenv("EVENTRELAY_MONITOR_AGENT_GAPS", "true")
        monkeypatch.setattr(_mon, "get_analyzer", _raise)
        # Should not raise — exception is caught and logged silently (lines 47-49)
        _mon.monitor_file_access("src/example.py", "test task")

    def test_monitor_error_exception_is_silenced(self, monkeypatch):
        import youtube_extension.services.agents.monitor as _mon

        def _raise():
            raise RuntimeError("boom from test")

        monkeypatch.setenv("EVENTRELAY_MONITOR_AGENT_GAPS", "true")
        monkeypatch.setattr(_mon, "get_analyzer", _raise)
        # Should not raise — exception is caught and logged silently (lines 67-68)
        _mon.monitor_error("test_error", "ctx", 1)


# ===========================================================================
# services/agents/agent_gap_analyzer.py  (lines 143-144 — save_gaps exception)
# ===========================================================================

# ===========================================================================
# services/agents/adapters/video_master_agent.py  (lines 73-77 — try/except)
# Covers the Gemini client setup when api_key is present but Client() raises.
# ===========================================================================

class TestVideoMasterAgentGeminiSetupException:
    def test_gemini_client_init_exception_is_caught(self, monkeypatch):
        import logging
        from unittest.mock import MagicMock, patch
        import youtube_extension.services.agents.base_agent as _ba
        from youtube_extension.services.agents.adapters.video_master_agent import VideoMasterAgent

        mock_genai = MagicMock()
        mock_genai.Client.side_effect = RuntimeError("test: connection refused")

        # Ensure BaseAgent has the attributes _setup_gemini depends on
        if not hasattr(_ba.BaseAgent, "logger"):
            monkeypatch.setattr(_ba.BaseAgent, "logger", logging.getLogger("test"), raising=False)
        if not hasattr(_ba.BaseAgent, "get_config"):
            monkeypatch.setattr(
                _ba.BaseAgent, "get_config",
                lambda self, key, default=None: "test-api-key",
                raising=False,
            )
        else:
            # Patch existing get_config to return a test key so we reach lines 73-77
            monkeypatch.setattr(
                _ba.BaseAgent, "get_config",
                lambda self, key, default=None: "test-api-key",
                raising=True,
            )

        with patch("youtube_extension.services.agents.adapters.video_master_agent.GEMINI_AVAILABLE", True):
            with patch("youtube_extension.services.agents.adapters.video_master_agent.genai", mock_genai):
                agent = VideoMasterAgent()

        # Exception was silently caught — client remains None
        assert agent._gemini_client is None
        mock_genai.Client.assert_called_once_with(api_key="test-api-key")


class TestAgentGapAnalyzerSaveException:
    def test_save_gaps_exception_is_caught(self, tmp_path, monkeypatch):
        import logging
        from youtube_extension.services.agents.agent_gap_analyzer import AgentGapAnalyzer

        analyzer = AgentGapAnalyzer(storage_dir=tmp_path)
        # Make the gaps_file path unwritable by patching open inside the module
        import youtube_extension.services.agents.agent_gap_analyzer as _mod
        import builtins

        original_open = builtins.open

        def _failing_open(path, *args, **kwargs):
            if "gaps.json" in str(path):
                raise PermissionError("test: no write permission")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", _failing_open)
        # Should not raise — exception is silently caught on line 143-144
        analyzer.save_gaps()
