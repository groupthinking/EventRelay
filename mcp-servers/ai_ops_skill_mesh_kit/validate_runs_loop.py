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
from typing import List, Optional, Tuple


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


REPO_ROOT = _resolve_repo_root()
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from shared.run_validation import RUNS_ROOT as DEFAULT_RUNS_ROOT  # type: ignore  # noqa: E402
from shared.run_validation import VALIDATOR_ROOT  # type: ignore  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Continuous validation loop for workflow run artifacts.")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=None,
        help="Directory containing run artifact folders. Defaults to shared RUNS_ROOT.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=300.0,
        help="Seconds between validation passes when --watch is set (default: 300).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously validate runs on the provided interval.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Optional JSONL log file for validation results. Defaults to <runs_root>/validation_log.jsonl.",
    )
    parser.add_argument(
        "--include-warnings",
        action="store_true",
        help="Treat warnings as actionable findings in the summary output.",
    )
    return parser.parse_args()


def _list_runs(runs_root: Path) -> List[Path]:
    if not runs_root.exists():
        return []
    return sorted([p for p in runs_root.iterdir() if p.is_dir()])


def _run_validator(run_dir: Path) -> Tuple[int, str]:
    command = ["npm", "run", "validate:run", "--", str(run_dir)]
    result = subprocess.run(
        command,
        cwd=VALIDATOR_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "NODE_ENV": os.environ.get("NODE_ENV", "production")},
    )
    output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    return result.returncode, output.strip()


def _write_log_entry(log_path: Path, record: dict[str, object]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def _summarise_warnings(output: str) -> List[str]:
    warnings: List[str] = []
    for line in output.splitlines():
        if "⚠️" in line or "warning" in line.lower():
            warnings.append(line.strip())
    return warnings


def _validate_pass(runs_root: Path, log_path: Optional[Path], include_warnings: bool) -> None:
    runs = _list_runs(runs_root)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not runs:
        print(f"[{timestamp}] No runs found under {runs_root}")
        return

    total = len(runs)
    successes = 0
    failures: List[Tuple[Path, str]] = []
    flagged: List[Tuple[Path, List[str]]] = []

    for run_dir in runs:
        code, output = _run_validator(run_dir)
        warnings = _summarise_warnings(output)
        status = "passed" if code == 0 else "failed"
        print(f"\n[{timestamp}] {run_dir.name} -> {status.upper()}")
        print(output)

        record = {
            "run": run_dir.name,
            "path": str(run_dir),
            "status": status,
            "warnings": warnings,
            "timestamp": timestamp,
        }
        if log_path:
            _write_log_entry(log_path, record)

        if code == 0:
            successes += 1
            if include_warnings and warnings:
                flagged.append((run_dir, warnings))
        else:
            failures.append((run_dir, output))

    summary = f"[{timestamp}] Validation summary: {successes}/{total} runs passed."
    print("\n" + summary)

    if failures:
        print("Failures:")
        for run_dir, output in failures:
            print(f"- {run_dir.name}: see details above.")

    if include_warnings and flagged:
        print("Runs with warnings:")
        for run_dir, warnings in flagged:
            print(f"- {run_dir.name}:")
            for warning in warnings:
                print(f"    {warning}")


def main() -> None:
    args = _parse_args()
    runs_root = args.runs_root.resolve() if args.runs_root else DEFAULT_RUNS_ROOT
    log_path = args.log_file or (runs_root / "validation_log.jsonl")

    try:
        while True:
            _validate_pass(runs_root, log_path, include_warnings=args.include_warnings)
            if not args.watch:
                break
            time.sleep(max(args.interval, 1.0))
    except KeyboardInterrupt:
        print("\nValidation loop interrupted by user.")


if __name__ == "__main__":
    main()
