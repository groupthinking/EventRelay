from __future__ import annotations

from pathlib import Path

import pytest

from agents.mcp_ecosystem_coordinator import SkillRegistry

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCK_FILE = str(_REPO_ROOT / "skills-lock.json")
_SOURCE = "groupthinking/EventRelay"

_EXPECTED_REPOSITORY_SKILLS = {
    "canonical-architecture-truth",
    "persistence-and-boundary-truth",
    "engineering-risk-and-duplication-audit",
    "github-ops-and-workflow-health",
    "product-positioning-and-buyer-fit",
    "agent-operating-harness",
}


@pytest.fixture
def registry() -> SkillRegistry:
    return SkillRegistry(lock_file_path=_LOCK_FILE)


def test_registry_lists_repository_runtime_skills_by_source(
    registry: SkillRegistry,
) -> None:
    skills = registry.list_skills(source=_SOURCE)
    assert {skill["id"] for skill in skills} == _EXPECTED_REPOSITORY_SKILLS


@pytest.mark.asyncio
async def test_canonical_architecture_truth_requires_evidence_sources(
    registry: SkillRegistry,
) -> None:
    result = await registry.invoke_skill(
        "canonical-architecture-truth",
        {
            "canonical_paths": {"public_entrypoint": "/", "workspace": "/studio"},
            "legacy_surfaces": ["/dashboard"],
        },
    )

    assert result["status"] == "error"
    assert "evidence_sources" in (result["error"] or "")


@pytest.mark.asyncio
async def test_canonical_architecture_truth_returns_evidence_backed_map(
    registry: SkillRegistry,
) -> None:
    result = await registry.invoke_skill(
        "canonical-architecture-truth",
        {
            "evidence_sources": [
                "AGENTS.md:8-14",
                "README.md:1-40",
                "docs/REPO_MAP.md:1-80",
            ],
            "canonical_paths": {"public_entrypoint": "/", "workspace": "/studio"},
            "legacy_surfaces": ["/dashboard"],
            "public_product_name": "UVAI",
            "internal_runtime_name": "EventRelay",
            "deployment_truth": {"production_surface": "apps/web"},
            "runtime_boundaries": ["apps/web", "src/youtube_extension"],
        },
    )

    assert result["status"] == "success", result["error"]
    output = result["output"]
    assert output["evidence_sources"] == [
        "AGENTS.md:8-14",
        "README.md:1-40",
        "docs/REPO_MAP.md:1-80",
    ]
    assert output["canonical_vs_legacy_map"]["canonical_paths"]["workspace"] == "/studio"
    assert output["canonical_vs_legacy_map"]["public_product_name"] == "UVAI"


@pytest.mark.asyncio
async def test_agent_operating_harness_requires_all_skill_outputs(
    registry: SkillRegistry,
) -> None:
    result = await registry.invoke_skill(
        "agent-operating-harness",
        {
            "evidence_sources": ["tests/unit/test_runtime_repository_skills.py:1-80"],
            "skill_outputs": {
                "canonical-architecture-truth": {
                    "evidence_sources": ["AGENTS.md:8-14"],
                    "canonical_vs_legacy_map": {},
                }
            },
        },
    )

    assert result["status"] == "error"
    assert "missing skill outputs" in (result["error"] or "")


@pytest.mark.asyncio
async def test_agent_operating_harness_aggregates_runtime_skill_outputs(
    registry: SkillRegistry,
) -> None:
    result = await registry.invoke_skill(
        "agent-operating-harness",
        {
            "evidence_sources": ["docs/MASTER_ROADMAP.md:1-40"],
            "skill_outputs": {
                "canonical-architecture-truth": {
                    "evidence_sources": ["AGENTS.md:8-14"],
                    "canonical_vs_legacy_map": {"canonical_paths": {"workspace": "/studio"}},
                    "recommended_actions": ["keep /studio canonical"],
                },
                "persistence-and-boundary-truth": {
                    "evidence_sources": ["apps/web/src/lib/video-pack-store.ts:1-40"],
                    "persistence_truth_map": {"video_pack_store": "upstash-rest"},
                    "security_boundary_map": {"public_routes": ["/"]},
                    "recommended_actions": ["verify pack writes remain on Upstash REST"],
                },
                "engineering-risk-and-duplication-audit": {
                    "evidence_sources": ["docs/REPO_MAP.md:1-80"],
                    "risk_register": [{"severity": "high", "title": "Doc drift"}],
                    "recommended_actions": ["retire duplicate docs"],
                },
                "github-ops-and-workflow-health": {
                    "evidence_sources": [".github/workflows/ci.yml:1-40"],
                    "workflow_health_report": {"failing_workflows": ["verification.yml"]},
                    "recommended_actions": ["audit failing legacy workflows"],
                },
                "product-positioning-and-buyer-fit": {
                    "evidence_sources": ["README.md:1-40"],
                    "product_fit_memo": {"positioning": "ship from video evidence"},
                    "recommended_actions": ["keep public UVAI positioning aligned"],
                },
            },
        },
    )

    assert result["status"] == "success", result["error"]
    output = result["output"]
    assert output["execution_order"] == [
        "canonical-architecture-truth",
        "persistence-and-boundary-truth",
        "engineering-risk-and-duplication-audit",
        "github-ops-and-workflow-health",
        "product-positioning-and-buyer-fit",
    ]
    assert output["canonical-vs-legacy map"]["canonical_paths"]["workspace"] == "/studio"
    assert output["persistence truth map"]["video_pack_store"] == "upstash-rest"
    assert output["workflow health report"]["failing_workflows"] == ["verification.yml"]
    assert output["product-fit memo"]["positioning"] == "ship from video evidence"
    assert len(output["remediation sequence with verification gates"]) == 5
