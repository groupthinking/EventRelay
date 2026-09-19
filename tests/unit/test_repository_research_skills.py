from __future__ import annotations

import json
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCK_PATH = _REPO_ROOT / "skills-lock.json"

_RESEARCH_SKILLS = {
    "canonical-architecture-truth": ".claude/skills/canonical-architecture-truth/SKILL.md",
    "persistence-and-boundary-truth": ".claude/skills/persistence-and-boundary-truth/SKILL.md",
    "engineering-risk-and-duplication-audit": ".claude/skills/engineering-risk-and-duplication-audit/SKILL.md",
    "github-ops-and-workflow-health": ".claude/skills/github-ops-and-workflow-health/SKILL.md",
    "product-positioning-and-buyer-fit": ".claude/skills/product-positioning-and-buyer-fit/SKILL.md",
    "agent-operating-harness": ".claude/skills/agent-operating-harness/SKILL.md",
}


def _lock_data() -> dict:
    return json.loads(_LOCK_PATH.read_text(encoding="utf-8"))


def test_skills_lock_registers_repository_research_skills() -> None:
    data = _lock_data()
    skills = data["skills"]

    for skill_id, rel_path in _RESEARCH_SKILLS.items():
        assert skill_id in skills, f"{skill_id} missing from skills-lock.json"
        meta = skills[skill_id]
        assert meta["source"] == "groupthinking/EventRelay"
        assert meta["sourceType"] == "local"
        assert meta["skillPath"] == rel_path
        assert meta["subscribed_triggers"] == []


def test_repository_research_skill_docs_exist() -> None:
    for rel_path in _RESEARCH_SKILLS.values():
        assert (_REPO_ROOT / rel_path).is_file(), f"missing skill doc: {rel_path}"


def test_repository_research_skill_docs_define_purpose_and_evidence() -> None:
    for skill_id, rel_path in _RESEARCH_SKILLS.items():
        text = (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "## Purpose" in text, f"{skill_id} missing Purpose section"
        assert "## When to Use" in text, f"{skill_id} missing When to Use section"
        assert "## Required Evidence" in text, f"{skill_id} missing Required Evidence section"
        assert "## Outputs" in text, f"{skill_id} missing Outputs section"


def test_agent_operating_harness_skill_defines_execution_order() -> None:
    text = (
        _REPO_ROOT / _RESEARCH_SKILLS["agent-operating-harness"]
    ).read_text(encoding="utf-8")

    assert "## Execution Order" in text
    assert "canonical-architecture-truth" in text
    assert "persistence-and-boundary-truth" in text
    assert "engineering-risk-and-duplication-audit" in text
    assert "github-ops-and-workflow-health" in text
    assert "product-positioning-and-buyer-fit" in text
