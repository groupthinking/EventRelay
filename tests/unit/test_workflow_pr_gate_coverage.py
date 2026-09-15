"""Every PR quality gate must run on every PR, whatever its base branch.

A `pull_request.branches:` allowlist filters on the PR's *base*, not its head.
Six gates carried `branches: [main]`, so a PR stacked onto another PR's branch
matched none of them and ran with no CI, no CodeQL, no security scan, no
coverage, no e2e and no dependency review. #1440 -- a security fix targeting
#1381's branch -- reached "ready for review" with zero CI runs that way.

These tests pin the trigger shape so the allowlist cannot come back.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github/workflows"

# PR-triggered quality gates. Each must fire regardless of the PR's base branch.
GATED_WORKFLOWS = [
    "ci.yml",
    "security.yml",
    "coverage.yml",
    "e2e-tests.yml",
    "codeql-analysis.yml",
    "dependency-review.yml",
]


def _triggers(filename: str) -> dict:
    path = WORKFLOWS / filename
    assert path.exists(), f"{filename} should exist"
    workflow = yaml.safe_load(path.read_text())
    # PyYAML parses the YAML 'on' key as the Python bool True.
    return workflow[True]


@pytest.mark.parametrize("filename", GATED_WORKFLOWS)
def test_gate_triggers_on_pull_request(filename: str) -> None:
    assert "pull_request" in _triggers(filename), (
        f"{filename} must run on pull_request to gate PRs at all"
    )


@pytest.mark.parametrize("filename", GATED_WORKFLOWS)
def test_gate_has_no_base_branch_allowlist(filename: str) -> None:
    """The defect itself: a base-branch allowlist lets stacked PRs skip the gate."""
    config = _triggers(filename)["pull_request"]
    # A bare `pull_request:` parses to None, which is the shape we want.
    if config is None:
        return
    assert "branches" not in config, (
        f"{filename} filters pull_request on base branch {config['branches']!r}; "
        "a PR stacked onto a non-main branch would skip this gate entirely"
    )
    assert "branches-ignore" not in config, (
        f"{filename} uses branches-ignore on pull_request, which has the same "
        "stacked-PR bypass as a branches allowlist"
    )


@pytest.mark.parametrize("filename", GATED_WORKFLOWS)
def test_push_trigger_stays_scoped_to_main(filename: str) -> None:
    """Widening the PR trigger must not widen the push trigger with it.

    Un-scoping `push` would run the full suite twice on every branch push.
    """
    triggers = _triggers(filename)
    if "push" not in triggers:
        return
    branches = triggers["push"].get("branches")
    assert branches, f"{filename} push trigger should stay pinned to a branch list"
    assert set(branches) <= {"main", "develop"}, (
        f"{filename} push trigger widened to {branches!r}"
    )


def test_e2e_job_does_not_skip_pull_requests_without_repo_var() -> None:
    """PR E2E coverage must come from the trigger, not an opt-in repo variable."""
    workflow = yaml.safe_load((WORKFLOWS / "e2e-tests.yml").read_text())
    job_if = workflow["jobs"]["e2e"].get("if", "")

    assert "vars.E2E_BASE_URL" not in job_if, (
        "e2e-tests.yml gates the PR job on E2E_BASE_URL, so PRs without that "
        "repository variable skip the E2E quality gate entirely"
    )


def test_e2e_workflow_has_configured_fallback_url() -> None:
    """PR E2E runs need a deterministic fallback URL when preview access is blocked."""
    workflow = yaml.safe_load((WORKFLOWS / "e2e-tests.yml").read_text())
    fallback_url = workflow.get("env", {}).get("E2E_FALLBACK_BASE_URL", "")
    assert fallback_url, "e2e-tests.yml should set E2E_FALLBACK_BASE_URL"
    assert "v0-uvai-jmdj10srd-garv1.vercel.app" in fallback_url


def test_e2e_preview_step_falls_back_when_bypass_secret_is_unavailable() -> None:
    """Dependabot/fork-like contexts may not receive bypass secrets; fallback must engage."""
    workflow = yaml.safe_load((WORKFLOWS / "e2e-tests.yml").read_text())
    steps = workflow["jobs"]["e2e"]["steps"]
    preview_step = next(
        step for step in steps if step.get("name") == "Extract Vercel preview URL for this PR"
    )
    script = preview_step["run"]
    assert "VERCEL_AUTOMATION_BYPASS_SECRET" in script
    assert "E2E_FALLBACK_BASE_URL" in script
    assert "BASE_URL=$E2E_FALLBACK_BASE_URL" in script
