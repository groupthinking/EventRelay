from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
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
    # `checks: read` is load-bearing, not decorative: the merge job's readiness
    # scan calls `checks.listForRef`, which 403s without it. Commit statuses and
    # check runs are separate surfaces behind separate scopes.
    assert workflow["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "statuses": "read",
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


# ---------------------------------------------------------------------------
# Behavioural coverage for the merge gate (#1476).
#
# The assertions above pin vocabulary: they check that the merge script
# *contains* "pulls.merge" and "semver-major". Both substrings were present in
# the version of this job that could never merge anything, so those tests
# passed against a no-op. The tests below extract the script and run it, so
# they fail if the gate's decisions are wrong regardless of how it is worded.
# ---------------------------------------------------------------------------

DRIVER_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures/dependabot_merge_gate_driver.js"
)

DIRECT_PATCH_COMMIT = """build(deps): bump js-yaml from 4.3.0 to 4.3.1

---
updated-dependencies:
- dependency-name: js-yaml
  dependency-version: 4.3.1
  dependency-type: direct:development
  update-type: version-update:semver-patch
...

Signed-off-by: dependabot[bot] <support@github.com>
"""

# Dependabot omits `update-type` for some indirect bumps -- the hono bump on
# PR #1459 is a real example.
INDIRECT_COMMIT = """build(deps): bump hono from 4.12.32 to 4.13.1

---
updated-dependencies:
- dependency-name: hono
  dependency-version: 4.13.1
  dependency-type: indirect
...
"""

GROUPED_WITH_MAJOR_COMMIT = """build(deps): bump the npm-minor-patch group

---
updated-dependencies:
- dependency-name: safe-dep
  update-type: version-update:semver-patch
- dependency-name: breaking-dep
  update-type: version-update:semver-major
...
"""


def _green(*names: str) -> list[dict]:
    return [
        {"name": name, "status": "completed", "conclusion": "success"} for name in names
    ]


