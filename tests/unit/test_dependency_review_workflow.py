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
    assert checkout["with"]["fetch-depth"] == 0

    detection = next(
        step for step in steps if step["name"] == "Detect dependency manifest changes"
    )
    assert detection["id"] == "dependency-changes"
    assert detection["if"] == "${{ github.event_name == 'pull_request' }}"
    detection_script = detection["run"]
    for protected_input in (
        "uv.lock",
        "pyproject.toml",
        "requirements",
        "package-lock.json",
        "package.json",
        "Dockerfile",
        ".github/workflows/dependency-review.yml",
    ):
        assert protected_input in detection_script
    assert '"git", "diff", "--name-only", "-z", base, head' in detection_script

    submission = next(
        step
        for step in steps
        if step.get("uses", "").startswith(
            "advanced-security/component-detection-dependency-submission-action@"
        )
    )
    assert "github.event_name == 'push'" in submission["if"]
    assert "steps.dependency-changes.outputs.changed == 'true'" in submission["if"]
    assert submission["with"]["snapshot-sha"] == (
        "${{ github.event_name == 'pull_request' && "
        "github.event.pull_request.head.sha || github.sha }}"
    )
    assert submission["with"]["snapshot-ref"] == (
        "${{ github.event_name == 'pull_request' && "
        "format('refs/heads/{0}', github.event.pull_request.head.ref) || github.ref }}"
    )

    review = next(step for step in steps if step["name"] == "Dependency Review")
    assert "github.event_name == 'pull_request'" in review["if"]
    assert "steps.dependency-changes.outputs.changed == 'true'" in review["if"]
    assert review["with"]["retry-on-snapshot-warnings"] is True
    assert review["with"]["retry-on-snapshot-warnings-timeout"] == 300

    no_delta = next(step for step in steps if step["name"] == "Record no dependency delta")
    assert "steps.dependency-changes.outputs.changed == 'false'" in no_delta["if"]
