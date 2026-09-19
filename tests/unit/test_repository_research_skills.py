from __future__ import annotations

import json
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCK_PATH = _REPO_ROOT / "skills-lock.json"

_RESEARCH_SKILLS = {
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


def _lock_data() -> dict:
    return json.loads(_LOCK_PATH.read_text(encoding="utf-8"))


def test_skills_lock_registers_repository_research_skills() -> None:
    data = _lock_data()
    skills = data["skills"]

    for skill_id, metadata in _RESEARCH_SKILLS.items():
        assert skill_id in skills, f"{skill_id} missing from skills-lock.json"
        meta = skills[skill_id]
        assert meta["source"] == "groupthinking/EventRelay"
        assert meta["sourceType"] == "local"
        assert meta["skillPath"] == metadata["runtime_path"]
        assert meta["className"] == metadata["class_name"]
        assert meta["version"] == "1.0.0"
        assert meta["triggers"] == []
        assert meta["dependencies"] == []
        assert meta["subscribed_triggers"] == []


def test_repository_research_skill_docs_exist() -> None:
    for metadata in _RESEARCH_SKILLS.values():
        rel_path = metadata["doc_path"]
        assert (_REPO_ROOT / rel_path).is_file(), f"missing skill doc: {rel_path}"


def test_repository_research_skill_docs_define_purpose_and_evidence() -> None:
    for skill_id, metadata in _RESEARCH_SKILLS.items():
        rel_path = metadata["doc_path"]
        text = (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "## Purpose" in text, f"{skill_id} missing Purpose section"
        assert "## When to Use" in text, f"{skill_id} missing When to Use section"
        assert "## Required Evidence" in text, f"{skill_id} missing Required Evidence section"
        assert "## Outputs" in text, f"{skill_id} missing Outputs section"


def test_repository_research_runtime_skill_modules_exist() -> None:
    for metadata in _RESEARCH_SKILLS.values():
        rel_path = metadata["runtime_path"]
        assert (_REPO_ROOT / rel_path).is_file(), f"missing runtime skill: {rel_path}"


def test_agent_operating_harness_skill_defines_execution_order() -> None:
    text = (
        _REPO_ROOT / _RESEARCH_SKILLS["agent-operating-harness"]["doc_path"]
    ).read_text(encoding="utf-8")

    assert "## Execution Order" in text
    assert "canonical-architecture-truth" in text
    assert "persistence-and-boundary-truth" in text
    assert "engineering-risk-and-duplication-audit" in text
    assert "github-ops-and-workflow-health" in text
    assert "product-positioning-and-buyer-fit" in text
