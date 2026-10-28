"""Every PR quality gate must run on every PR, whatever its base branch.

A `pull_request.branches:` allowlist filters on the PR's *base*, not its head.
Six gates carried `branches: [main]`, so a PR stacked onto another PR's branch
matched none of them and ran with no CI, no CodeQL, no security scan, no
coverage, no e2e and no dependency review. #1440 -- a security fix targeting
#1381's branch -- reached "ready for review" with zero CI runs that way.

These tests pin the trigger shape so the allowlist cannot come back.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github/workflows"
DEPLOYMENT_INPUTS = WORKFLOWS.parent / "e2e-deployment-inputs.json"

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


def _needs_vercel_preview(*paths: str, changed_files: int | None = None) -> bool:
    manifest = json.loads(DEPLOYMENT_INPUTS.read_text())
    if changed_files is not None and len(paths) < changed_files:
        return True
    return any(
        path in manifest["files"]
        or any(path.startswith(prefix) for prefix in manifest["prefixes"])
        for path in paths
    )


@pytest.mark.parametrize(
    "path",
    [
        "apps/web/src/app/page.tsx",
        "apps/web/next.config.ts",
        "package.json",
        "package-lock.json",
        "turbo.json",
        "vercel.json",
        ".npmrc",
        ".vercelignore",
    ],
)
def test_e2e_deployment_inputs_require_a_preview(path: str) -> None:
    assert _needs_vercel_preview(path), f"{path} should require a Vercel preview"


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        "artifacts/security/audit.md",
        "docs/runbook.md",
        "scripts/security/audit_local_mcp_configs.py",
        "tests/security/test_mcp_catalog_approval.py",
        "tests/unit/test_workflow_pr_gate_coverage.py",
    ],
)
def test_non_deployment_inputs_do_not_require_a_preview(path: str) -> None:
    assert not _needs_vercel_preview(path), (
        f"{path} should not wait for a preview Vercel intentionally does not build"
    )


def test_e2e_workflow_classifies_current_and_previous_file_names() -> None:
    """Renaming a web input out of apps/ must still trigger a preview."""
    workflow = yaml.safe_load((WORKFLOWS / "e2e-tests.yml").read_text())
    steps = workflow["jobs"]["e2e"]["steps"]
    impact = next(step for step in steps if step.get("id") == "impact")
    script = impact["with"]["script"]

    assert "github.paginate(github.rest.pulls.listFiles" in script
    assert "github.rest.pulls.get" in script
    assert "files.length < pullRequest.changed_files" in script
    assert "file.filename" in script
    assert "file.previous_filename" in script
    assert "e2e-deployment-inputs.json" in script
    assert "fileListIncomplete || deploymentInputs.length > 0" in script
    assert "core.setOutput('needs_preview', String(needsPreview))" in script


def test_incomplete_pr_file_list_requires_a_preview() -> None:
    """GitHub caps PR file listings; an unseen app path must not bypass E2E."""
    assert _needs_vercel_preview("docs/first-3000-files.md", changed_files=3001)


def test_e2e_execution_steps_require_deployment_impact_on_pull_requests() -> None:
    workflow = yaml.safe_load((WORKFLOWS / "e2e-tests.yml").read_text())
    steps = workflow["jobs"]["e2e"]["steps"]
    by_name = {step.get("name"): step for step in steps}

    for name in [
        "Setup Node.js",
        "Extract Vercel preview URL for this PR",
        "Install dependencies",
        "Run E2E tests",
        "Parse test results",
        "Post PR comment with results",
    ]:
        assert "steps.impact.outputs.needs_preview" in by_name[name].get("if", ""), (
            f"{name} must not run when Vercel has no PR preview to test"
        )

    not_applicable = by_name["Record E2E as not applicable"]
    assert "steps.impact.outputs.needs_preview == 'false'" in not_applicable["if"]
