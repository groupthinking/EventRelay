from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class _StepConfig:
    step_id: str
    display_name: str
    kind: str
    status: str
    start_offset: float
    end_offset: float
    inputs: Optional[List[Dict[str, Any]]] = None
    outputs: Optional[List[Dict[str, Any]]] = None
    artifacts: Optional[List[Dict[str, Any]]] = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _has_validator_runner(directory: Path) -> bool:
    package_json = directory / "package.json"
    if not package_json.is_file():
        return False

    try:
        package_data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    scripts = package_data.get("scripts") or {}
    return "validate:run" in scripts


def _discover_validator_root() -> Path:
    env_override = os.getenv("SOFTWARE_ON_DEMAND_ROOT")
    if env_override:
        candidate = Path(env_override).expanduser()
        if _has_validator_runner(candidate):
            return candidate.resolve()
        raise FileNotFoundError(
            f"software-on-demand validator package not found at SOFTWARE_ON_DEMAND_ROOT={env_override!r}"
        )

    candidate_subpaths = [
        Path("software-on-demand"),
        Path("OpenAI_Hub") / "projects" / "software-on-demand",
        Path("OpenAI_Hub") / "software-on-demand",
        Path("projects") / "software-on-demand",
    ]

    search_roots = {PROJECT_ROOT, PROJECT_ROOT.parent}
    for root in search_roots:
        for subpath in candidate_subpaths:
            candidate = root / subpath
            if candidate.is_dir() and _has_validator_runner(candidate):
                return candidate.resolve()

    raise FileNotFoundError("software-on-demand validator package not found.")


VALIDATOR_ROOT = _discover_validator_root()
RUNS_ROOT = (PROJECT_ROOT / "workflow_results" / "runs").resolve()


def _iso(base: datetime, offset_seconds: float) -> str:
    return (base + timedelta(seconds=offset_seconds)).isoformat(timespec="seconds") + "Z"


def _build_steps(video_result: Dict[str, Any], base_time: datetime) -> List[Dict[str, Any]]:
    metadata = video_result.get("metadata") or {}
    transcript = video_result.get("transcript_data") or []
    actionable = (video_result.get("actionable_content") or {}).get("actions") or []

    steps_config: List[_StepConfig] = []

    steps_config.append(
        _StepConfig(
            step_id="context-intake",
            display_name="Context Intake Agent",
            kind="ingest_metadata",
            status="succeeded" if metadata else "failed",
            start_offset=0,
            end_offset=2,
            outputs=[
                {
                    "name": "tutorial_metadata",
                    "type": "json",
                    "value": {
                        "title": metadata.get("title"),
                        "channel": metadata.get("channel_title"),
                        "duration": metadata.get("duration"),
                    },
                }
            ]
            if metadata
            else [],
        )
    )

    if transcript:
        steps_config.append(
            _StepConfig(
                step_id="transcribe",
                display_name="Transcribe Agent",
                kind="transcribe",
                status="succeeded",
                start_offset=2,
                end_offset=35,
                outputs=[
                    {
                        "name": "transcript_segments",
                        "type": "json",
                        "value": {"segment_count": len(transcript)},
                    }
                ],
                artifacts=[
                    {
                        "uri": f"memory://transcripts/{metadata.get('video_id', 'unknown')}.json",
                        "type": "file",
                        "description": "Transcript segments captured from the source video.",
                    }
                ],
            )
        )
    else:
        steps_config.append(
            _StepConfig(
                step_id="transcribe",
                display_name="Transcribe Agent",
                kind="transcribe",
                status="skipped",
                start_offset=2,
                end_offset=2,
            )
        )

    if actionable:
        steps_config.append(
            _StepConfig(
                step_id="extract-actions",
                display_name="Action Extraction Agent",
                kind="extract_actions",
                status="succeeded",
                start_offset=35,
                end_offset=42,
                inputs=[
                    {
                        "name": "transcript",
                        "type": "file",
                        "value": f"memory://transcripts/{metadata.get('video_id', 'unknown')}.json",
                    }
                ],
                outputs=[
                    {
                        "name": "action_plan",
                        "type": "json",
                        "value": {"actions_extracted": len(actionable)},
                    }
                ],
            )
        )
    else:
        steps_config.append(
            _StepConfig(
                step_id="extract-actions",
                display_name="Action Extraction Agent",
                kind="extract_actions",
                status="failed",
                start_offset=35,
                end_offset=42,
            )
        )

    return [
        {
            "id": cfg.step_id,
            "display_name": cfg.display_name,
            "kind": cfg.kind,
            "status": cfg.status,
            "started_at": _iso(base_time, cfg.start_offset),
            "completed_at": _iso(base_time, cfg.end_offset),
            "retries": 0,
            "inputs": cfg.inputs or [],
            "outputs": cfg.outputs or [],
            "artifacts": cfg.artifacts or [],
        }
        for cfg in steps_config
    ]


