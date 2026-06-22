from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/auto-assign.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "Auto-assign workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def test_auto_assign_uses_rest_api_instead_of_gh_issue_edit() -> None:
    workflow = _load_workflow()
    steps = workflow["jobs"]["auto-assign"]["steps"]
    run_scripts = "\n".join(step.get("run", "") for step in steps)

    assert "gh issue edit" not in run_scripts
    assert "gh api" in run_scripts
    assert '"/repos/${REPOSITORY}/issues/${ISSUE_NUMBER}/assignees"' in run_scripts
