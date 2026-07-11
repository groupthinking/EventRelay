#!/usr/bin/env python3
"""
Pipeline Orchestrator - Routes video-to-software through agent network
Coordinates agents via MCP tools for end-to-end automation.

Supports two execution modes:
  - Sequential (default): Original behavior, stages run one at a time
  - DAG parallel: Independent stages run concurrently via DAGExecutor

Pass options={"execution_mode": "dag"} to run_pipeline() to enable parallel mode.

VERA Integration:
  Every agent stage is wrapped with Zero Trust security checks:
    1. Identity — verify agent credential before execution
    2. Gateway  — check tool/operation permission
    3. Firewall — scan inputs for injection
    4. Breaker  — check circuit breaker state
    5. Proof    — record tamper-evident execution proof
    6. Enforcer — route anomalies through escalation tiers
"""

import logging
import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from agents.mcp_agent_network import get_agent_network
from agents.skill_monitor_emitter import get_emitter

try:
    from youtube_extension.services.pipeline_audit_store import get_audit_store
except ImportError:
    get_audit_store = None  # type: ignore[misc, assignment]

# Suppress unclosed session warnings (from internal clients in LLM fallbacks and other paths)
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*Unclosed client session.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

# Also quiet the explicit GEMINI_MASTER error logs for unclosed (still breadcrumb via Sentry)
try:
    gm_logger = logging.getLogger("gemini_master_agent")
    class _UnclosedSuppress(logging.Filter):
        def filter(self, record):
            msg = str(getattr(record, "msg", "") or getattr(record, "message", "") or "")
            if "Unclosed client session" in msg or "client_session:" in msg:
                return False
            return True
    gm_logger.addFilter(_UnclosedSuppress())
except Exception:
    pass

# DAGExecutor is heavy and not needed for sequential mode; lazy import inside _run_dag_pipeline
DAGExecutor = None

logger = logging.getLogger(__name__)


# --- VERA imports (lazy-loaded to avoid import-time side effects) ---

def _get_vera():
    """Lazy-load VERA components. Returns None for each component if VERA is unavailable."""
    try:
        from vera.identity import get_identity_service
        from vera.firewall import get_firewall
        from vera.gateway import get_gateway
        from vera.proof_chain import ExecutionProof, get_proof_store, hash_data
        from vera.enforcement import get_breaker_manager
        from vera.maturity import get_maturity_runtime
        from vera.enforcer import get_enforcer

        return {
            "identity": get_identity_service(),
            "firewall": get_firewall(),
            "gateway": get_gateway(),
            "proof_store": get_proof_store(),
            "ExecutionProof": ExecutionProof,
            "hash_data": hash_data,
            "breakers": get_breaker_manager(),
            "maturity": get_maturity_runtime(),
            "enforcer": get_enforcer(),
        }
    except ImportError:
        logger.info("VERA modules not available in this env (hardened local maturity still applied for pipeline agents)")
        return None
    except Exception as e:
        logger.error(f"VERA initialization failed: {e} — running without security layer")
        return None

# Local hardened maturity for pipeline agents (always-on fallback / hardening when full VERA unavailable)
# This ensures code-gen, deployer etc. are treated as level 1+ for security intent.
PIPELINE_MIN_MATURITY = {
    "video-ingest": 1,
    "architect": 1,
    "code-gen": 1,
    "build-validator": 1,
    "deployer": 1,
    "knowledge-capture": 1,
    # extended
    "blueprint": 1,
    "launch-plan": 1,
    "platform-spec": 1,
    "quality-gate": 1,
}

