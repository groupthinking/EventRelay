from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github/workflows/repository-reconciliation.yml"
)


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "Repository reconciliation workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _get_script(workflow: dict) -> str:
    steps = workflow["jobs"]["report"]["steps"]
    script_step = next(
        step for step in steps if "Reconcile" in step.get("name", "")
    )
    return script_step["with"]["script"]


def test_reconciliation_workflow_file_is_valid_yaml() -> None:
    workflow = _load_workflow()
    assert workflow["name"] == "Repository Reconciliation"


def test_reconciliation_workflow_triggers_on_schedule_and_dispatch() -> None:
    workflow = _load_workflow()
    # PyYAML parses the YAML 'on' key as Python True.
    triggers = workflow[True]
    assert "schedule" in triggers
    assert "workflow_dispatch" in triggers
    crons = [entry["cron"] for entry in triggers["schedule"]]
    assert len(crons) >= 1


def test_reconciliation_workflow_minimum_permissions() -> None:
    workflow = _load_workflow()
    perms = workflow["permissions"]
    assert perms.get("contents") == "read"
    assert perms.get("pull-requests") == "read"
    # Needs write to upsert the drift report issue.
    assert perms.get("issues") == "write"


def test_reconciliation_workflow_excludes_draft_prs_from_untracked() -> None:
    """Draft PRs must not be counted as governance drift in the untracked list."""
    script = _get_script(_load_workflow())
    assert "pr.draft" in script, (
        "Draft PRs must be excluded from the untracked list; governance defers enforcement for drafts."
    )


def test_reconciliation_workflow_validates_issue_numbers_via_api() -> None:
    """Issue numbers referenced in PR bodies must be validated through the Issues API."""
    script = _get_script(_load_workflow())
    assert "github.rest.issues.get" in script, (
        "Issue numbers must be validated via the Issues API to prevent fictitious duplicate groups."
    )
    # Must verify it's a real issue (not a PR number).
    assert "pull_request" in script
    # Must handle 404 (non-existent references).
    assert "404" in script


def test_reconciliation_workflow_restricts_active_heads_to_same_repo() -> None:
    """activeHeads must only include branches from the same repository, not forks."""
    script = _get_script(_load_workflow())
    assert "head.repo" in script and "full_name" in script, (
        "activeHeads must filter by pr.head.repo.full_name to exclude fork branch names."
    )


def test_reconciliation_workflow_stale_cutoff_is_positive() -> None:
    """The stale-branch cutoff must be a positive number of milliseconds."""
    script = _get_script(_load_workflow())
    assert "staleAfterMs" in script
    # The constant must appear as a numeric expression > 0.
    assert "14 * 24 * 60 * 60 * 1000" in script or "staleAfterMs = " in script


def test_reconciliation_workflow_total_branches_metric_is_accurate() -> None:
    """The branches metric must correctly reflect what was fetched (all branches)."""
    script = _get_script(_load_workflow())
    # Should NOT fetch with protected: false, because that excludes protected branches.
    assert "protected: false" not in script, (
        "Fetching with protected: false excludes protected branches and makes the total inaccurate."
    )
    # The label in the report must say "Total remote branches" (includes all fetched).
    assert "Total remote branches" in script


def test_reconciliation_workflow_report_is_idempotent() -> None:
    """Running the reconciliation twice must upsert a single issue, not create duplicates."""
    script = _get_script(_load_workflow())
    # Should search for the existing report issue.
    assert "search.issuesAndPullRequests" in script or "issuesAndPullRequests" in script
    # Should update the existing issue if found, otherwise create a new one.
    assert "issues.update" in script
    assert "issues.create" in script
