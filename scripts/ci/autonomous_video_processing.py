#!/usr/bin/env python3
"""Autonomous video processing batch runner.

Extracted from the inline heredoc that used to live in
``.github/workflows/autonomous-video-processing.yml`` so the logic is
lintable, unit-testable and versioned.

Design contract (Phase 1)
-------------------------
* **Nothing is ever reported as processed because a loop completed.** A video
  reaches ``delivered`` only when every pipeline stage — including the
  QA/verification stage — reports ``success``.
* Every run emits a machine-readable manifest tree::

      <out>/run.json                              run manifest
      <out>/videos/<video_id>/manifest.json       per-video manifest
      <out>/videos/<video_id>/stages/atlas.json   per-stage record
      <out>/videos/<video_id>/stages/prism.json
      <out>/videos/<video_id>/stages/forge.json
      <out>/videos/<video_id>/stages/sentinel.json

* A correlation ID is minted per video and carried into every stage record, so
  stage output can be linked back to the originating run.

Gate 0 decision: **map, don't duplicate.** ATLAS/PRISM/FORGE/SENTINEL are role
labels over the existing ``PipelineOrchestrator`` stages (see ``STAGES``), not a
second agent system.

Modes
-----
``discovery``
    Discover candidate videos and emit manifests. Stages are recorded as
    ``not_implemented``; the run terminates with ``discovery-only``. This is an
    honest, non-failing outcome — no video is claimed as processed.
``full``
    Run every stage. Any stage that is not implemented (Phase 2 work) or that
    fails causes the run to fail closed with ``blocked``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = "1.0"

#: Role label -> existing pipeline stage id (Gate 0 option A: map, don't duplicate).
STAGES: tuple[tuple[str, str, str], ...] = (
    ("atlas", "ATLAS", "video-ingest"),
    ("prism", "PRISM", "research-grounding"),
    ("forge", "FORGE", "code-gen"),
    ("sentinel", "SENTINEL", "quality-gate"),
)

#: The stage that gates delivery. If it does not succeed, nothing is delivered.
TERMINAL_STAGE = "sentinel"

#: Guardrails. A run that would exceed either cap fails closed before any work.
DEFAULT_MAX_VIDEOS_PER_RUN = 50
DEFAULT_MAX_MODEL_CALLS = 200

REQUIRED_SECRETS: dict[str, tuple[str, ...]] = {
    "discovery": ("YOUTUBE_API_KEY",),
    "full": ("YOUTUBE_API_KEY", "GEMINI_API_KEY"),
}

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

#: Stage implementations land here in Phase 2. Until then every stage resolves
#: to ``None`` and ``full`` mode fails closed rather than reporting success.
StageRunner = Callable[[dict[str, Any]], dict[str, Any]]
STAGE_RUNNERS: dict[str, StageRunner] = {}


class GuardrailError(RuntimeError):
    """Raised when a run violates a hard guardrail and must not start."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def correlation_id_for(run_id: str, category: str, video_id: str) -> str:
    """Deterministic per-video correlation ID.

    Deterministic (rather than random) so a re-run of the same video in the same
    run is linkable, and so tests can assert exact values.
    """
    digest = hashlib.sha256(f"{run_id}|{category}|{video_id}".encode()).hexdigest()
    return f"{video_id}-{digest[:12]}"


def check_required_secrets(mode: str, env: dict[str, str] | None = None) -> list[str]:
    """Return the names of required-but-missing secrets for ``mode``."""
    environ = os.environ if env is None else env
    required = REQUIRED_SECRETS.get(mode, ())
    return [name for name in required if not (environ.get(name) or "").strip()]


def enforce_guardrails(
    *,
    categories: Sequence[str],
    videos_per_category: int,
    mode: str,
    max_videos_per_run: int = DEFAULT_MAX_VIDEOS_PER_RUN,
    max_model_calls: int = DEFAULT_MAX_MODEL_CALLS,
) -> dict[str, int]:
    """Fail closed before any external call if the run exceeds its budget.

    ``full`` mode issues at most one model call per stage per video; ``discovery``
    mode issues none.
    """
    if videos_per_category < 1:
        raise GuardrailError("videos_per_category must be >= 1")
    if not categories:
        raise GuardrailError("at least one category is required")

    planned_videos = len(categories) * videos_per_category
    calls_per_video = len(STAGES) if mode == "full" else 0
    planned_calls = planned_videos * calls_per_video

    if planned_videos > max_videos_per_run:
        raise GuardrailError(
            f"planned videos ({planned_videos}) exceeds max_videos_per_run "
            f"({max_videos_per_run}); reduce categories or videos_per_category"
        )
    if planned_calls > max_model_calls:
        raise GuardrailError(
            f"planned model calls ({planned_calls}) exceeds max_model_calls "
            f"({max_model_calls}); reduce the batch size or raise the cap "
            "deliberately"
        )
    return {"planned_videos": planned_videos, "planned_model_calls": planned_calls}


