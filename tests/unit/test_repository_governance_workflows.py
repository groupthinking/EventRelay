from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
PR_GOVERNANCE = REPO_ROOT / ".github/workflows/pr-governance.yml"
RECONCILIATION = REPO_ROOT / ".github/workflows/repository-reconciliation.yml"


def _load_yaml(path: Path) -> dict:
    assert path.exists(), f"Expected workflow to exist: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def _workflow_on(workflow: dict) -> dict:
    # PyYAML follows YAML 1.1 booleans, where `on` may parse as True.
    return workflow.get("on") or workflow.get(True) or {}


def test_pr_governance_workflow_enforces_single_issue_contract() -> None:
    workflow = _load_yaml(PR_GOVERNANCE)
    workflow_on = _workflow_on(workflow)

    assert workflow["name"] == "PR Governance"
    assert workflow_on["pull_request_target"]["types"] == [
        "opened",
        "edited",
        "reopened",
        "synchronize",
        "ready_for_review",
    ]
    assert workflow["permissions"] == {
        "contents": "read",
        "issues": "read",
        "pull-requests": "read",
    }
    script = workflow["jobs"]["policy"]["steps"][0]["with"]["script"]
    assert "exactly one closing reference" in script
    assert "already has another open implementation PR" in script


def test_repository_reconciliation_is_non_destructive_report_only() -> None:
    workflow = _load_yaml(RECONCILIATION)
    workflow_on = _workflow_on(workflow)

    assert workflow["name"] == "Repository Reconciliation"
    assert "workflow_dispatch" in workflow_on
    assert workflow["permissions"] == {
        "contents": "read",
        "issues": "write",
        "pull-requests": "read",
    }
    script = workflow["jobs"]["report"]["steps"][0]["with"]["script"]
    assert "[automation] Repository drift report" in script
    assert "intentionally non-destructive" in script
    assert "issues.create" in script
    assert "issues.update" in script
