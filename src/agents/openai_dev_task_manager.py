#!/usr/bin/env python3
"""
OpenAI Dev Task Manager (MCP-first)
- Orchestrates per-video development tasks using existing MCP pipeline
- Enforces step-gated verification before moving to next step
- Generates deliverables: Blueprint.md and SubAgent-Spec.json

Notes:
- Video processing goes through `src/agents/mcp_ecosystem_coordinator.py`
- Coordinates subagents via A2A framework when needed
- PR creation is output as a ready-to-run command script (no auto-push here)
"""

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agents.mcp_ecosystem_coordinator import MCPVideoProcessorServer
from utils.path_utils import select_writable_dir
from youtube_extension.utils.video_utils import extract_video_id


@dataclass
class DevTaskResult:
    video_id: str
    success: bool
    actions_generated: int
    transcript_segments: int
    category: str
    result_path: Optional[str]
    error: Optional[str] = None


class OpenAIDevTaskManager:
    """MCP-first dev task manager to operationalize YouTube video capabilities."""

    def __init__(self, workspace_root: Optional[str] = None):
        explicit = workspace_root or os.getenv("WORKSPACE_ROOT")
        if explicit:
            self.workspace_root = Path(explicit)
        else:
            # Reuse the legacy dev root only if it already exists and is
            # writable; otherwise fall back to a runtime workspace under cwd.
            self.workspace_root = select_writable_dir(
                "/Users/garvey/UVAI/src/core/youtube_extension",
                Path.cwd() / "workflow_workspace",
            )
        self.output_root = self.workspace_root / "workflow_output"
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _load_mcp_video_processor(self) -> MCPVideoProcessorServer:
        """Load the live video processor from the MCP ecosystem coordinator."""
        return MCPVideoProcessorServer()

    async def run_videos(self, video_urls: list[str]) -> list[DevTaskResult]:
        results: list[DevTaskResult] = []
        for url in video_urls:
            result = await self._process_single_video(url)
            results.append(result)
        return results

    async def _process_single_video(self, video_url: str) -> DevTaskResult:
        processor = self._load_mcp_video_processor()
        video_id = "unknown"
        try:
            video_id = extract_video_id(video_url)
            processing = await processor.handle_request(
                {"action": "process_video", "video_id": video_id}
            )

            if processing.get("status") != "success":
                return DevTaskResult(
                    video_id=video_id,
                    success=False,
                    actions_generated=0,
                    transcript_segments=0,
                    category=str(processing.get("category", "unknown")),
                    result_path=None,
                    error=str(
                        processing.get("message")
                        or processing.get("error")
                        or "Unknown error"
                    ),
                )

            analysis = processing.get("analysis") or {}
            actions = analysis.get("actions") or []
            topics = analysis.get("topics") or []
            actions_generated = len(actions) if isinstance(actions, list) else 0
            transcript_segments = int(processing.get("transcript_segments") or 0)
            category = (
                topics[0]
                if isinstance(topics, list) and topics
                else str(processing.get("category", "general"))
            )

            self._enforce_gate(
                transcript_segments >= 5, "Transcript too short (<5 segments)"
            )
            self._enforce_gate(
                actions_generated >= 2, "Insufficient actions generated (<2)"
            )

            # Deliverables
            dest = self.output_root / video_id
            dest.mkdir(parents=True, exist_ok=True)

            await self._write_blueprint(dest, video_id, video_url, category)
            await self._write_subagent_spec(dest, video_id, category)

            # PR helper script (non-destructive)
            await self._write_pr_script(dest, video_id)

            # Return
            return DevTaskResult(
                video_id=video_id,
                success=True,
                actions_generated=actions_generated,
                transcript_segments=transcript_segments,
                category=category,
                result_path=str(dest),
            )
        except Exception as e:
            # Hard fail gate
            return DevTaskResult(
                video_id=video_id,
                success=False,
                actions_generated=0,
                transcript_segments=0,
                category="unknown",
                result_path=None,
                error=str(e),
            )

    def _enforce_gate(self, condition: bool, message: str) -> None:
        if not condition:
            raise RuntimeError(f"GATE_FAILED: {message}")

    async def _write_blueprint(
        self, dest: Path, video_id: str, video_url: str, category: str
    ) -> str:
        path = dest / "Blueprint.md"
        content = f"""
## Overview
- Video ID: {video_id}
- URL: {video_url}
- Objective: Recreate the core capability in UVAI (MCP-first) with subagents.
- Category: {category}

## Architecture
- Processor: `src/agents/mcp_ecosystem_coordinator.py` (`MCPVideoProcessorServer`)
- Orchestrator: `src/agents/mcp_ecosystem_coordinator.py` (`MCPEcosystemCoordinator`)
- YouTube Proxy: `shared/libs/youtube_proxy.py`
- A2A: `agents/a2a_framework.py`

## Dependencies
- Python deps: youtube-transcript-api, google-api-python-client, yt-dlp
- Env: `YOUTUBE_API_KEY` (valid key)

## Milestones
1. Transcript + Actions (gated: >=5 segments, >=2 actions)
2. Subagent Implementation (tests added)
3. PR and CI (pytest -q green)
""".strip()
        path.write_text(content)
        return str(path)

    async def _write_subagent_spec(
        self, dest: Path, video_id: str, category: str
    ) -> str:
        path = dest / "SubAgent-Spec.json"
        spec = {
            "agent_name": f"subagent-{video_id}",
            "role": f"Implement {category} capability in MCP stack",
            "tooling": [
                "python",
                "mcp",
                "a2a",
                "openai",
                "grok",
                "gemini",
                "pytest",
                "git",
            ],
            "inputs": [
                {"name": "video_url", "type": "url"},
                {"name": "transcript", "type": "file"},
            ],
            "outputs": [
                {"name": "Blueprint.md", "type": "file"},
                {"name": "SubAgent-Spec.json", "type": "file"},
                {"name": f"feat/{video_id}", "type": "pr"},
            ],
            "milestone": "CI green on pytest -q",
        }
        path.write_text(json.dumps(spec, indent=2))
        return str(path)

    async def _write_pr_script(self, dest: Path, video_id: str) -> str:
        path = dest / f"open_pr_{video_id}.sh"
        script = f"""#!/bin/bash
set -euo pipefail
BRANCH="feat/{video_id}"
git checkout -b "$BRANCH" || git checkout "$BRANCH"
git add -A
git commit -m "feat(video): implement {video_id} via MCP pipeline"
git push -u origin "$BRANCH"
"""
        path.write_text(script)
        os.chmod(path, 0o755)
        return str(path)


async def main():
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m agents.openai_dev_task_manager <youtube_url_1> [youtube_url_2 ...]"
        )
        raise SystemExit(1)

    manager = OpenAIDevTaskManager()
    results = await manager.run_videos(sys.argv[1:])

    print(json.dumps([r.__dict__ for r in results], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
