from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github/workflows/dependabot-auto-merge.yml"
)


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "Dependabot automation workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def test_dependabot_workflow_uses_safe_triggers_and_permissions() -> None:
    workflow = _load_workflow()

    assert workflow["on"]["pull_request_target"]["types"] == [
        "opened",
        "reopened",
        "synchronize",
        "ready_for_review",
    ]
    assert workflow["on"]["check_suite"]["types"] == ["completed"]
    assert workflow["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
    }


def test_dependabot_workflow_approves_and_merges_without_checkout() -> None:
    workflow = _load_workflow()
    jobs = workflow["jobs"]

    approve_job = jobs["approve"]
    merge_job = jobs["merge"]

    assert "dependabot[bot]" in approve_job["if"]

    approve_steps = approve_job["steps"]
    merge_steps = merge_job["steps"]

    assert all(step.get("uses") != "actions/checkout@v4" for step in approve_steps)
    assert all(step.get("uses") != "actions/checkout@v4" for step in merge_steps)

    assert any(
        "createReview" in step.get("with", {}).get("script", "")
        for step in approve_steps
    )
    assert any(
        "dependabot[bot]" in step.get("with", {}).get("script", "")
        and "pulls.merge" in step.get("with", {}).get("script", "")
        for step in merge_steps
    )
