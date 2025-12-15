#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
EVENTRELAY_ROOT = ROOT / "OpenAI_Hub" / "projects" / "EventRelay"
VALIDATION_LOG = ROOT / "workflow_results" / "runs" / "validation_log.jsonl"
COLLECTIVE_LOG = EVENTRELAY_ROOT / "collective_learning_monitor_log.jsonl"
REPORTS_DIR = EVENTRELAY_ROOT / "reports"


def _read_jsonl(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if limit is not None:
        lines = lines[-limit:]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _summarise_validation(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total_runs": len(records),
        "passed": sum(1 for r in records if r.get("status") == "passed"),
        "failed": [r for r in records if r.get("status") == "failed"],
        "last_timestamp": records[-1]["timestamp"] if records else None,
    }


def _summarise_collective(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "iterations": len(records),
        "last_snapshot": records[-1] if records else {},
        "failures": [],
        "test_failures": [],
    }
    for record in records:
        for test in record.get("tests", []):
            if test.get("status") not in {"passed", "skipped"}:
                summary["test_failures"].append(test)
        if not record.get("bridge_db_present", False):
            summary["failures"].append({"timestamp": record.get("timestamp"), "reason": "bridge missing"})
    return summary


def generate_report(validation_limit: int, monitor_limit: int) -> str:
    validation_records = _read_jsonl(VALIDATION_LOG, validation_limit)
    collective_records = _read_jsonl(COLLECTIVE_LOG, monitor_limit)

    validation_summary = _summarise_validation(validation_records)
    collective_summary = _summarise_collective(collective_records)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines: List[str] = []
    lines.append("# AI Ops Skill Mesh – Operations Snapshot")
    lines.append(f"_Generated: {now}_")
    lines.append("")

    lines.append("## Artifact Validation")
    if validation_records:
        lines.append(f"- Total runs tracked: **{validation_summary['total_runs']}**")
        lines.append(f"- Pass rate: **{validation_summary['passed']}/{validation_summary['total_runs']}**")
        if validation_summary["failed"]:
            lines.append("- ❌ Failed runs:")
            for fail in validation_summary["failed"]:
                lines.append(f"  - `{fail['run']}` at {fail['timestamp']}")
        else:
            lines.append("- ✅ No failed runs in the sampled window.")
        lines.append(f"- Last validation timestamp: `{validation_summary['last_timestamp']}`")
    else:
        lines.append("- ⚠️ No validation entries recorded.")
    lines.append("")

    lines.append("## Collective Learning Monitor")
    if collective_records:
        last_snapshot = collective_summary["last_snapshot"]
        skill_count = last_snapshot.get("skills_snapshot", {}).get("skill_count")
        stats = last_snapshot.get("skills_snapshot", {}).get("stats", {})
        lines.append(f"- Iterations sampled: **{collective_summary['iterations']}**")
        lines.append(f"- Current skill count: **{skill_count}**")
        lines.append(f"- Stats: `total_errors_handled={stats.get('total_errors_handled')}` "
                     f"`auto_resolved={stats.get('auto_resolved')}`")
        lines.append(f"- Bridge status: {'✅ present' if last_snapshot.get('bridge_db_present') else '❌ missing'}")
        if collective_summary["test_failures"]:
            lines.append("- ❌ Test failures detected:")
            for fail in collective_summary["test_failures"][-5:]:
                lines.append(f"  - `{fail['script']}` status `{fail['status']}`")
        else:
            lines.append("- ✅ No test failures in the sampled window.")
    else:
        lines.append("- ⚠️ No collective monitor entries recorded.")
    lines.append("")

    lines.append("## Recommended Actions")
    if validation_summary["failed"]:
        lines.append("- Investigate failed run artifacts listed above before promoting new workflows.")
    if collective_summary["test_failures"]:
        lines.append("- Re-run failing collective-learning tests and inspect bridge connectivity.")
    if not validation_records or not collective_records:
        lines.append("- Ensure monitoring cron jobs are active (validate_runs_loop + monitor_collective_learning).")
    if not validation_summary["failed"] and not collective_summary["test_failures"]:
        lines.append("- System healthy. Consider moving to Tier-2 upgrade (WebSocket push) for higher agent count.")

    lines.append("")
    lines.append("## Source Logs")
    lines.append(f"- Validation log: `{VALIDATION_LOG}`")
    lines.append(f"- Collective monitor log: `{COLLECTIVE_LOG}`")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AI Ops Skill Mesh operational report.")
    parser.add_argument("--validation-limit", type=int, default=20, help="Number of validation entries to include.")
    parser.add_argument("--monitor-limit", type=int, default=20, help="Number of monitor entries to include.")
    parser.add_argument("--output", type=Path, default=REPORTS_DIR / "ai_ops_skill_mesh_report.md",
                        help="Output file path.")
    args = parser.parse_args()

    report = generate_report(args.validation_limit, args.monitor_limit)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")

    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
