#!/usr/bin/env python3
"""Aggregate per-category run manifests into a single run status.

Runs in the ``summary`` job of ``autonomous-video-processing.yml``. The status it
computes is derived from the manifests the processing jobs actually wrote — never
from the fact that the matrix finished.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

#: Worst-to-best ordering. The run takes the worst status any category reported.
STATUS_PRECEDENCE = ("failed", "blocked", "discovery-only", "dry-run", "delivered")


def load_manifests(evidence_dir: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(evidence_dir.rglob("run.json")):
        try:
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"::warning::unreadable manifest {path}: {exc}", file=sys.stderr)
    return manifests


def aggregate(manifests: list[dict[str, Any]], process_result: str) -> dict[str, Any]:
    if not manifests:
        return {
            "final_status": "failed",
            "delivered": 0,
            "blocked": 0,
            "discovered": 0,
            "categories": [],
            "reason": "no run manifests were produced",
        }

    delivered = blocked = discovered = 0
    statuses = []
    categories = []
    for manifest in manifests:
        counts = manifest.get("counts", {})
        delivered += counts.get("delivered", 0)
        blocked += counts.get("blocked", 0) + counts.get("failed", 0)
        discovered += manifest.get("discovered", 0)
        status = manifest.get("final_status", "failed")
        statuses.append(status)
        categories.append(
            {"category": manifest.get("category", "?"), "final_status": status}
        )

    final_status = next(
        (status for status in STATUS_PRECEDENCE if status in statuses), "failed"
    )
    if process_result not in {"success", ""} and final_status == "delivered":
        final_status = "blocked"

    return {
        "final_status": final_status,
        "delivered": delivered,
        "blocked": blocked,
        "discovered": discovered,
        "categories": categories,
        "reason": "",
    }


def render_summary(result: dict[str, Any]) -> str:
    lines = [
        "## Autonomous Video Processing",
        "",
        f"**Final status:** `{result['final_status']}`",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Discovered | {result['discovered']} |",
        f"| Delivered (all stages incl. QA) | {result['delivered']} |",
        f"| Blocked / failed | {result['blocked']} |",
        f"| Mode | {os.environ.get('PIPELINE_MODE', 'discovery')} |",
        f"| Dry run | {os.environ.get('DRY_RUN', 'false')} |",
        f"| Triggered by | {os.environ.get('GITHUB_ACTOR', 'unknown')} |",
        "",
    ]
    if result["categories"]:
        lines += ["| Category | Status |", "|----------|--------|"]
        lines += [
            f"| {entry['category']} | `{entry['final_status']}` |"
            for entry in result["categories"]
        ]
        lines.append("")
    if result["reason"]:
        lines.append(f"> {result['reason']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    evidence_dir = Path(os.environ.get("EVIDENCE_DIR", "evidence"))
    result = aggregate(
        load_manifests(evidence_dir) if evidence_dir.exists() else [],
        os.environ.get("PROCESS_RESULT", ""),
    )

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    summary = render_summary(result)
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(summary)
    else:
        print(summary)

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"final_status={result['final_status']}\n")
            handle.write(f"delivered={result['delivered']}\n")
            handle.write(f"blocked={result['blocked']}\n")

    return 0 if result["final_status"] != "failed" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