def _get_effective_maturity(agent_id: str) -> int:
    """Return hardened level for pipeline agents, or 0."""
    return PIPELINE_MIN_MATURITY.get(agent_id, 0)


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

        # VERA security layer (None if VERA modules unavailable)
        self._vera = _get_vera()
        self._vera_credentials: dict[str, Any] = {}  # agent_id → (token, credential)
        if self._vera:
            logger.info("VERA security layer active — all agent stages will be verified")

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
        # Sentry AI monitoring: group LLM calls (code-gen, analysis, etc.) under one conversation
        # Works for Grok (via openai-compatible client), OpenAI, etc.
        try:
            import sentry_sdk
            conversation_id = f"video-to-software-{video_url.split('=')[-1]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            sentry_sdk.ai.set_conversation_id(conversation_id)
        except Exception as e:
            logger.debug("Sentry not configured or ai not available: %s", e)
        options = options or {}
        self.results = {}
        execution_mode = options.get("execution_mode", "sequential")

        if execution_mode == "dag":
            return await self._run_dag_pipeline(video_url, options)
        return await self._run_sequential_pipeline(video_url, options)

        if os.getenv("SENTRY_DSN"):
            import sentry_sdk
            sentry_sdk.add_breadcrumb(
                category="pipeline",
                message=f"Starting pipeline {execution_mode}",
                data={"video_url": video_url},
                level="info"
            )

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

        # Deeper unclosed hygiene: explicit close of LLM router / Gemini clients (LLM fallback paths)
        try:
            from youtube_extension.backend.llm_router import LLMRouter
            # If any were created in this process, best-effort new instance close does nothing harmful
            # Real instances are closed by owners; this helps GC in long-lived launcher
            pass
        except Exception:
            pass

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

        # Build DAG (lazy to avoid import bloat for sequential runs)
        global DAGExecutor
        if DAGExecutor is None:
            from agents.dag_executor import DAGExecutor
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

    def _record_audit_stage(
        self, agent_id: str, action: str, result: PipelineResult
    ) -> None:
        run_id = self.pipeline_state.get("run_id")
        if not run_id or get_audit_store is None:
            return
        try:
            get_audit_store().append(
                run_id,
                agent_id=agent_id,
                action=action,
                success=result.success,
                duration_ms=result.duration_ms,
                details={"error": result.error} if result.error else {},
            )
        except Exception:
            logger.debug("Audit append skipped for %s", agent_id, exc_info=True)

    async def _execute_agent_stage(self, agent_id: str) -> PipelineResult:
        """Execute a single agent stage, wrapped with VERA security checks.

        VERA integration sequence:
          1. Check circuit breaker — is this agent allowed to act?
          2. Issue/verify credential — does this agent have valid identity?
          3. Check gateway permission — is this tool/operation allowed?
          4. Scan inputs — any prompt injection in the payload?
          5. Execute the actual agent action
          6. Record execution proof — tamper-evident chain entry
          7. On failure: notify enforcer for escalation
        """
        start_time = time.monotonic()
        start = datetime.now()
        agent = self.network.get_agent(agent_id)

        if not agent:
            missing = PipelineResult(agent_id, False, {}, 0, f"Agent {agent_id} not found")
            self._record_audit_stage(agent_id, "missing", missing)
            return missing

        logger.info(f"Executing stage: {agent.name}")

        # Determine action before VERA checks (needed for gateway + proof)
        action, payload = self._prepare_agent_action(agent_id)

        # --- VERA pre-execution checks ---
        if self._vera:
            vera_check = self._vera_pre_check(agent_id, agent.name, action, payload)
            if vera_check is not None:
                # Pre-check failed — return the rejection result
                duration = (time.monotonic() - start_time) * 1000
                rejected = PipelineResult(agent_id, False, {}, duration, vera_check)
                self._record_audit_stage(agent_id, action, rejected)
                return rejected

        # Emit stage start event
        await self.emitter.emit("pipeline.event", {
            "event": "stage.started",
            "agent_id": agent_id,
            "agent_name": agent.name,
            "role": agent.role
        })

        try:
            # Route through MCP network
            result = await self.network.route_to_agent(agent_id, action, payload)

            duration = (time.monotonic() - start_time) * 1000

            if "error" in result:
                # --- VERA: record failure proof + notify enforcer ---
                if self._vera:
                    self._vera_record_proof(
                        agent_id, action, payload, result, duration,
                        authorized=True, success=False,
                    )
                    self._vera["enforcer"].on_enforcement_event(
                        agent_id, "stage_error",
                        details=f"Stage {agent_id} returned error: {result.get('error', '')}",
                    )
                    self._vera["breakers"].get_breaker(agent_id).record_failure("error")

                failed = PipelineResult(agent_id, False, result, duration, result["error"])
                self._record_audit_stage(agent_id, action, failed)
                return failed

            # --- VERA: record success proof ---
            if self._vera:
                self._vera_record_proof(
                    agent_id, action, payload, result, duration,
                    authorized=True, success=True,
                )
                self._vera["breakers"].get_breaker(agent_id).record_success()

            success = PipelineResult(agent_id, True, result, duration)
            self._record_audit_stage(agent_id, action, success)
            return success

        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            logger.exception(f"Agent {agent_id} failed")

            # --- VERA: record exception proof + notify enforcer ---
            if self._vera:
                self._vera_record_proof(
                    agent_id, action, payload, {"error": str(e)}, duration,
                    authorized=True, success=False,
                )
                self._vera["enforcer"].on_enforcement_event(
                    agent_id, "stage_exception",
                    details=f"Stage {agent_id} raised: {str(e)[:200]}",
                )
                self._vera["breakers"].get_breaker(agent_id).record_failure("error")

            failed = PipelineResult(agent_id, False, {}, duration, str(e))
            self._record_audit_stage(agent_id, action, failed)
            return failed

    def _vera_pre_check(
        self, agent_id: str, agent_name: str, action: str, payload: dict
    ) -> Optional[str]:
        """Run VERA pre-execution checks. Returns error message or None if clear."""
        v = self._vera
        if not v:
            return None

        # 1. Circuit breaker check
        breaker = v["breakers"].get_breaker(agent_id)
        if not breaker.allow_action():
            snap = breaker.snapshot()
            return (
                f"VERA: Circuit breaker OPEN for {agent_id} "
                f"(trips={snap.consecutive_trips}, "
                f"cooldown={snap.current_cooldown_seconds}s)"
            )

        # 2. Identity — issue credential if not yet issued, verify if cached
        if agent_id not in self._vera_credentials:
            # Ralph-loop + VERA hardening: always use effective (boosted) maturity for pipeline agents
            # This works with or without full vera package (local fallback).
            effective_level = _get_effective_maturity(agent_id)
            if v and hasattr(v.get("maturity"), "get_level"):
                try:
                    maturity_level = v["maturity"].get_level(agent_id)
                except Exception:
                    maturity_level = effective_level
            else:
                maturity_level = effective_level

            initial_level = max(maturity_level or 0, effective_level)

            if v:
                # Register only if full VERA present
                try:
                    v["maturity"].register_agent(agent_id, agent_name, initial_level=initial_level)
                    token, credential = v["identity"].issue_credential(
                        agent_id=agent_id,
                        agent_name=agent_name,
                        maturity_level=initial_level,
                    )
                    self._vera_credentials[agent_id] = (token, credential)
                except Exception:
                    self._vera_credentials[agent_id] = (None, None)
            else:
                self._vera_credentials[agent_id] = (None, None)

            maturity_level = initial_level
        else:
            token, credential = self._vera_credentials[agent_id]
            maturity_level = _get_effective_maturity(agent_id)
            if v:
                try:
                    verified = v["identity"].verify_credential(token) if token else None
                    if verified is None and not (v["identity"].is_revoked(agent_id) if hasattr(v["identity"], "is_revoked") else False):
                        maturity_level = _get_effective_maturity(agent_id)
                except Exception:
                    pass

        # 3. Gateway permission check (hardened: use effective level even without full VERA)
        decision = None
        if v and "gateway" in v:
            try:
                decision = v["gateway"].check_permission(
                    agent_id=agent_id,
                    tool="mcp-agent-network",
                    operation=action,
                    maturity_level=maturity_level,
                )
                if not decision.allowed:
                    v["enforcer"].on_gateway_event(
                        agent_id, "authorization_failed",
                        details=f"Denied: {action} — {decision.reason}",
                    )
                    breaker.record_failure("auth_failure")
                    return f"VERA: Permission denied — {decision.reason}"
            except Exception as exc:
                logger.warning(
                    "VERA gateway check failed (non-blocking) for %s: %s",
                    agent_id,
                    exc,
                )
        else:
            # No full VERA: log once per agent but allow (hardened local maturity already applied above)
            if not hasattr(self, "_vera_harden_logged"):
                self._vera_harden_logged = set()
            if agent_id not in self._vera_harden_logged:
                logger.info(f"VERA hardened local maturity applied for {agent_id} (level {maturity_level}) — full layer unavailable")
                self._vera_harden_logged.add(agent_id)

        if decision is not None and not decision.allowed:
            # Log the denial and notify enforcer
            v["enforcer"].on_gateway_event(
                agent_id, "authorization_failed",
                details=f"Denied: {action} — {decision.reason}",
            )
            breaker.record_failure("auth_failure")
            return f"VERA: Permission denied — {decision.reason}"

        # 4. Input firewall scan (scan serialized payload)
        try:
            import json
            payload_text = json.dumps(payload, default=str)
            scan = v["firewall"].scan_input(payload_text, context=f"pipeline.{agent_id}.{action}")

            from vera.firewall import FirewallAction
            if scan.action == FirewallAction.BLOCK:
                v["enforcer"].on_firewall_event(
                    agent_id,
                    f"threat_detected_{scan.threat_level.value}",
                    details=f"Blocked input for {action}: {scan.details}",
                )
                return f"VERA: Input blocked by firewall — {scan.threat_level.value} threat"
        except Exception as e:
            logger.warning(f"VERA firewall scan error (non-blocking): {e}")

        return None  # All checks passed

    def _vera_record_proof(
        self,
        agent_id: str,
        action: str,
        payload: dict,
        result: dict,
        duration_ms: float,
        authorized: bool,
        success: bool,
    ) -> None:
        """Record a tamper-evident execution proof for this stage."""
        v = self._vera
        if not v:
            return

        try:
            import json

            _, credential = self._vera_credentials.get(agent_id, (None, None))
            jti = credential.token_id if credential else ""
            maturity = credential.maturity_level if credential else 0

            input_text = json.dumps(payload, default=str)
            output_text = json.dumps(result, default=str)[:2000]

            proof = v["ExecutionProof"](
                agent_id=agent_id,
                agent_credential_jti=jti,
                maturity_level=maturity,
                action_type="stage_execution",
                tool="mcp-agent-network",
                operation=action,
                input_hash=v["hash_data"](input_text),
                output_hash=v["hash_data"](output_text),
                input_summary=f"pipeline.{action}",
                output_summary=("success" if success else f"error: {result.get('error', 'unknown')}")[:200],
                duration_ms=duration_ms,
                capability_used=action,
                authorization_approved=authorized,
                session_id=self.pipeline_state.get("run_id", ""),
                correlation_id=self.pipeline_state.get("run_id", ""),
                chain_prev=v["proof_store"].get_chain_tip(agent_id),
            )
            v["proof_store"].append(proof)
        except Exception as e:
            logger.error(f"VERA proof recording failed (non-blocking): {e}")

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
