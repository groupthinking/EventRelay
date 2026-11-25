"""Regression coverage for the PR-preview discovery quality gate.

The gate must remain fail-closed when a Vercel preview is absent, while using a
small fixed GitHub API budget so a shared GitHub App quota outage is reported
as its actual cause rather than as a spurious missing-preview verdict.
"""

from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/e2e-tests.yml"


def _preview_lookup_script() -> str:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    steps = workflow["jobs"]["e2e"]["steps"]
    step = next(item for item in steps if item.get("id") == "preview")
    return step["run"]


def test_e2e_workflow_file_is_valid_yaml() -> None:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())

    assert workflow["name"] == "E2E Tests"


def test_preview_lookup_uses_a_bounded_api_budget_and_reports_rate_limits() -> None:
    script = _preview_lookup_script()

    assert "MAX_PREVIEW_LOOKUP_ATTEMPTS=12" in script
    assert 'seq 1 "$MAX_PREVIEW_LOOKUP_ATTEMPTS"' in script
    assert "PREVIEW_LOOKUP_DELAY_SECONDS=10" in script
    assert "GitHub API rate limit reached while resolving the Vercel preview" in script
    assert "No Vercel preview deployment became available" in script
