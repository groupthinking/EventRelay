#!/usr/bin/env python3
"""
Pipeline Orchestrator - Routes video-to-software through agent network
Coordinates 6 agents via MCP tools for end-to-end automation
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from .mcp_agent_network import get_agent_network
from .skill_monitor_emitter import get_emitter

logger = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    """Result from a pipeline stage"""
    agent_id: str
    success: bool
    data: Dict[str, Any]
    duration_ms: float
    error: Optional[str] = None

class VideoPipelineOrchestrator:
    """
    Orchestrates video-to-software pipeline through agent network.

    Pipeline Flow:
    1. video-ingest → Extract video content
    2. architect → Determine tech stack
    3. code-gen → Generate application
    4. build-validator → Test and fix
    5. deployer → Push to GitHub/Vercel
    6. knowledge-capture → Learn from run
    """

    def __init__(self):
        self.network = get_agent_network()
        self.pipeline_state: Dict[str, Any] = {}
        self.results: Dict[str, PipelineResult] = {}
        self.emitter = get_emitter()

    async def run_pipeline(self, video_url: str, options: Optional[Dict] = None) -> Dict:
        """Execute full video-to-software pipeline"""
        options = options or {}
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"Starting pipeline run {run_id} for {video_url}")

        self.pipeline_state = {
            "run_id": run_id,
            "video_url": video_url,
            "started_at": datetime.now().isoformat(),
            "options": options
        }

        # Emit pipeline start event
        await self.emitter.emit("pipeline.event", {
            "event": "pipeline.started",
            "run_id": run_id,
            "video_url": video_url,
            "stages": len(self.network.get_pipeline_agents())
        })

        pipeline_agents = self.network.get_pipeline_agents()

        for agent_id in pipeline_agents:
            result = await self._execute_agent_stage(agent_id)
            self.results[agent_id] = result

            # Emit stage complete/failed event
            await self.emitter.emit("pipeline.event", {
                "event": "stage.completed" if result.success else "stage.failed",
                "run_id": run_id,
                "agent_id": agent_id,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error": result.error
            })

            if not result.success:
                logger.error(f"Pipeline failed at {agent_id}: {result.error}")
                if not options.get("continue_on_error", False):
                    break

            # Pass data to next stage
            self.pipeline_state[f"{agent_id}_output"] = result.data

        report = self._build_pipeline_report()

        # Emit pipeline complete event
        await self.emitter.emit("pipeline.event", {
            "event": "pipeline.completed",
            "run_id": run_id,
            "success": report["success"],
            "stages_completed": report["stages_completed"],
            "total_duration_ms": report["total_duration_ms"]
        })

        return report

    async def _execute_agent_stage(self, agent_id: str) -> PipelineResult:
        """Execute a single agent stage"""
        start = datetime.now()
        agent = self.network.get_agent(agent_id)

        if not agent:
            return PipelineResult(agent_id, False, {}, 0, f"Agent {agent_id} not found")

        logger.info(f"Executing stage: {agent.name}")

        # Emit stage start event
        await self.emitter.emit("pipeline.event", {
            "event": "stage.started",
            "agent_id": agent_id,
            "agent_name": agent.name,
            "role": agent.role
        })

        try:
            # Determine action based on agent role
            action, payload = self._prepare_agent_action(agent_id)

            # Route through MCP network
            result = await self.network.route_to_agent(agent_id, action, payload)

            duration = (datetime.now() - start).total_seconds() * 1000

            if "error" in result:
                return PipelineResult(agent_id, False, result, duration, result["error"])

            return PipelineResult(agent_id, True, result, duration)

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            logger.exception(f"Agent {agent_id} failed")
            return PipelineResult(agent_id, False, {}, duration, str(e))

    def _prepare_agent_action(self, agent_id: str) -> tuple:
        """Prepare action and payload for agent based on pipeline state"""

        if agent_id == "video-ingest":
            return "process_video_markdown", {
                "video_url": self.pipeline_state.get("video_url"),
                "extract_transcript": True,
                "analyze_content": True
            }

        elif agent_id == "architect":
            return "determine_architecture", {
                "video_analysis": self.pipeline_state.get("video-ingest_output", {}),
                "use_knowledge_context": True
            }

        elif agent_id == "code-gen":
            return "generate_fullstack", {
                "architecture": self.pipeline_state.get("architect_output", {}),
                "video_analysis": self.pipeline_state.get("video-ingest_output", {})
            }

        elif agent_id == "build-validator":
            return "get_error_patterns", {
                "generated_code": self.pipeline_state.get("code-gen_output", {}),
                "run_build": True
            }

        elif agent_id == "deployer":
            return "create_repo", {
                "code_output": self.pipeline_state.get("code-gen_output", {}),
                "build_result": self.pipeline_state.get("build-validator_output", {}),
                "deploy_to_vercel": self.pipeline_state.get("options", {}).get("deploy", True)
            }

        elif agent_id == "knowledge-capture":
            return "capture_technology", {
                "video_analysis": self.pipeline_state.get("video-ingest_output", {}),
                "architecture": self.pipeline_state.get("architect_output", {}),
                "deployment_result": self.pipeline_state.get("deployer_output", {})
            }

        return "unknown", {}

    def _build_pipeline_report(self) -> Dict:
        """Build final pipeline report"""
        successful_stages = sum(1 for r in self.results.values() if r.success)
        total_duration = sum(r.duration_ms for r in self.results.values())

        return {
            "run_id": self.pipeline_state.get("run_id"),
            "video_url": self.pipeline_state.get("video_url"),
            "success": all(r.success for r in self.results.values()),
            "stages_completed": f"{successful_stages}/{len(self.results)}",
            "total_duration_ms": total_duration,
            "stage_results": {
                agent_id: {
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "error": r.error
                }
                for agent_id, r in self.results.items()
            },
            "outputs": {
                k: v for k, v in self.pipeline_state.items()
                if k.endswith("_output")
            }
        }

async def run_video_to_software(video_url: str, **options) -> Dict:
    """Convenience function to run pipeline"""
    orchestrator = VideoPipelineOrchestrator()
    return await orchestrator.run_pipeline(video_url, options)
