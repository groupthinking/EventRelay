#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_SKILLS: dict[str, str] = {
    "canonical-architecture-truth": ".claude/skills/canonical-architecture-truth/SKILL.md",
    "persistence-and-boundary-truth": ".claude/skills/persistence-and-boundary-truth/SKILL.md",
    "engineering-risk-and-duplication-audit": ".claude/skills/engineering-risk-and-duplication-audit/SKILL.md",
    "github-ops-and-workflow-health": ".claude/skills/github-ops-and-workflow-health/SKILL.md",
    "product-positioning-and-buyer-fit": ".claude/skills/product-positioning-and-buyer-fit/SKILL.md",
    "agent-operating-harness": ".claude/skills/agent-operating-harness/SKILL.md",
}

REQUIRED_SECTIONS = (
    "## Purpose",
    "## When to Use",
    "## Required Evidence",
    "## Outputs",
)

REQUIRED_OUTPUTS = (
    "canonical-vs-legacy map",
    "persistence truth map",
    "security boundary map",
    "risk register",
    "workflow health report",
    "product-fit memo",
    "remediation sequence with verification gates",
)


def summarize_checks(
    checks: list[dict[str, Any]],
    *,
    required: bool,
    exit_code: int,
) -> dict[str, Any]:
    counts = Counter(str(check.get("status", "UNKNOWN")) for check in checks)
    blocking = [
        f"{check.get('id', '<unknown>')}:{check.get('status', 'UNKNOWN')}"
        for check in checks
        if required and str(check.get("status")) in {"FAILURE", "WARNING"}
    ]
    if required and exit_code != 0:
        blocking.append(f"runner-exit-code:{exit_code}")
    return {"ok": not blocking, "counts": dict(counts), "blocking": blocking}


def validate_repository_skill_bundle(repo_root: Path) -> dict[str, Any]:
    lock_path = repo_root / "skills-lock.json"
    skills_lock = json.loads(lock_path.read_text(encoding="utf-8"))
    skills = skills_lock.get("skills", {})
    checks: list[dict[str, Any]] = []

    missing_skill_ids = sorted(set(REQUIRED_SKILLS) - set(skills))
    if missing_skill_ids:
        checks.append(
            {
                "id": "missing required skill registrations: "
                + ", ".join(missing_skill_ids),
                "status": "FAILURE",
            }
        )
    else:
        checks.append({"id": "required skill registrations", "status": "SUCCESS"})

    for skill_id, rel_path in REQUIRED_SKILLS.items():
        meta = skills.get(skill_id)
        if meta is None:
            continue
        expected_meta = (
            meta.get("source") == "groupthinking/EventRelay"
            and meta.get("sourceType") == "local"
            and meta.get("skillPath") == rel_path
            and meta.get("subscribed_triggers") == []
        )
        checks.append(
            {
                "id": f"skills-lock:{skill_id}",
                "status": "SUCCESS" if expected_meta else "FAILURE",
            }
        )

        skill_path = repo_root / rel_path
        if not skill_path.is_file():
            checks.append({"id": f"missing skill doc: {rel_path}", "status": "FAILURE"})
            continue

        text = skill_path.read_text(encoding="utf-8")
        missing_sections = [section for section in REQUIRED_SECTIONS if section not in text]
        checks.append(
            {
                "id": f"skill sections:{skill_id}",
                "status": "SUCCESS" if not missing_sections else "FAILURE",
            }
        )

    harness_path = repo_root / REQUIRED_SKILLS["agent-operating-harness"]
    if harness_path.is_file():
        harness_text = harness_path.read_text(encoding="utf-8")
        ordered = all(name in harness_text for name in REQUIRED_SKILLS if name != "agent-operating-harness")
        checks.append(
            {
                "id": "harness execution order",
                "status": "SUCCESS" if ("## Execution Order" in harness_text and ordered) else "FAILURE",
            }
        )

        lower_harness_text = harness_text.lower()
        output_checks = all(item in lower_harness_text for item in REQUIRED_OUTPUTS)
        checks.append(
            {
                "id": "harness outputs",
                "status": "SUCCESS" if output_checks else "FAILURE",
            }
        )

    exit_code = 0 if all(check["status"] == "SUCCESS" for check in checks) else 1
    summary = summarize_checks(checks, required=True, exit_code=exit_code)
    summary["checks"] = checks
    summary["required_skill_count"] = len(REQUIRED_SKILLS)
    summary["outputs"] = list(REQUIRED_OUTPUTS)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate repository research skills and harness")
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="Repository root containing skills-lock.json",
    )
    args = parser.parse_args()

    summary = validate_repository_skill_bundle(args.repo_root)
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
