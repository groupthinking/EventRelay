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
        step for step in steps if "Validate delivery contract" in step.get("name", "")
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
    assert "ready_for_review" in types


def test_governance_workflow_minimum_permissions() -> None:
    workflow = _load_workflow()
    perms = workflow["permissions"]
    # Must NOT request write permissions to contents or pull-requests.
    assert perms.get("contents") == "read"
    assert perms.get("pull-requests") == "read"
    assert perms.get("issues") == "read"


def test_governance_workflow_draft_bypass_present() -> None:
    """Draft PRs should be bypassed; enforcement begins on ready_for_review."""
    script = _get_script(_load_workflow())
    assert "pr.draft" in script
    assert "Draft PR" in script or "draft" in script.lower()


def test_governance_workflow_detects_empty_placeholder_content() -> None:
    """Sections must be checked for empty/placeholder content, not just heading presence."""
    script = _get_script(_load_workflow())
    # The script should strip HTML comments and trim before checking emptiness.
    assert "getSectionContent" in script or "replace" in script
    assert "<!--" in script or "html" in script.lower() or "trim()" in script
    # Should NOT rely solely on body.includes() for non-empty validation.
    assert "content.length" in script or "content ===" in script


def test_governance_workflow_validates_issue_via_api() -> None:
    """The canonical issue number must be validated through the Issues API."""
    script = _get_script(_load_workflow())
    assert "github.rest.issues.get" in script
    # Must check it's not a PR (issues have no pull_request field).
    assert "pull_request" in script
    # Must check the issue is open.
    assert "state" in script and "open" in script
    # Must handle 404 (non-existent issue).
    assert "404" in script


def test_governance_workflow_competing_pr_check_present() -> None:
    """Should detect and fail on competing open PRs for the same canonical issue."""
    script = _get_script(_load_workflow())
    assert "competing" in script
    assert "github.paginate" in script
    assert "github.rest.pulls.list" in script


def test_governance_workflow_competing_check_only_after_valid_issue() -> None:
    """Competing PR search should only run after the canonical issue passes validation."""
    script = _get_script(_load_workflow())
    # The issue.get call must appear before the pulls.list paginate call.
    issues_get_pos = script.find("github.rest.issues.get")
    pulls_list_pos = script.find("github.rest.pulls.list")
    assert issues_get_pos != -1
    assert pulls_list_pos != -1
    assert issues_get_pos < pulls_list_pos
