"""Regression tests for repository-owned GitHub Actions invariants."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

# GitHub documents this closed set for GITHUB_TOKEN workflow/job permissions.
SUPPORTED_PERMISSIONS = {
    "actions",
    "artifact-metadata",
    "attestations",
    "checks",
    "code-quality",
    "contents",
    "deployments",
    "discussions",
    "id-token",
    "issues",
    "models",
    "packages",
    "pages",
    "pull-requests",
    "security-events",
    "statuses",
    "vulnerability-alerts",
}


def _workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))


def test_workflows_only_request_supported_github_token_permissions() -> None:
    invalid: dict[str, set[str]] = {}

    for path in _workflow_paths():
        workflow = _workflow(path.name)
        scopes = [workflow.get("permissions")]
        scopes.extend(job.get("permissions") for job in workflow.get("jobs", {}).values())

        bad: set[str] = set()
        for scope in scopes:
            if scope is None:
                continue
            if isinstance(scope, str):
                if scope not in {"read-all", "write-all"}:
                    bad.add(f"scalar:{scope}")
                continue
            if not isinstance(scope, dict):
                bad.add(f"type:{type(scope).__name__}")
                continue
            bad.update(key for key in scope if key not in SUPPORTED_PERMISSIONS)
        if bad:
            invalid[path.name] = bad

    assert invalid == {}


def test_branch_cleanup_does_not_claim_unsupported_automatic_restore() -> None:
    workflow = (WORKFLOWS / "branch-cleanup.yml").read_text(encoding="utf-8")

    assert "restore-branch" not in workflow
    assert "mode=restore" not in workflow
    assert "Restore branch from archive tag" not in workflow


def test_branch_cleanup_stays_preview_only_until_live_guard_is_restored() -> None:
    workflow_path = WORKFLOWS / "branch-cleanup.yml"
    workflow = _workflow(workflow_path.name)
    workflow_text = workflow_path.read_text(encoding="utf-8")
    script = (
        ROOT / "scripts" / "maintenance" / "branch-cleanup-delete.sh"
    ).read_text(encoding="utf-8")

    assert "\n  push:" not in workflow_text
    assert workflow["permissions"].get("contents") == "read"
    assert 'DRY_RUN: "1"' in workflow_text
    assert "Destructive branch cleanup is disabled" in script
    assert "git push origin --delete" not in script
    assert "git tag -f" not in script


def test_e2e_is_blocking_and_targets_the_triggering_sha_deployment() -> None:
    path = WORKFLOWS / "e2e-tests.yml"
    workflow = _workflow(path.name)
    job = workflow["jobs"]["e2e"]
    steps = {step.get("name"): step for step in job["steps"]}
    text = path.read_text(encoding="utf-8")
    target_sha = "${{ github.event.pull_request.head.sha || github.sha }}"

    assert job.get("continue-on-error", False) is False
    assert steps["Checkout"]["with"]["ref"] == target_sha
    assert steps["Checkout"]["with"]["persist-credentials"] is False
    assert 'test "$(git rev-parse HEAD)" = "$TARGET_SHA"' in steps[
        "Verify exact checked-out SHA"
    ]["run"]
    assert steps["Verify exact checked-out SHA"]["env"]["TARGET_SHA"] == target_sha
    assert "Require preview bypass credential" in steps
    assert steps["Run E2E tests"]["continue-on-error"] is True
    assert "exit 1" in steps["Fail the job if tests failed"]["run"]
    assert 'SHA="${{ github.event.pull_request.head.sha || github.sha }}"' in text
    assert 'ENVIRONMENT="${{ github.event_name == \'pull_request\' && \'Preview\' || \'Production\' }}"' in text
    assert 'deployments?sha=${SHA}' in text
    # Both environment-specific deployment filters and the status filter must
    # bind to Vercel's immutable bot identity before a URL is trusted.
    assert text.count(".creator.id == 35613825") == 3
    assert text.count('.creator.login == "vercel[bot]"') == 3
    assert text.count('.creator.type == "Bot"') == 3
    assert text.count('.task == "deploy"') == 2
    assert 'select(.state == "success" and .creator.id == 35613825' in text
    assert "DEPLOY_IDS=$(gh api" in text
    assert "per_page=100" in text
    assert "--paginate" in text
    assert 'done <<< "$DEPLOY_IDS"' in text
    assert "| first | .id" not in text
    assert 'No successful ${ENVIRONMENT} deployment found for exact SHA ${SHA}' in text


def test_workflow_audit_tracks_every_live_workflow() -> None:
    audit = (WORKFLOWS / "AUDIT.md").read_text(encoding="utf-8")
    catalog = (WORKFLOWS / "README.md").read_text(encoding="utf-8")
    missing_from_audit = [
        path.name
        for path in _workflow_paths()
        if f"`{path.name}`" not in audit
    ]
    missing_from_catalog = [
        path.name
        for path in _workflow_paths()
        if f"`{path.name}`" not in catalog
    ]

    assert missing_from_audit == []
    assert missing_from_catalog == []