def _build_step_graph(video_result: Dict[str, Any], run_id: str, base_time: datetime) -> Dict[str, Any]:
    metadata = video_result.get("metadata") or {}
    video_url = video_result.get("video_url") or f"https://www.youtube.com/watch?v={metadata.get('video_id', run_id)}"

    steps = _build_steps(video_result, base_time)
    edges = [
        {"from": steps[i]["id"], "to": steps[i + 1]["id"]}
        for i in range(len(steps) - 1)
    ]

    return {
        "schema_version": "v1.0",
        "graph_id": run_id,
        "run_context": {
            "video_url": video_url,
            "run_id": run_id,
            "initiated_at": _iso(base_time, 0),
            "initiator": "continuous-runner",
            "stack": {
                "language": "python",
                "framework": "eventrelay",
            },
        },
        "steps": steps,
        "edges": edges,
    }


def _build_trace_events(
    step_graph: Dict[str, Any],
    video_result: Dict[str, Any],
    base_time: datetime,
    run_id: str,
) -> List[Dict[str, Any]]:
    metadata = video_result.get("metadata") or {}
    transcript = video_result.get("transcript_data") or []
    actionable = (video_result.get("actionable_content") or {}).get("actions") or []

    events: List[Dict[str, Any]] = []
    events.append(
        {
            "event_id": f"{run_id}-evt-0",
            "run_id": run_id,
            "event_type": "run.created",
            "emitted_at": _iso(base_time, 0),
            "severity": "info",
            "source": {"component": "orchestrator", "agent_id": "continuous-runner", "version": "1.0.0"},
            "payload": {
                "status": "queued",
                "video_url": video_result.get("video_url"),
                "initiator": "continuous-runner",
            },
        }
    )

    event_counter = 1
    for step in step_graph["steps"]:
        events.append(
            {
                "event_id": f"{run_id}-evt-{event_counter}",
                "run_id": run_id,
                "event_type": "agent.step.started",
                "emitted_at": step["started_at"],
                "severity": "info",
                "source": {"component": step["id"], "agent_id": step["id"], "version": "1.0.0"},
                "payload": {
                    "step_id": step["id"],
                    "step_kind": step["kind"],
                    "status": "running",
                    "started_at": step["started_at"],
                    "retry_count": 0,
                    "message": f"{step['display_name']} started.",
                },
            }
        )
        event_counter += 1
        events.append(
            {
                "event_id": f"{run_id}-evt-{event_counter}",
                "run_id": run_id,
                "event_type": "agent.step.completed"
                if step["status"] in {"succeeded", "skipped"}
                else "agent.step.failed",
                "emitted_at": step["completed_at"],
                "severity": "info" if step["status"] != "failed" else "error",
                "source": {"component": step["id"], "agent_id": step["id"], "version": "1.0.0"},
                "payload": {
                    "step_id": step["id"],
                    "step_kind": step["kind"],
                    "status": step["status"],
                    "started_at": step["started_at"],
                    "completed_at": step["completed_at"],
                    "retry_count": 0,
                    "message": f"{step['display_name']} {step['status']}.",
                },
            }
        )
        event_counter += 1

    if transcript:
        events.append(
            {
                "event_id": f"{run_id}-evt-{event_counter}",
                "run_id": run_id,
                "event_type": "artifact.generated",
                "emitted_at": _iso(base_time, 35),
                "severity": "info",
                "source": {"component": "transcribe", "agent_id": "transcribe", "version": "1.0.0"},
                "payload": {
                    "artifact_id": f"{run_id}-transcript",
                    "artifact_type": "file",
                    "uri": f"memory://transcripts/{metadata.get('video_id', 'unknown')}.json",
                    "description": "Transcript segments captured from the source video.",
                },
            }
        )
        event_counter += 1

    if actionable:
        events.append(
            {
                "event_id": f"{run_id}-evt-{event_counter}",
                "run_id": run_id,
                "event_type": "metric.updated",
                "emitted_at": _iso(base_time, 42),
                "severity": "info",
                "source": {"component": "extract-actions", "agent_id": "extract-actions", "version": "1.0.0"},
                "payload": {
                    "name": "actions.extracted",
                    "value": len(actionable),
                    "unit": "count",
                },
            }
        )
        event_counter += 1

    final_status = "failed" if any(step["status"] == "failed" for step in step_graph["steps"]) else "succeeded"
    events.append(
        {
            "event_id": f"{run_id}-evt-{event_counter}",
            "run_id": run_id,
            "event_type": "run.status.updated",
            "emitted_at": _iso(base_time, 45),
            "severity": "info" if final_status == "succeeded" else "error",
            "source": {"component": "orchestrator", "agent_id": "continuous-runner", "version": "1.0.0"},
            "payload": {
                "status": final_status,
                "video_url": video_result.get("video_url"),
                "initiator": "continuous-runner",
            },
        }
    )

    return events


