"""
Unit tests for Agent Graph, Handoff Envelopes, and Cyclic Self-Correction Loops.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from shared.youtube import RobustYouTubeMetadata
from youtube_extension.services.agents.adapters.agent_orchestrator import (
    AgentOrchestrator,
    OrchestrationResult,
)
from youtube_extension.services.agents.agent_graph import AgentGraph, LoopResult
from youtube_extension.services.agents.agent_handoff import AgentHandoffEnvelope
from youtube_extension.services.agents.base_agent import AgentResult, BaseAgent
from youtube_extension.services.workflows.transcript_action_workflow import (
    TranscriptActionWorkflow,
)


class MockStepAgent(BaseAgent):
    """Mock agent that appends its name to an execution path in output."""

    def __init__(self, name: str, step_tag: str):
        super().__init__(name=name)
        self.step_tag = step_tag

    async def run(self, request):
        out = dict(request.params)
        path = list(request.params.get("path", []))
        path.append(self.step_tag)
        score = request.params.get("score", 0) + 10
        out.update({"path": path, "score": score, "last_agent": self.name})
        return AgentResult(
            agent_name=self.name,
            status="ok",
            output=out,
        )


class MockCorrectionGenerator(BaseAgent):
    """Mock generator that fixes its output based on critique."""

    def __init__(self, name: str = "generator"):
        super().__init__(name=name)

    async def run(self, request):
        critique = request.params.get("previous_critique")
        if critique == "needs_lint_fix":
            return AgentResult(
                agent_name=self.name,
                status="ok",
                output={"code": "clean_code()", "lint_passed": True},
            )
        return AgentResult(
            agent_name=self.name,
            status="ok",
            output={"code": "dirty_code()", "lint_passed": False},
        )


def test_agent_handoff_envelope_lineage():
    env1 = AgentHandoffEnvelope(
        sender_agent="agent_a",
        recipient_agent="agent_b",
        intent="process_data",
        payload={"raw": 123},
    )
    assert env1.acknowledged is False
    env1.acknowledge()
    assert env1.acknowledged is True

    env2 = env1.forward(
        next_recipient="agent_c",
        next_intent="enrich_data",
        updated_payload={"enriched": True},
    )

    assert env2.sender_agent == "agent_b"
    assert env2.recipient_agent == "agent_c"
    assert env2.intent == "enrich_data"
    assert env2.payload["raw"] == 123
    assert env2.payload["enriched"] is True
    assert "agent_b" in env2.lineage
    assert env2.trace_id == env1.trace_id


@pytest.mark.asyncio
async def test_agent_graph_pipeline_execution():
    graph = AgentGraph(name="test_pipeline")
    agent_a = MockStepAgent(name="step_a", step_tag="A")
    agent_b = MockStepAgent(name="step_b", step_tag="B")
    agent_c = MockStepAgent(name="step_c", step_tag="C")

    graph.add_agent_node("step_a", agent_a)
    graph.add_agent_node("step_b", agent_b)
    graph.add_agent_node("step_c", agent_c)

    graph.add_edge("step_a", "step_b")
    graph.add_edge("step_b", "step_c")

    result = await graph.execute_pipeline("step_a", {"path": [], "score": 0})
    assert result["success"] is True
    assert result["visited_nodes"] == ["step_a", "step_b", "step_c"]
    assert result["final_payload"]["path"] == ["A", "B", "C"]
    assert result["final_payload"]["score"] == 30


@pytest.mark.asyncio
async def test_agent_graph_conditional_routing():
    graph = AgentGraph(name="conditional_graph")
    agent_start = MockStepAgent(name="start", step_tag="START")
    agent_fast = MockStepAgent(name="fast_path", step_tag="FAST")
    agent_deep = MockStepAgent(name="deep_path", step_tag="DEEP")

    graph.add_agent_node("start", agent_start)
    graph.add_agent_node("fast_path", agent_fast)
    graph.add_agent_node("deep_path", agent_deep)

    # Route based on requested mode
    def router(output: dict) -> str:
        return "fast_path" if output.get("mode") == "fast" else "deep_path"

    graph.add_conditional_router("start", router)

    # Test fast route
    res_fast = await graph.execute_pipeline("start", {"mode": "fast", "path": []})
    assert res_fast["visited_nodes"] == ["start", "fast_path"]

    # Test deep route
    res_deep = await graph.execute_pipeline("start", {"mode": "deep", "path": []})
    assert res_deep["visited_nodes"] == ["start", "deep_path"]


@pytest.mark.asyncio
async def test_agent_graph_fork_join():
    graph = AgentGraph(name="fork_join_graph")
    agent_1 = MockStepAgent(name="worker_1", step_tag="W1")
    agent_2 = MockStepAgent(name="worker_2", step_tag="W2")

    graph.add_agent_node("worker_1", agent_1)
    graph.add_agent_node("worker_2", agent_2)

    aggregated = await graph.execute_fork_join(
        subagent_names=["worker_1", "worker_2"],
        shared_input={"score": 50},
    )

    assert "worker_1" in aggregated
    assert "worker_2" in aggregated
    assert aggregated["worker_1"]["score"] == 60
    assert aggregated["worker_2"]["score"] == 60


@pytest.mark.asyncio
async def test_agent_graph_self_correction_loop_success():
    graph = AgentGraph(name="loop_graph")
    generator = MockCorrectionGenerator(name="gen_agent")
    graph.add_agent_node("gen_agent", generator)

    def evaluator(out: dict) -> tuple[bool, str | None]:
        if out.get("lint_passed") is True:
            return True, None
        return False, "needs_lint_fix"

    loop_res: LoopResult = await graph.execute_self_correction_loop(
        generator_name="gen_agent",
        evaluator_fn=evaluator,
        initial_input={},
        max_iterations=3,
    )

    assert loop_res.success is True
    assert loop_res.iterations == 2
    assert loop_res.final_output["code"] == "clean_code()"
    assert len(loop_res.history) == 2


@pytest.mark.asyncio
async def test_agent_graph_self_correction_loop_max_iterations():
    graph = AgentGraph(name="failing_loop_graph")
    generator = MockCorrectionGenerator(name="stubborn_agent")
    graph.add_agent_node("stubborn_agent", generator)

    # Evaluator that never passes
    def strict_evaluator(out: dict) -> tuple[bool, str | None]:
        return False, "always_fail"

    loop_res: LoopResult = await graph.execute_self_correction_loop(
        generator_name="stubborn_agent",
        evaluator_fn=strict_evaluator,
        initial_input={},
        max_iterations=2,
    )

    assert loop_res.success is False
    assert loop_res.iterations == 2
    assert "Exceeded max iterations" in (loop_res.error or "")


def test_orchestrator_create_agent_graph():
    orchestrator = AgentOrchestrator()
    g = orchestrator.create_agent_graph(name="test_graph")
    assert isinstance(g, AgentGraph)
    assert g.name == "test_graph"


@pytest.mark.asyncio
async def test_transcript_action_workflow_includes_agent_graph_meta(monkeypatch):
    meta = RobustYouTubeMetadata(
        video_id="auJzb1D-fag",
        title="Agent Graph Video",
        description="",
        channel_id="UC_test",
        channel_title="Test Channel",
        published_at="2024-01-01T00:00:00Z",
        duration="PT3M",
        view_count=100,
        like_count=10,
        comment_count=1,
        thumbnail_urls={},
        tags=[],
        category_id="28",
        default_language="en",
        default_audio_language="en",
        live_broadcast_content="none",
        transcript_available=True,
        transcript_segments=3,
        source_api="test",
    )

    class _FakeYTService:
        async def get_video_metadata(self, url):
            return meta

        async def get_transcript(self, video_id, language="en"):
            return {"text": "Test transcript", "segments": [], "source": "youtube_api"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    orch_result = OrchestrationResult(
        success=True,
        results={
            "transcript_action": AgentResult(
                agent_name="transcript_action",
                status="ok",
                output={"task_board": {}},
                logs=[],
            )
        },
        errors=[],
        total_processing_time=0.25,
        agents_used=["transcript_action", "strategy_agent"],
    )
    mock_orchestrator = MagicMock(spec=AgentOrchestrator)
    mock_orchestrator.execute_task = AsyncMock(return_value=orch_result)

    mock_ml = MagicMock()
    mock_ml.score_transcript = AsyncMock(return_value=None)
    mock_ml.record_transcript_outcome = AsyncMock(return_value=None)
    mock_ml.rank_actions = AsyncMock(return_value={"ranked_actions": []})

    mock_skill_builder = MagicMock()
    mock_skill_builder.get_context.return_value = {
        "has_data": False,
        "lessons": [],
        "success_rate": 0,
    }
    mock_skill_builder.record_deployment.return_value = None
    monkeypatch.setattr(
        "youtube_extension.services.workflows.transcript_action_workflow.get_skill_builder",
        lambda: mock_skill_builder,
    )

    workflow = TranscriptActionWorkflow(
        youtube_service_factory=lambda: _FakeYTService(),
        orchestrator=mock_orchestrator,
        hybrid_processor=MagicMock(),
        speech_service=MagicMock(),
        ml_client=mock_ml,
    )

    result = await workflow.run(
        "https://www.youtube.com/watch?v=auJzb1D-fag",
        transcript_text="Sample transcript for agent graph verification.",
        prefetched_metadata=meta,
    )

    assert result["success"] is True
    agent_graph = result["orchestration_meta"]["agent_graph"]
    assert agent_graph is not None
    assert agent_graph["graph_name"] == "transcript_action_graph"
    assert agent_graph["trace_id"]
    assert agent_graph["visited_nodes"] == [
        "transcript_extractor",
        "transcript_action",
        "strategy_agent",
        "self_correction_evaluator",
    ]
    assert agent_graph["lineage"] == ["transcript_action", "strategic_analysis"]
    assert agent_graph["handoff_count"] == 2
    assert agent_graph["loop_verified"] is True
