from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github/workflows/dependabot-auto-merge.yml"
)
DEPENDABOT_CONFIG_PATH = Path(__file__).resolve().parents[2] / ".github/dependabot.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "Dependabot automation workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _load_dependabot_config() -> dict:
    assert DEPENDABOT_CONFIG_PATH.exists(), "Dependabot config should exist"
    return yaml.safe_load(DEPENDABOT_CONFIG_PATH.read_text())


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
        "statuses": "read",
        # Without `checks: read` the merge job's checks.listForRef call 403s and
        # the readiness gate below can never be evaluated.
        "checks": "read",
    }
    # The auto-merge feature flag is controlled by a repository variable
    # (vars context), which — unlike env — is available in job-level `if`
    # conditions. It must not be defined as a workflow-level env value, since
    # env is not accessible there and would make the flag inert.
    assert "env" not in workflow or "DEPENDABOT_AUTO_MERGE_ENABLED" not in (
        workflow.get("env") or {}
    )


def test_dependabot_workflow_approves_and_merges_without_checkout() -> None:
    workflow = _load_workflow()
    jobs = workflow["jobs"]

    approve_job = jobs["approve"]
    merge_job = jobs["merge"]

    assert "vars.DEPENDABOT_AUTO_MERGE_ENABLED == 'true'" in approve_job["if"]
    assert "dependabot[bot]" in approve_job["if"]
    assert "github.event.pull_request.user.login == 'dependabot[bot]'" in approve_job["if"]
    assert "github.repository == 'groupthinking/EventRelay'" in approve_job["if"]
    assert "github.actor == 'dependabot[bot]'" not in approve_job["if"]

    assert "vars.DEPENDABOT_AUTO_MERGE_ENABLED == 'true'" in merge_job["if"]

    approve_steps = approve_job["steps"]
    merge_steps = merge_job["steps"]

    assert all(
        not step.get("uses", "").startswith("actions/checkout@")
        for step in approve_steps
    )
    assert all(
        not step.get("uses", "").startswith("actions/checkout@")
        for step in merge_steps
    )
    assert any(
        step.get("uses", "").startswith("dependabot/fetch-metadata@")
        and step.get("id") == "metadata"
        for step in approve_steps
    )

    assert any(
        "createReview" in step.get("with", {}).get("script", "")
        for step in approve_steps
    )
    assert any(
        step.get("if")
        == "steps.metadata.outputs.update-type != 'version-update:semver-major'"
        and "enablePullRequestAutoMerge" in step.get("with", {}).get("script", "")
        for step in approve_steps
    )
    assert any(
        "dependabot[bot]" in step.get("with", {}).get("script", "")
        and "pulls.merge" in step.get("with", {}).get("script", "")
        and "semver-major" in step.get("with", {}).get("script", "")
        for step in merge_steps
    )


def _merge_script() -> str:
    merge_steps = _load_workflow()["jobs"]["merge"]["steps"]
    scripts = [step.get("with", {}).get("script", "") for step in merge_steps]
    script = "\n".join(scripts)
    assert script.strip(), "Merge job should run a github-script step"
    return script


def test_merge_job_does_not_read_update_type_from_the_pull_request_resource() -> None:
    """The pull request REST resource carries no dependency metadata.

    `GET /repos/{owner}/{repo}/pulls/{pull_number}` returns no `dependency`,
    `update_type` or `dependency_update_type` field, and there is no `dorian`
    preview that adds one. Reading the update type from there yielded
    `undefined` on every pull request, so the job hit its
    "Could not determine update type" branch and skipped unconditionally —
    it could never merge anything.
    """
    script = _merge_script()

    assert "dorian" not in script
    assert "mediaType" not in script
    assert "previews" not in script
    assert "dependency?.update_type" not in script
    assert "dependency_update_type" not in script
    # The update type must come from Dependabot's own commit-message block.
    assert "listCommits" in script
    assert "update-type" in script


def test_merge_job_gates_on_check_runs_not_only_commit_statuses() -> None:
    """Commit statuses are not evidence that CI passed on this repo.

    Every check in MERGE_POLICY.md gate 2 (`build`, `test`, `lint-python`,
    `CodeQL`, …) is a check run. The only *statuses* are Vercel's and
    CodeRabbit's, so `getCombinedStatusForRef` reports `success` while CI is
    still queued — observed live on #1433, whose combined status was green at
    20:48 UTC while `build`/`test`/`lint-*` were queued. Gating on the combined
    status alone would merge a Dependabot PR with unfinished or failing CI.
    """
    script = _merge_script()

    assert "checks.listForRef" in script, (
        "Merge readiness must consult the checks API, not just commit statuses"
    )
    # Unfinished checks must block, not be read as passing.
    assert "status !== 'completed'" in script
    # This workflow's own jobs are in flight while the gate runs; counting them
    # would deadlock the check against itself.
    assert "ownJobNames" in script
    assert "'approve'" in script and "'merge'" in script


def test_dependabot_ignores_eslint_v10() -> None:
    config = _load_dependabot_config()
    npm_updates = [
        update
        for update in config["updates"]
        if update["package-ecosystem"] == "npm"
        and update["directory"] in {"/", "/apps/web"}
    ]

    assert len(npm_updates) >= 2, (
        f"Expected npm update entries for both '/' and '/apps/web', got {len(npm_updates)}: "
        f"{[u['directory'] for u in npm_updates]}"
    )

    for update in npm_updates:
        assert {
            "dependency-name": "eslint",
            "versions": [">=10"],
        } in update.get("ignore", [])
