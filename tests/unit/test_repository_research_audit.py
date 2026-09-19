from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from agents.mcp_ecosystem_coordinator import SkillRegistry
from skills.repository_research_audit import (
    collect_repository_research_inputs,
    run_repository_research_audit,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCK_FILE = str(_REPO_ROOT / "skills-lock.json")
_SCRIPT_PATH = _REPO_ROOT / "scripts/testing/run_repository_research_audit.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_repository_research_audit", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_collect_repository_research_inputs_returns_all_skill_inputs() -> None:
    audit_inputs = collect_repository_research_inputs(_REPO_ROOT)

    assert audit_inputs["harness_evidence_sources"]
    assert set(audit_inputs["skill_inputs"]) == {
        "canonical-architecture-truth",
        "persistence-and-boundary-truth",
        "engineering-risk-and-duplication-audit",
        "github-ops-and-workflow-health",
        "product-positioning-and-buyer-fit",
    }

    canonical = audit_inputs["skill_inputs"]["canonical-architecture-truth"]
    assert canonical["public_product_name"] == "UVAI"
    assert canonical["canonical_paths"]["workspace"] == "/studio"

    persistence = audit_inputs["skill_inputs"]["persistence-and-boundary-truth"]
    assert persistence["persistence_truth_map"]["video_pack_store"] == "upstash-rest"
    assert persistence["contradictions"]

    workflow = audit_inputs["skill_inputs"]["github-ops-and-workflow-health"]
    assert "ci.yml" in workflow["workflow_health_report"]["workflow_files"]
    assert audit_inputs["original_checklist"]
    item_18 = next(item for item in audit_inputs["original_checklist"] if item["item"] == 18)
    assert item_18["status"] in {"handled", "partially_handled", "still_needed"}


def test_collect_repository_research_inputs_uses_live_workflow_health_when_provided() -> None:
    live_health = {
        "source": "github-api",
        "status": "live",
        "recent_runs": [
            {"name": "CI", "conclusion": "success"},
            {"name": "verification", "conclusion": "failure"},
        ],
        "failing_workflows": ["verification.yml"],
    }

    audit_inputs = collect_repository_research_inputs(
        _REPO_ROOT,
        live_workflow_health=live_health,
    )

    workflow = audit_inputs["skill_inputs"]["github-ops-and-workflow-health"]
    assert workflow["workflow_health_report"]["live_run_health"] == live_health
    item_18 = next(item for item in audit_inputs["original_checklist"] if item["item"] == 18)
    assert item_18["status"] == "handled"
    assert "verification.yml" in item_18["handling"]


def test_collect_repository_research_inputs_fails_closed_without_authority_files(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(ValueError, match="Missing authority file"):
        collect_repository_research_inputs(repo)


@pytest.mark.asyncio
async def test_run_repository_research_audit_executes_end_to_end() -> None:
    registry = SkillRegistry(lock_file_path=_LOCK_FILE)

    result = await run_repository_research_audit(
        _REPO_ROOT,
        registry=registry,
        live_workflow_health={
            "source": "github-api",
            "status": "live",
            "recent_runs": [{"name": "CI", "conclusion": "success"}],
            "failing_workflows": [],
        },
    )

    assert result["status"] == "success", result["error"]
    assert result["execution_order"] == [
        "canonical-architecture-truth",
        "persistence-and-boundary-truth",
        "engineering-risk-and-duplication-audit",
        "github-ops-and-workflow-health",
        "product-positioning-and-buyer-fit",
        "agent-operating-harness",
    ]
    assert "canonical-vs-legacy map" in result["output"]
    assert "workflow health report" in result["output"]
    assert result["original_checklist"]


def test_audit_runner_script_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    module = _load_script_module()

    exit_code = module.main(["--repo-root", str(_REPO_ROOT)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["output"]["product-fit memo"]["positioning"]
    assert payload["original_checklist"]