def _run_merge_gate(tmp_path: Path, scenario: dict) -> dict:
    """Execute the workflow's real merge script against a stubbed octokit."""
    node = shutil.which("node")
    if node is None:  # pragma: no cover - depends on the runner image
        pytest.skip("node is required to execute the workflow's inline script")

    workflow = _load_workflow()
    script = workflow["jobs"]["merge"]["steps"][0]["with"]["script"]

    script_path = tmp_path / "merge_script.js"
    script_path.write_text(script)
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario))

    result = subprocess.run(
        [node, str(DRIVER_PATH), str(script_path), str(scenario_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"driver failed: {result.stderr}"
    return json.loads(result.stdout)


def test_merge_gate_merges_a_green_patch_update(tmp_path: Path) -> None:
    """The whole point of the job. This fails against the pre-#1476 script,
    which read `update_type` off a pulls-API field that does not exist and so
    skipped every pull request it was meant to merge."""
    outcome = _run_merge_gate(
        tmp_path,
        {
            "commitMessage": DIRECT_PATCH_COMMIT,
            "combinedState": "success",
            "checkRuns": _green("build", "test", "guards", "lint-python"),
        },
    )

    assert outcome["merged"] is True, outcome["log"]


def test_merge_gate_blocks_while_check_runs_are_unfinished(tmp_path: Path) -> None:
    """Commit statuses carry no CI on this repo -- on a typical Dependabot head
    the combined status is `success` off two Vercel statuses while `build` and
    `test` are still queued. Gating on that alone merged with CI unfinished."""
    outcome = _run_merge_gate(
        tmp_path,
        {
            "commitMessage": DIRECT_PATCH_COMMIT,
            "combinedState": "success",
            "checkRuns": [
                *_green("lint-python"),
                {"name": "build", "status": "queued", "conclusion": None},
                {"name": "test", "status": "in_progress", "conclusion": None},
            ],
        },
    )

    assert outcome["merged"] is False
    assert "still running" in outcome["log"][-1]


def test_merge_gate_blocks_on_a_failing_check_run(tmp_path: Path) -> None:
    outcome = _run_merge_gate(
        tmp_path,
        {
            "commitMessage": DIRECT_PATCH_COMMIT,
            "combinedState": "success",
            "checkRuns": [
                *_green("build", "guards"),
                {"name": "test", "status": "completed", "conclusion": "failure"},
            ],
        },
    )

    assert outcome["merged"] is False
    assert "test=failure" in outcome["log"][-1]


def test_merge_gate_treats_skipped_and_neutral_as_satisfied(tmp_path: Path) -> None:
    """`MERGE_POLICY.md` gate 2 lists conditional checks; `E2E Pipeline Tests`
    is routinely `skipped` and `PR Governance` `neutral`. Neither should
    deadlock a merge."""
    outcome = _run_merge_gate(
        tmp_path,
        {
            "commitMessage": DIRECT_PATCH_COMMIT,
            "combinedState": "success",
            "checkRuns": [
                *_green("build", "test"),
                {
                    "name": "E2E Pipeline Tests",
                    "status": "completed",
                    "conclusion": "skipped",
                },
                {
                    "name": "PR Governance",
                    "status": "completed",
                    "conclusion": "neutral",
                },
            ],
        },
    )

    assert outcome["merged"] is True, outcome["log"]


def test_merge_gate_ignores_its_own_check_runs(tmp_path: Path) -> None:
    """`approve` and `merge` are check runs on the same head, and `merge` is
    necessarily in progress while it evaluates this. Counting them would
    deadlock the gate against itself."""
    outcome = _run_merge_gate(
        tmp_path,
        {
            "commitMessage": DIRECT_PATCH_COMMIT,
            "combinedState": "success",
            "checkRuns": [
                *_green("build", "test"),
                {"name": "approve", "status": "completed", "conclusion": "skipped"},
                {"name": "merge", "status": "in_progress", "conclusion": None},
            ],
        },
    )

    assert outcome["merged"] is True, outcome["log"]


def test_merge_gate_skips_updates_it_cannot_classify(tmp_path: Path) -> None:
    """No `update-type` trailer means the semver impact is unknown. Skipping is
    the conservative read; guessing minor would let a major through."""
    outcome = _run_merge_gate(
        tmp_path,
        {
            "commitMessage": INDIRECT_COMMIT,
            "combinedState": "success",
            "checkRuns": _green("build", "test"),
        },
    )

    assert outcome["merged"] is False
    assert "update type" in outcome["log"][-1]


def test_merge_gate_blocks_a_group_containing_a_major(tmp_path: Path) -> None:
    """Grouped updates carry one trailer entry per dependency. A single major
    in the group disqualifies the PR, so the check cannot stop at the first."""
    outcome = _run_merge_gate(
        tmp_path,
        {
            "commitMessage": GROUPED_WITH_MAJOR_COMMIT,
            "combinedState": "success",
            "checkRuns": _green("build", "test"),
        },
    )

    assert outcome["merged"] is False
    assert "major" in outcome["log"][-1]


def test_merge_gate_still_respects_commit_statuses(tmp_path: Path) -> None:
    """Check runs are an addition, not a replacement -- a red commit status
    (Vercel, CodeRabbit) must still block."""
    outcome = _run_merge_gate(
        tmp_path,
        {
            "commitMessage": DIRECT_PATCH_COMMIT,
            "combinedState": "failure",
            "checkRuns": _green("build", "test"),
        },
    )

    assert outcome["merged"] is False
    assert "combined status" in outcome["log"][-1]


def test_merge_gate_skips_non_dependabot_and_draft_pull_requests(
    tmp_path: Path,
) -> None:
    human = _run_merge_gate(
        tmp_path,
        {
            "author": "groupthinking",
            "commitMessage": DIRECT_PATCH_COMMIT,
            "checkRuns": _green("build", "test"),
        },
    )
    assert human["merged"] is False

    draft = _run_merge_gate(
        tmp_path,
        {
            "draft": True,
            "commitMessage": DIRECT_PATCH_COMMIT,
            "checkRuns": _green("build", "test"),
        },
    )
    assert draft["merged"] is False
