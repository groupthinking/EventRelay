"""Guards for the runtime dead-stub cleanup."""

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.mcp_ecosystem_coordinator import MCPVideoProcessorServer
from agents.openai_dev_task_manager import OpenAIDevTaskManager

REPO = Path(__file__).resolve().parents[2]

DELETED = (
    "src/integration/api_gateway.py",
    "src/integration/performance_monitor.py",
    "src/integration/component_registry.py",
    "src/integration/context_manager.py",
    "src/integration/mcp_orchestrator.py",
    "src/analysis/code_structure_analyzer.py",
)


def test_unreferenced_stubs_are_gone() -> None:
    for relative in DELETED:
        assert not (REPO / relative).exists(), relative
    assert (REPO / "src/integration/gemini_video_fix.py").is_file()


def test_task_manager_loads_live_coordinator(tmp_path: Path) -> None:
    manager = OpenAIDevTaskManager(workspace_root=str(tmp_path))
    assert isinstance(manager._load_mcp_video_processor(), MCPVideoProcessorServer)


async def test_task_manager_uses_coordinator_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = OpenAIDevTaskManager(workspace_root=str(tmp_path))

    class _Processor:
        async def handle_request(self, request: dict) -> dict:
            assert request == {"action": "process_video", "video_id": "auJzb1D-fag"}
            return {
                "status": "success",
                "transcript_segments": 6,
                "analysis": {
                    "actions": [{"name": "one"}, {"name": "two"}],
                    "topics": ["demo"],
                },
            }

    monkeypatch.setattr(manager, "_load_mcp_video_processor", lambda: _Processor())
    result = await manager._process_single_video("https://www.youtube.com/watch?v=auJzb1D-fag")
    assert result.success is True
    assert result.video_id == "auJzb1D-fag"
    assert result.actions_generated == 2
    assert result.transcript_segments == 6
    assert result.category == "demo"
    assert (tmp_path / "workflow_output" / "auJzb1D-fag" / "Blueprint.md").is_file()


async def test_task_manager_reports_coordinator_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = OpenAIDevTaskManager(workspace_root=str(tmp_path))

    class _Processor:
        async def handle_request(self, request: dict) -> dict:
            return {"status": "error", "message": "Video extractor unavailable"}

    monkeypatch.setattr(manager, "_load_mcp_video_processor", lambda: _Processor())
    result = await manager._process_single_video("https://youtu.be/auJzb1D-fag")
    assert result.success is False
    assert result.video_id == "auJzb1D-fag"
    assert result.error == "Video extractor unavailable"


async def test_coordinator_returns_real_transcript_length() -> None:
    @dataclass
    class _Metadata:
        video_id: str

    transcript = [object(), object(), object(), object(), object()]
    actions = [{"name": "one"}, {"name": "two"}]
    content = SimpleNamespace(
        summary="summary",
        metadata=_Metadata(video_id="auJzb1D-fag"),
        topics=["demo"],
        sentiment="neutral",
        world_class_analysis={"quality_score": 1},
        actions=actions,
        transcript=transcript,
    )

    async def _process_video(video_url: str) -> SimpleNamespace:
        assert video_url == "https://www.youtube.com/watch?v=auJzb1D-fag"
        return content

    server = MCPVideoProcessorServer()
    server.extractor = SimpleNamespace(process_video=_process_video)
    result = await server.handle_request({"action": "process_video", "video_id": "auJzb1D-fag"})
    assert result["status"] == "success"
    assert result["video_id"] == "auJzb1D-fag"
    assert result["transcript_segments"] == len(transcript)
    assert result["analysis"]["actions"] == actions
