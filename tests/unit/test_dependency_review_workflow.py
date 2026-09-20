from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/dependency-review.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "dependency-review workflow should exist"
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    return workflow if "on" in workflow else {**workflow, "on": workflow[True]}


def test_dependency_review_submits_pr_head_snapshot_and_retries_warnings() -> None:
    workflow = _load_workflow()
    triggers = workflow["on"]
    job = workflow["jobs"]["dependency-review"]
    steps = job["steps"]

    assert triggers["push"]["branches"] == ["main"]

    checkout = next(step for step in steps if step["name"] == "Checkout code")
    assert checkout["with"]["ref"] == (
        "${{ github.event_name == 'pull_request' && "
        "github.event.pull_request.head.sha || github.sha }}"
    )

    submission = next(
        step
        for step in steps
        if step.get("uses", "").startswith(
            "advanced-security/component-detection-dependency-submission-action@"
        )
    )
    assert submission["if"] == (
        "${{ github.event_name == 'push' || "
        "github.event.pull_request.head.repo.full_name == github.repository }}"
    )
    assert submission["with"]["snapshot-sha"] == (
        "${{ github.event_name == 'pull_request' && "
        "github.event.pull_request.head.sha || github.sha }}"
    )
    assert submission["with"]["snapshot-ref"] == (
        "${{ github.event_name == 'pull_request' && "
        "format('refs/heads/{0}', github.event.pull_request.head.ref) || github.ref }}"
    )

    review = next(step for step in steps if step["name"] == "Dependency Review")
    assert review["if"] == "${{ github.event_name == 'pull_request' }}"
    assert review["with"]["retry-on-snapshot-warnings"] is True
    assert review["with"]["retry-on-snapshot-warnings-timeout"] == 300