def _write_json(target: Path, data: Any) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _run_validator(run_dir: Path) -> None:
    if not VALIDATOR_ROOT.exists():
        raise FileNotFoundError("software-on-demand validator package not found.")
    command = ["npm", "run", "validate:run", "--", str(run_dir)]
    subprocess.run(command, cwd=VALIDATOR_ROOT, check=True)


def persist_run_artifacts(
    video_result: Dict[str, Any],
    *,
    source: str = "unknown",
    logger: Optional[Any] = None,
) -> Path:
    video_id = (
        video_result.get("metadata", {}).get("video_id")
        or video_result.get("video_id")
        or video_result.get("id")
        or datetime.utcnow().strftime("%Y%m%d%H%M%S")
    )
    run_id = f"{source}-{video_id}"
    base_time = datetime.utcnow()

    run_dir = RUNS_ROOT / run_id
    step_graph = _build_step_graph(video_result, run_id, base_time)
    trace_events = _build_trace_events(step_graph, video_result, base_time, run_id)

    _write_json(run_dir / "step_graph.json", step_graph)
    _write_json(run_dir / "trace_events.json", trace_events)

    log_fn = getattr(logger, "info", None) if logger else None
    if callable(log_fn):
        log_fn("Persisted run artifacts", extra={"run_dir": str(run_dir), "run_id": run_id})
    else:
        print(f"[run-validation] Persisted run artifacts to {run_dir}")

    try:
        _run_validator(run_dir)
        if callable(log_fn):
            log_fn("Run artifacts validated", extra={"run_dir": str(run_dir), "run_id": run_id})
        else:
            print(f"[run-validation] Validation successful for {run_dir}")
    except subprocess.CalledProcessError as exc:
        if callable(log_fn):
            log_fn(
                "Run artifact validation failed",
                extra={"run_dir": str(run_dir), "run_id": run_id, "returncode": exc.returncode},
            )
        else:
            print(
                f"[run-validation] Validation failed for {run_dir} (exit code {exc.returncode})"
            )
        raise

    return run_dir
