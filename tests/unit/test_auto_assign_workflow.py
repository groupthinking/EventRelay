from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/auto-assign.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "Auto-assign workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def test_auto_assign_uses_rest_api_for_assignees() -> None:
    workflow = _load_workflow()
    assign_step = next(
        step
        for step in workflow["jobs"]["auto-assign"]["steps"]
        if step.get("name") == "Assign issue to repository owner"
    )
    run_script = assign_step["run"]

    assert "gh issue edit" not in run_script
    assert "gh api" in run_script
    assert "--method POST" in run_script
    assert '"/repos/${REPOSITORY}/issues/${ISSUE_NUMBER}/assignees"' in run_script
    assert '--field "assignees[]=${ASSIGNEE}"' in run_script
