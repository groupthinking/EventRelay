"""
Unit tests for Antigravity SDK workflows in AgentOrchestrator.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.services.agents.adapters.agent_orchestrator import (
    AgentOrchestrator,
    OrchestrationResult,
)
from youtube_extension.services.agents.base_agent import AgentResult, BaseAgent


class DummySubagent(BaseAgent):
    """Dummy subagent for delegation testing."""

    def __init__(self, name: str = "dummy", config: dict | None = None):
        super().__init__(name=name, config=config)

    async def run(self, request):
        return AgentResult(
            agent_name=self.name,
            status="ok",
            output={"processed": True, "task": request.task, "data": request.params},
            logs=[f"{self.name} completed successfully"],
        )


@pytest.mark.asyncio
async def test_antigravity_delegation_workflow():
    orchestrator = AgentOrchestrator()
    orchestrator.register_agent_type("dummy_sub1", DummySubagent)
    orchestrator.register_agent_type("dummy_sub2", DummySubagent)

    result = await orchestrator.execute_antigravity_delegation(
        task_type="custom_task",
        input_data={"video_id": "auJzb1D-fag"},
        subagent_names=["dummy_sub1", "dummy_sub2"],
    )

    assert isinstance(result, OrchestrationResult)
    assert result.success is True
    assert "dummy_sub1" in result.results
    assert "dummy_sub2" in result.results
    assert len(result.agents_used) == 2

    # Check A2A log contains agent_dispatch entries
    a2a_log = orchestrator.get_a2a_log(limit=10)
    dispatch_entries = [
        m for m in a2a_log if m["content"].get("type") == "agent_dispatch"
    ]
    assert len(dispatch_entries) == 2
    assert dispatch_entries[0]["content"]["framework"] == "google_antigravity_sdk"


@pytest.mark.asyncio
async def test_antigravity_delegation_fallback_task_type():
    orchestrator = AgentOrchestrator()
    orchestrator.register_agent_type("action_implementer", DummySubagent)

    result = await orchestrator.execute_antigravity_delegation(
        task_type="action_planning",
        input_data={"action": "extract_transcripts"},
    )

    assert isinstance(result, OrchestrationResult)
    assert result.success is True
    assert "action_implementer" in result.results
