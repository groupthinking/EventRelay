#!/usr/bin/env python3
"""Run the autonomous repository research audit and print JSON output."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from agents.mcp_ecosystem_coordinator import SkillRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="Repository root to audit",
    )
    return parser


async def _run(repo_root: Path) -> dict:
    registry = SkillRegistry(lock_file_path=str(repo_root / "skills-lock.json"))
    return await registry.run_repository_research_audit(repo_root)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = asyncio.run(_run(args.repo_root))
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
