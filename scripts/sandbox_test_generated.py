#!/usr/bin/env python3
"""Minimal sandbox runner for generated project trees (Phase 4 gate)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_pytest(target: Path, timeout: int) -> int:
    if not target.exists():
        print(f"SKIP: {target} does not exist")
        return 0
    cmd = [sys.executable, "-m", "pytest", str(target), "-q", "--tb=short"]
    try:
        completed = subprocess.run(cmd, timeout=timeout, check=False)
        return completed.returncode
    except subprocess.TimeoutExpired:
        print(f"FAIL: pytest timed out after {timeout}s")
        return 124


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sandbox tests on a generated project")
    parser.add_argument("project_dir", type=Path, help="Generated project root")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    tests_dir = args.project_dir / "tests"
    if tests_dir.is_dir():
        return run_pytest(tests_dir, args.timeout)

    single = args.project_dir / "test_generated.py"
    if single.is_file():
        return run_pytest(single, args.timeout)

    print("SKIP: no tests/ or test_generated.py — nothing to execute")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
