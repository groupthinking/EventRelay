#!/usr/bin/env python3
"""
Pipeline Orchestrator - Routes video-to-software through agent network
Coordinates agents via MCP tools for end-to-end automation.

Supports two execution modes:
  - Sequential (default): Original behavior, stages run one at a time
  - DAG parallel: Independent stages run concurrently via DAGExecutor

Pass options={"execution_mode": "dag"} to run_pipeline() to enable parallel mode.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .dag_executor import DAGExecutor
from .mcp_agent_network import get_agent_network
from .skill_monitor_emitter import get_emitter

logger = logging.getLogger(__name__)


# --- Stage dependency declarations ---
# Each stage declares which other stages must complete before it can start.
# Stages with no overlapping dependencies can run in parallel.
STAGE_DEPENDENCIES: dict[str, list[str]] = {
    "video-ingest": [],
    "architect": ["video-ingest"],
    "blueprint": ["video-ingest"],          # parallel with architect
    "launch-plan": ["video-ingest"],        # parallel with architect
    "platform-spec": ["video-ingest"],      # parallel with architect
    "code-gen": ["architect"],
    "build-validator": ["code-gen"],
    "quality-gate": ["build-validator"],     # correction loop entry point
    "deployer": ["build-validator"],
    "knowledge-capture": ["deployer"],
}

# Default stages for the original 6-agent pipeline
DEFAULT_PIPELINE_STAGES = [
    "video-ingest", "architect", "code-gen",
    "build-validator", "deployer", "knowledge-capture",
]

# Extended pipeline includes business artifact generators + quality gate
EXTENDED_PIPELINE_STAGES = [
    "video-ingest", "architect", "blueprint", "launch-plan", "platform-spec",
    "code-gen", "build-validator", "quality-gate", "deployer", "knowledge-capture",
]


@dataclass
class PipelineResult:
    """Result from a pipeline stage"""
    agent_id: str
    success: bool
    data: dict[str, Any]
    duration_ms: float
    error: Optional[str] = None


class VideoPipelineOrchestrator:
    """
    Orchestrates video-to-software pipeline through agent network.

    Pipeline Flow (sequential mode — original):
    1. video-ingest → Extract video content
    2. architect → Determine tech stack
    3. code-gen → Generate application
    4. build-validator → Test and fix
    5. deployer → Push to GitHub/Vercel
    6. knowledge-capture → Learn from run

    Pipeline Flow (DAG mode — extended):
    Batch 0: video-ingest
    Batch 1: architect, blueprint, launch-plan, platform-spec  (parallel)
    Batch 2: code-gen
    Batch 3: build-validator
    Batch 4: quality-gate, deployer  (parallel if quality passes)
    Batch 5: knowledge-capture
    """

    def __init__(self):
        self.network = get_agent_network()
        self.pipeline_state: dict[str, Any] = {}
        self.results: dict[str, PipelineResult] = {}
        self.emitter = get_emitter()

    async def run_pipeline(self, video_url: str, options: Optional[dict] = None) -> dict:
        """Execute video-to-software pipeline.

        Args:
            video_url: YouTube URL to process
            options: Pipeline options. Keys:
                execution_mode: "sequential" (default) or "dag"
                pipeline: "default" or "extended" (includes business artifacts)
                continue_on_error: bool
                preferences: dict of user preferences for agent context
        """
        options = options or {}
        execution_mode = options.get("execution_mode", "sequential")

        if execution_mode == "dag":
            return await self._run_dag_pipeline(video_url, options)
        return await self._run_sequential_pipeline(video_url, options)

    async def _run_sequential_pipeline(self, video_url: str, options: dict) -> dict:
        """Original sequential execution — preserved for backward compatibility."""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"Starting sequential pipeline run {run_id} for {video_url}")

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
            "execution_mode": "sequential",
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

    async def _run_dag_pipeline(self, video_url: str, options: dict) -> dict:
        """DAG-based parallel execution — independent stages run concurrently."""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"Starting DAG pipeline run {run_id} for {video_url}")

        self.pipeline_state = {
            "run_id": run_id,
            "video_url": video_url,
            "started_at": datetime.now().isoformat(),
            "options": options,
        }

        # Choose stage set
        pipeline_type = options.get("pipeline", "default")
        stage_ids = (
            EXTENDED_PIPELINE_STAGES if pipeline_type == "extended"
            else DEFAULT_PIPELINE_STAGES
        )

        # Build DAG
        dag = DAGExecutor(on_event=self.emitter.emit)

        for stage_id in stage_ids:
            deps = [
                d for d in STAGE_DEPENDENCIES.get(stage_id, [])
                if d in stage_ids  # only include deps that are in our stage set
            ]
            dag.add_stage(
                stage_id=stage_id,
                dependencies=deps,
                executor=self._make_stage_executor(stage_id),
                description=stage_id,
            )

        # Emit pipeline start with execution plan
        plan = dag.get_execution_plan()
        await self.emitter.emit("pipeline.event", {
            "event": "pipeline.started",
            "run_id": run_id,
            "video_url": video_url,
            "execution_mode": "dag",
            "execution_plan": plan,
        })

        # Execute DAG — context is our shared pipeline_state
        dag_results = await dag.execute(
            context=self.pipeline_state,
            continue_on_error=options.get("continue_on_error", False),
        )

        # Convert DAGExecutor results to PipelineResult for compatibility
        for stage_id, stage_result in dag_results.items():
            self.results[stage_id] = PipelineResult(
                agent_id=stage_id,
                success=stage_result.success,
                data=stage_result.data,
                duration_ms=stage_result.duration_ms,
                error=stage_result.error,
            )

        report = self._build_pipeline_report()
        report["execution_mode"] = "dag"
        report["execution_plan"] = plan

        await self.emitter.emit("pipeline.event", {
            "event": "pipeline.completed",
            "run_id": run_id,
            "success": report["success"],
            "stages_completed": report["stages_completed"],
            "total_duration_ms": report["total_duration_ms"],
            "execution_mode": "dag",
        })

        return report

    def _make_stage_executor(self, agent_id: str):
        """Create an async executor function for use with DAGExecutor.

        Each executor reads from the shared context dict (pipeline_state) and
        returns its result dict, which DAGExecutor stores back into context.
        """
        async def executor(context: dict) -> dict:
            result = await self._execute_agent_stage(agent_id)
            if not result.success:
                raise RuntimeError(result.error or f"Stage {agent_id} failed")
            return result.data

        return executor

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

        # --- Business artifact generators (Change 5) ---
        elif agent_id == "blueprint":
            return "generate_blueprint", {
                "video_analysis": self.pipeline_state.get("video-ingest_output", {}),
                "preferences": self.pipeline_state.get("options", {}).get("preferences"),
            }

        elif agent_id == "launch-plan":
            return "generate_launch_plan", {
                "video_analysis": self.pipeline_state.get("video-ingest_output", {}),
                "preferences": self.pipeline_state.get("options", {}).get("preferences"),
            }

        elif agent_id == "platform-spec":
            return "generate_platform_spec", {
                "video_analysis": self.pipeline_state.get("video-ingest_output", {}),
                "architecture": self.pipeline_state.get("architect_output"),
                "preferences": self.pipeline_state.get("options", {}).get("preferences"),
            }

        # --- Quality gate (Change 2) ---
        elif agent_id == "quality-gate":
            return "assess_quality", {
                "build_result": self.pipeline_state.get("build-validator_output", {}),
                "code_output": self.pipeline_state.get("code-gen_output", {}),
                "video_analysis": self.pipeline_state.get("video-ingest_output", {}),
            }

        return "unknown", {}

    def _build_pipeline_report(self) -> dict:
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

async def run_video_to_software(video_url: str, **options) -> dict:
    """Convenience function to run pipeline (sequential mode)."""
    orchestrator = VideoPipelineOrchestrator()
    return await orchestrator.run_pipeline(video_url, options)


async def run_video_to_software_parallel(video_url: str, **options) -> dict:
    """Convenience function to run pipeline in DAG parallel mode."""
    options["execution_mode"] = "dag"
    orchestrator = VideoPipelineOrchestrator()
    return await orchestrator.run_pipeline(video_url, options)
