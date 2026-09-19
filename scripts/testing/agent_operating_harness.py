#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_SKILLS: dict[str, dict[str, str]] = {
    "canonical-architecture-truth": {
        "doc_path": ".claude/skills/canonical-architecture-truth/SKILL.md",
        "runtime_path": "src/skills/canonical_architecture_truth/main.py",
        "class_name": "CanonicalArchitectureTruthSkill",
    },
    "persistence-and-boundary-truth": {
        "doc_path": ".claude/skills/persistence-and-boundary-truth/SKILL.md",
        "runtime_path": "src/skills/persistence_and_boundary_truth/main.py",
        "class_name": "PersistenceAndBoundaryTruthSkill",
    },
    "engineering-risk-and-duplication-audit": {
        "doc_path": ".claude/skills/engineering-risk-and-duplication-audit/SKILL.md",
        "runtime_path": "src/skills/engineering_risk_and_duplication_audit/main.py",
        "class_name": "EngineeringRiskAndDuplicationAuditSkill",
    },
    "github-ops-and-workflow-health": {
        "doc_path": ".claude/skills/github-ops-and-workflow-health/SKILL.md",
        "runtime_path": "src/skills/github_ops_and_workflow_health/main.py",
        "class_name": "GitHubOpsAndWorkflowHealthSkill",
    },
    "product-positioning-and-buyer-fit": {
        "doc_path": ".claude/skills/product-positioning-and-buyer-fit/SKILL.md",
        "runtime_path": "src/skills/product_positioning_and_buyer_fit/main.py",
        "class_name": "ProductPositioningAndBuyerFitSkill",
    },
    "agent-operating-harness": {
        "doc_path": ".claude/skills/agent-operating-harness/SKILL.md",
        "runtime_path": "src/skills/agent_operating_harness/main.py",
        "class_name": "AgentOperatingHarnessSkill",
    },
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

    for skill_id, paths in REQUIRED_SKILLS.items():
        meta = skills.get(skill_id)
        if meta is None:
            continue
        expected_meta = (
            meta.get("source") == "groupthinking/EventRelay"
            and meta.get("sourceType") == "local"
            and meta.get("skillPath") == paths["runtime_path"]
            and meta.get("className") == paths["class_name"]
            and meta.get("version") == "1.0.0"
            and meta.get("triggers") == []
            and meta.get("dependencies") == []
            and meta.get("subscribed_triggers") == []
        )
        checks.append(
            {
                "id": f"skills-lock:{skill_id}",
                "status": "SUCCESS" if expected_meta else "FAILURE",
            }
        )

        doc_path = repo_root / paths["doc_path"]
        runtime_path = repo_root / paths["runtime_path"]
        if not doc_path.is_file():
            checks.append(
                {"id": f"missing skill doc: {paths['doc_path']}", "status": "FAILURE"}
            )
            continue
        if not runtime_path.is_file():
            checks.append(
                {"id": f"missing runtime skill: {paths['runtime_path']}", "status": "FAILURE"}
            )
            continue

        text = doc_path.read_text(encoding="utf-8")
        missing_sections = [section for section in REQUIRED_SECTIONS if section not in text]
        checks.append(
            {
                "id": f"skill sections:{skill_id}",
                "status": "SUCCESS" if not missing_sections else "FAILURE",
            }
        )
        runtime_text = runtime_path.read_text(encoding="utf-8")
        checks.append(
            {
                "id": f"runtime skill:{skill_id}",
                "status": "SUCCESS" if "evidence_sources" in runtime_text else "FAILURE",
            }
        )

    harness_path = repo_root / REQUIRED_SKILLS["agent-operating-harness"]["doc_path"]
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
