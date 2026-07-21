from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/pr-governance.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "PR governance workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _get_script(workflow: dict) -> str:
    steps = workflow["jobs"]["policy"]["steps"]
    script_step = next(
        step
        for step in steps
        if "Validate delivery contract" in step.get("name", "")
    )
    return script_step["with"]["script"]


def test_governance_workflow_file_is_valid_yaml() -> None:
    workflow = _load_workflow()
    assert workflow["name"] == "PR Governance"


def test_governance_workflow_triggers_on_pull_request_target() -> None:
    workflow = _load_workflow()
    # PyYAML parses the YAML 'on' key as Python True.
    triggers = workflow[True]
    assert "pull_request_target" in triggers
    types = triggers["pull_request_target"]["types"]
    assert "opened" in types
    assert "synchronize" in types
    assert "ready_for_review" in types


def test_governance_workflow_uses_minimum_permissions() -> None:
    workflow = _load_workflow()
    perms = workflow["permissions"]
    assert perms.get("checks") == "write"
    assert perms.get("contents") == "read"
    assert perms.get("pull-requests") == "read"
    assert perms.get("issues") == "read"
    assert set(perms) == {"checks", "contents", "issues", "pull-requests"}


def test_governance_workflow_publishes_exact_head_check() -> None:
    script = _get_script(_load_workflow())
    assert 'name: "PR Governance"' in script
    assert "github.rest.checks.create" in script
    assert "head_sha: pr.head.sha" in script
    assert 'status: "completed"' in script


def test_governance_workflow_draft_bypass_is_head_bound() -> None:
    script = _get_script(_load_workflow())
    assert "pr.draft" in script
    assert '"neutral"' in script
    assert "Governance deferred for draft PR" in script
    assert "pr.head.sha" in script


def test_governance_workflow_rejects_default_placeholders() -> None:
    script = _get_script(_load_workflow())
    assert "placeholderPatterns" in script
    assert "hasMeaningfulContent" in script
    assert "Describe the user or operational result" in script
    assert "Risk level:" in script
    assert "Focused tests" in script
    assert "meaningfulLines.length > 0" in script
    assert r'replace(/<!--[\s\S]*?-->/g, "").trim()' in script
    assert r'replace(/<!--[\\s\\S]*?-->/g, "").trim()' not in script


def test_governance_workflow_validates_issue_via_api() -> None:
    script = _get_script(_load_workflow())
    assert "github.rest.issues.get" in script
    assert "pull_request" in script
    assert "issue.state" in script
    assert "404" in script


def test_governance_workflow_detects_competing_prs() -> None:
    script = _get_script(_load_workflow())
    assert "github.paginate" in script
    assert "github.rest.pulls.list" in script
    assert "competing" in script
    assert "another open implementation PR" in script


def test_governance_workflow_checks_issue_before_competitors() -> None:
    script = _get_script(_load_workflow())
    assert script.index("github.rest.issues.get") < script.index(
        "github.rest.pulls.list"
    )
