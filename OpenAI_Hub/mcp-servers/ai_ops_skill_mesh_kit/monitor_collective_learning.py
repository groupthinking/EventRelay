#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List


ROOT = Path(__file__).resolve().parents[1]
EVENTRELAY_ROOT = ROOT / "OpenAI_Hub" / "projects" / "EventRelay"
MONITOR_LOG = EVENTRELAY_ROOT / "collective_learning_monitor_log.jsonl"
SKILLS_DB = EVENTRELAY_ROOT / "skills_database.json"
MANIFEST = EVENTRELAY_ROOT / "COLLECTIVE_LEARNING_MANIFEST.md"
BRIDGE_DB = Path.home() / ".claude" / "claude_bridge_enhanced.db"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run_test(script_name: str) -> Dict[str, Any]:
    script_path = EVENTRELAY_ROOT / script_name
    result: Dict[str, Any] = {
        "script": script_name,
        "status": "skipped",
        "stdout": "",
        "stderr": "",
        "returncode": None,
    }

    if not script_path.exists():
        result["status"] = "missing"
        result["stderr"] = f"{script_name} not found."
        return result

    try:
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=EVENTRELAY_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONPATH": str(EVENTRELAY_ROOT)},
        )
        result["returncode"] = completed.returncode
        result["stdout"] = completed.stdout.strip()
        result["stderr"] = completed.stderr.strip()
        result["status"] = "passed" if completed.returncode == 0 else "failed"
    except Exception as exc:
        result["status"] = "error"
        result["stderr"] = str(exc)

    return result


def _read_skills_snapshot() -> Dict[str, Any]:
    if not SKILLS_DB.exists():
        return {}
    try:
        data = json.loads(SKILLS_DB.read_text())
        return {
            "skill_count": len(data.get("skills", [])),
            "stats": data.get("stats", {}),
        }
    except json.JSONDecodeError:
        return {"error": "invalid_json"}


def _write_log(entry: Dict[str, Any]) -> None:
    MONITOR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with MONITOR_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def _summarise_tests(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {"total": len(results), "passed": 0, "failed": 0, "errors": 0, "missing": 0}
    for res in results:
        status = res["status"]
        if status == "passed":
            summary["passed"] += 1
        elif status == "failed":
            summary["failed"] += 1
        elif status == "error":
            summary["errors"] += 1
        elif status == "missing":
            summary["missing"] += 1
    return summary


def monitor(run_tests: bool = True, record_manifest: bool = False) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "timestamp": _timestamp(),
        "bridge_db_present": BRIDGE_DB.exists(),
        "skills_snapshot": _read_skills_snapshot(),
        "tests": [],
    }

    if run_tests:
        tests_to_run = [
            "test_skill_connector.py",
            "test_multi_agent_learning.py",
        ]
        for test_script in tests_to_run:
            record["tests"].append(_run_test(test_script))

    record["tests_summary"] = _summarise_tests(record["tests"])

    if record_manifest and MANIFEST.exists():
        record["manifest_size_bytes"] = MANIFEST.stat().st_size

    _write_log(record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor collective learning system health.")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running Python test scripts, only capture artifacts snapshot.",
    )
    parser.add_argument(
        "--show-output",
        action="store_true",
        help="Print test output to stdout for immediate inspection.",
    )
    parser.add_argument(
        "--include-manifest",
        action="store_true",
        help="Record manifest file size in log entry.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously monitor on the given interval (default 300s).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=300.0,
        help="Seconds between checks when --watch is set (default: 300).",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Number of iterations to run in watch mode (default: infinite).",
    )
    args = parser.parse_args()

    try:
        iteration = 0
        while True:
            iteration += 1
            record = monitor(run_tests=not args.skip_tests, record_manifest=args.include_manifest)

            print(json.dumps(record, indent=2))

            if args.show_output:
                for test in record["tests"]:
                    print("\n=== {} ===".format(test["script"]))
                    if test["stdout"]:
                        print(test["stdout"])
                    if test["stderr"]:
                        print("--- stderr ---")
                        print(test["stderr"])

            if not args.watch:
                break

            if args.iterations and iteration >= args.iterations:
                break

            time.sleep(max(args.interval, 1.0))
    except KeyboardInterrupt:
        print("\nMonitor interrupted by user.")


if __name__ == "__main__":
    main()