def discover_videos(
    category: str,
    limit: int,
    api_key: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> list[str]:
    """Discover candidate video IDs for ``category`` via the YouTube Data API."""
    params = urllib.parse.urlencode(
        {
            "part": "id,snippet",
            "q": category,
            "type": "video",
            "maxResults": min(limit, 50),
            "key": api_key,
        }
    )
    request = urllib.request.Request(f"{YOUTUBE_SEARCH_URL}?{params}")  # noqa: S310
    open_url = opener or urllib.request.urlopen
    with open_url(request, timeout=30) as response:
        payload = json.loads(response.read())

    video_ids: list[str] = []
    for item in payload.get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        if video_id and video_id not in video_ids:
            video_ids.append(video_id)
    return video_ids[:limit]


def _stage_record(
    *,
    stage: str,
    role: str,
    pipeline_stage: str,
    video_id: str,
    correlation_id: str,
    status: str,
    error: str | None = None,
    outputs: dict[str, Any] | None = None,
    duration_ms: float = 0.0,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "role": role,
        "pipeline_stage": pipeline_stage,
        "video_id": video_id,
        "correlation_id": correlation_id,
        "status": status,
        "recorded_at": _utcnow(),
        "duration_ms": duration_ms,
        "outputs": outputs or {},
        "error": error,
    }


def run_stages(
    *,
    video_id: str,
    correlation_id: str,
    mode: str,
    runners: dict[str, StageRunner] | None = None,
) -> list[dict[str, Any]]:
    """Execute (or record as unimplemented) every stage for one video."""
    registry = STAGE_RUNNERS if runners is None else runners
    records: list[dict[str, Any]] = []
    halted = False

    for stage, role, pipeline_stage in STAGES:
        base = {
            "stage": stage,
            "role": role,
            "pipeline_stage": pipeline_stage,
            "video_id": video_id,
            "correlation_id": correlation_id,
        }
        if halted:
            records.append(
                _stage_record(**base, status="skipped", error="upstream stage did not succeed")
            )
            continue

        if mode != "full":
            records.append(
                _stage_record(**base, status="not_implemented", error="discovery mode: stage not executed")
            )
            continue

        runner = registry.get(stage)
        if runner is None:
            records.append(
                _stage_record(
                    **base,
                    status="not_implemented",
                    error=f"no runner registered for stage '{stage}' (Phase 2)",
                )
            )
            halted = True
            continue

        started = datetime.now(timezone.utc)
        try:
            outputs = runner({"video_id": video_id, "correlation_id": correlation_id})
            status = "success"
            error = None
        except Exception as exc:  # noqa: BLE001 - recorded as stage evidence
            outputs = {}
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
        duration_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        records.append(
            _stage_record(
                **base,
                status=status,
                error=error,
                outputs=outputs,
                duration_ms=duration_ms,
            )
        )
        if status != "success":
            halted = True

    return records


def video_status(stage_records: Iterable[dict[str, Any]], mode: str) -> str:
    """Derive a video's status from its actual stage results.

    A video is ``delivered`` only when every stage succeeded, including the
    terminal QA stage. It is never ``delivered`` because the loop finished.
    """
    records = list(stage_records)
    by_stage = {record["stage"]: record for record in records}

    if any(record["status"] == "failed" for record in records):
        return "failed"
    if mode != "full":
        return "discovered"
    terminal = by_stage.get(TERMINAL_STAGE)
    if terminal is not None and terminal["status"] == "success" and all(
        record["status"] == "success" for record in records
    ):
        return "delivered"
    return "blocked"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def process_category(
    *,
    category: str,
    videos_per_category: int,
    mode: str,
    run_id: str,
    output_dir: Path,
    api_key: str,
    dry_run: bool = False,
    runners: dict[str, StageRunner] | None = None,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Discover and process one category, returning the run manifest."""
    started_at = _utcnow()
    video_ids = discover_videos(category, videos_per_category, api_key, opener=opener)
    if not video_ids:
        raise RuntimeError(
            f"discovery returned zero videos for category '{category}' — "
            "failing closed rather than reporting an empty success"
        )

    videos: list[dict[str, Any]] = []
    for video_id in video_ids:
        cid = correlation_id_for(run_id, category, video_id)
        if dry_run:
            videos.append(
                {
                    "video_id": video_id,
                    "correlation_id": cid,
                    "status": "dry-run",
                    "stages": [],
                }
            )
            continue

        stage_records = run_stages(
            video_id=video_id, correlation_id=cid, mode=mode, runners=runners
        )
        status = video_status(stage_records, mode)
        video_dir = output_dir / "videos" / video_id
        for record in stage_records:
            _write_json(video_dir / "stages" / f"{record['stage']}.json", record)

        video_manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "category": category,
            "video_id": video_id,
            "correlation_id": cid,
            "mode": mode,
            "status": status,
            "recorded_at": _utcnow(),
            "stages": [
                {
                    "stage": record["stage"],
                    "role": record["role"],
                    "status": record["status"],
                    "error": record["error"],
                    "path": f"stages/{record['stage']}.json",
                }
                for record in stage_records
            ],
        }
        _write_json(video_dir / "manifest.json", video_manifest)
        videos.append(
            {
                "video_id": video_id,
                "correlation_id": cid,
                "status": status,
                "manifest": f"videos/{video_id}/manifest.json",
                "stages": video_manifest["stages"],
            }
        )

    counts = {
        status: sum(1 for video in videos if video["status"] == status)
        for status in ("delivered", "blocked", "failed", "discovered", "dry-run")
    }

    if dry_run:
        final_status = "dry-run"
    elif counts["failed"]:
        final_status = "failed"
    elif mode != "full":
        final_status = "discovery-only"
    elif counts["blocked"]:
        final_status = "blocked"
    else:
        final_status = "delivered"

    run_manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "category": category,
        "mode": mode,
        "dry_run": dry_run,
        "started_at": started_at,
        "completed_at": _utcnow(),
        "discovered": len(video_ids),
        "counts": counts,
        "final_status": final_status,
        "stage_roles": [
            {"stage": stage, "role": role, "pipeline_stage": pipeline_stage}
            for stage, role, pipeline_stage in STAGES
        ],
        "videos": videos,
    }
    _write_json(output_dir / "run.json", run_manifest)
    return run_manifest


def _emit_github_output(manifest: dict[str, Any]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    counts = manifest["counts"]
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"final_status={manifest['final_status']}\n")
        handle.write(f"discovered={manifest['discovered']}\n")
        handle.write(f"delivered={counts['delivered']}\n")
        handle.write(f"blocked={counts['blocked'] + counts['failed']}\n")


def _bool_env(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", default=os.environ.get("CATEGORY", ""))
    parser.add_argument(
        "--videos-per-category",
        type=int,
        default=int(os.environ.get("VIDEOS_PER_CATEGORY", "25") or 25),
    )
    parser.add_argument("--mode", choices=("discovery", "full"), default=os.environ.get("PIPELINE_MODE", "discovery"))
    parser.add_argument("--dry-run", action="store_true", default=_bool_env(os.environ.get("DRY_RUN")))
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    parser.add_argument("--output-dir", default=os.environ.get("OUTPUT_DIR", "pipeline_output"))
    parser.add_argument(
        "--max-videos-per-run",
        type=int,
        default=int(os.environ.get("MAX_VIDEOS_PER_RUN", DEFAULT_MAX_VIDEOS_PER_RUN)),
    )
    parser.add_argument(
        "--max-model-calls",
        type=int,
        default=int(os.environ.get("MAX_MODEL_CALLS", DEFAULT_MAX_MODEL_CALLS)),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    category = args.category.strip()
    if not category:
        print("::error::--category (or CATEGORY) is required", file=sys.stderr)
        return 2

    missing = set(check_required_secrets(args.mode))
    if missing:
        # Report the names from the static REQUIRED_SECRETS table rather than
        # from the environment-derived list, so no value read out of the
        # process environment can reach the log.
        for name in REQUIRED_SECRETS.get(args.mode, ()):
            if name in missing:
                print(
                    f"::error::missing required secret for mode '{args.mode}': {name}",
                    file=sys.stderr,
                )
        return 2

    try:
        budget = enforce_guardrails(
            categories=[category],
            videos_per_category=args.videos_per_category,
            mode=args.mode,
            max_videos_per_run=args.max_videos_per_run,
            max_model_calls=args.max_model_calls,
        )
    except GuardrailError as exc:
        print(f"::error::guardrail violation: {exc}", file=sys.stderr)
        return 2
    print(f"[{category}] budget: {budget}")

    try:
        manifest = process_category(
            category=category,
            videos_per_category=args.videos_per_category,
            mode=args.mode,
            run_id=args.run_id,
            output_dir=Path(args.output_dir),
            api_key=os.environ["YOUTUBE_API_KEY"],
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as a workflow error
        print(f"::error::[{category}] run failed: {exc}", file=sys.stderr)
        return 1

    _emit_github_output(manifest)
    print(
        f"[{category}] final_status={manifest['final_status']} "
        f"discovered={manifest['discovered']} counts={manifest['counts']}"
    )
    return 0 if manifest["final_status"] in {"delivered", "discovery-only", "dry-run"} else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
