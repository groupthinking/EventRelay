from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from starlette.requests import Request

from youtube_extension.backend.api.v1.router import (
    get_rendered_video,
    persist_rendered_video,
)
from youtube_extension.services.agents.adapters.hyperframes_agent import (
    HyperFramesAgent,
)
from youtube_extension.services.agents.dto import AgentRequest

TEST_VIDEO_ID = "auJzb1D-fag"
TEST_VIDEO_URL = f"https://www.youtube.com/watch?v={TEST_VIDEO_ID}"


class _FakeProcess:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        return (b"rendered", b"")


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "scheme": "http",
            "server": ("testserver", 80),
            "headers": [],
            "path": "/api/v1/videos/auJzb1D-fag/rendered",
            "query_string": b"",
        }
    )


@pytest.mark.asyncio
async def test_hyperframes_agent_generates_expected_html(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, str] = {}

    async def _fake_create_subprocess_exec(*cmd, cwd=None, **kwargs):
        output_index = cmd.index("--output") + 1
        output_path = Path(str(cmd[output_index]))
        output_path.write_bytes(b"mp4")
        composition_file = Path(str(cwd)).joinpath("index.html")
        assert composition_file.exists()
        captured["html"] = composition_file.read_text(encoding="utf-8")
        captured["command"] = " ".join(str(part) for part in cmd)
        return _FakeProcess()

    monkeypatch.setenv("HYPERFRAMES_ENABLED", "true")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)

    agent = HyperFramesAgent(config={"render_root": tmp_path})
    result = await agent.run(
        AgentRequest(
            task="video_rendering",
            params={
                "video_url": TEST_VIDEO_URL,
                "transcript": (
                    "EventRelay extracts context from YouTube videos and dispatches "
                    "specialized agents to act on the transcript."
                ),
                "metadata": {"title": "HyperFrames launch walkthrough"},
                "transcript_segments": [
                    {"start": 12, "text": "Pipeline kickoff and transcript extraction"},
                    {"start": 37, "text": "Agent dispatch and orchestration overview"},
                    {"start": 64, "text": "Published outputs and dashboard delivery"},
                ],
            },
        )
    )

    assert result.status == "ok"
    assert result.output["video_id"] == TEST_VIDEO_ID
    assert Path(result.output["file_path"]).exists()
    assert "HyperFrames launch walkthrough" in captured["html"]
    assert "Pipeline kickoff and transcript extraction" in captured["html"]
    assert "00:12" in captured["html"]
    assert "npx" in captured["command"]


@pytest.mark.asyncio
async def test_rendered_video_endpoint_returns_download_url(
    tmp_path: Path,
) -> None:
    rendered_file = tmp_path / "rendered.mp4"
    rendered_file.write_bytes(b"video")

    persist_rendered_video(
        {
            "metadata": {"video_id": TEST_VIDEO_ID},
            "outputs": {
                "hyperframes": {
                    "data": {
                        "status": "complete",
                        "title": "Rendered output",
                        "summary": "Short recap video",
                        "format": "mp4",
                        "duration_seconds": 12,
                        "file_path": str(rendered_file),
                    }
                }
            },
        },
        base_url="http://testserver",
    )

    response = await get_rendered_video(
        TEST_VIDEO_ID,
        request=_build_request(),
        download=False,
    )

    assert response.data["video_id"] == TEST_VIDEO_ID
    assert response.data["status"] == "complete"
    assert response.data["download_url"] == (
        f"http://testserver/api/v1/videos/{TEST_VIDEO_ID}/rendered?download=1"
    )
