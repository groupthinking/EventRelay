#!/usr/bin/env python3
"""
OpenAI Dev Task Manager (MCP-first)
- Orchestrates per-video development tasks using existing MCP pipeline
- Enforces step-gated verification before moving to next step
- Generates deliverables: Blueprint.md and SubAgent-Spec.json

Notes:
- Uses existing `src/mcp/mcp_video_processor.py` (no re-creation)
- Coordinates subagents via A2A framework when needed
- PR creation is output as a ready-to-run command script (no auto-push here)
"""

import asyncio
import json
import os
import importlib.util
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


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
        self.workspace_root = Path(workspace_root or "/Users/garvey/UVAI/src/core/youtube_extension")
        self.output_root = self.workspace_root / "workflow_output"
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _load_mcp_video_processor(self):
        """Dynamically load MCPVideoProcessor from src/mcp/mcp_video_processor.py by file path."""
        processor_path = self.workspace_root / "src" / "mcp" / "mcp_video_processor.py"
        if not processor_path.exists():
            raise FileNotFoundError(f"MCP video processor not found at {processor_path}")

        spec = importlib.util.spec_from_file_location("mcp_video_processor", str(processor_path))
        if spec is None or spec.loader is None:
            raise ImportError("Unable to load mcp_video_processor module spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        if not hasattr(module, "MCPVideoProcessor"):
            raise ImportError("MCPVideoProcessor class not found in mcp_video_processor module")
        return module.MCPVideoProcessor()

    async def run_videos(self, video_urls: List[str]) -> List[DevTaskResult]:
        results: List[DevTaskResult] = []
        for url in video_urls:
            result = await self._process_single_video(url)
            results.append(result)
        return results

    async def _process_single_video(self, video_url: str) -> DevTaskResult:
        processor = self._load_mcp_video_processor()
        try:
            processing = await processor.process_video_mcp(video_url)

            if not processing.get("success", True):
                return DevTaskResult(
                    video_id=processing.get("video_id", "unknown"),
                    success=False,
                    actions_generated=0,
                    transcript_segments=0,
                    category=processing.get("category", "unknown"),
                    result_path=None,
                    error=processing.get("error", "Unknown error")
                )

            # Gates
            transcript_segments = int(processing.get("transcript_segments", 0))
            actions_generated = int(processing.get("actions_generated", 0))

            self._enforce_gate(transcript_segments >= 5, "Transcript too short (<5 segments)")
            self._enforce_gate(actions_generated >= 2, "Insufficient actions generated (<2)")

            video_id = processing["video_id"]
            category = processing.get("category", "general")

            # Deliverables
            dest = self.output_root / video_id
            dest.mkdir(parents=True, exist_ok=True)

            blueprint_path = await self._write_blueprint(dest, video_id, video_url, category)
            spec_path = await self._write_subagent_spec(dest, video_id, category)

            # PR helper script (non-destructive)
            pr_script = await self._write_pr_script(dest, video_id)

            # Return
            return DevTaskResult(
                video_id=video_id,
                success=True,
                actions_generated=actions_generated,
                transcript_segments=transcript_segments,
                category=category,
                result_path=str(dest)
            )
        except Exception as e:
            # Hard fail gate
            return DevTaskResult(
                video_id="unknown",
                success=False,
                actions_generated=0,
                transcript_segments=0,
                category="unknown",
                result_path=None,
                error=str(e)
            )

    def _enforce_gate(self, condition: bool, message: str) -> None:
        if not condition:
            raise RuntimeError(f"GATE_FAILED: {message}")

    async def _write_blueprint(self, dest: Path, video_id: str, video_url: str, category: str) -> str:
        path = dest / "Blueprint.md"
        content = f"""
## Overview
- Video ID: {video_id}
- URL: {video_url}
- Objective: Recreate the core capability in UVAI (MCP-first) with subagents.
- Category: {category}

## Architecture
- Processor: `src/mcp/mcp_video_processor.py`
- Orchestrator (optional): `src/mcp/mcp_ecosystem_coordinator.py`
- YouTube Proxy: `mcp_servers/youtube_api_proxy.py`
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

    async def _write_subagent_spec(self, dest: Path, video_id: str, category: str) -> str:
        path = dest / "SubAgent-Spec.json"
        spec = {
            "agent_name": f"subagent-{video_id}",
            "role": f"Implement {category} capability in MCP stack",
            "tooling": ["python", "mcp", "a2a", "openai", "grok", "gemini", "pytest", "git"],
            "inputs": [
                {"name": "video_url", "type": "url"},
                {"name": "transcript", "type": "file"}
            ],
            "outputs": [
                {"name": "Blueprint.md", "type": "file"},
                {"name": "SubAgent-Spec.json", "type": "file"},
                {"name": f"feat/{video_id}", "type": "pr"}
            ],
            "milestone": "CI green on pytest -q"
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
        print("Usage: python -m agents.openai_dev_task_manager <youtube_url_1> [youtube_url_2 ...]")
        raise SystemExit(1)

    manager = OpenAIDevTaskManager()
    results = await manager.run_videos(sys.argv[1:])

    print(json.dumps([r.__dict__ for r in results], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
