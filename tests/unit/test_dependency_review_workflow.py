from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github/workflows/dependency-review.yml"
)


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "dependency-review workflow should exist"
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    return workflow if "on" in workflow else {**workflow, "on": workflow[True]}


@pytest.mark.parametrize(
    ("changed_path", "expected_changed"),
    [
        (".github/workflows/actions.lock", True),
        ("docs/actions.lock", False),
        (".github/aw/actions-lock.json", False),
    ],
)
def test_dependency_detector_handles_lockfile_only_changes(
    tmp_path: Path, changed_path: str, expected_changed: bool
) -> None:
    """Run the workflow's detector against an actual one-file Git diff."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            [
                "git",
                "-c",
                "user.name=Workflow test",
                "-c",
                "user.email=workflow-test@example.invalid",
                *args,
            ],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "--quiet")
    changed_file = repo / changed_path
    changed_file.parent.mkdir(parents=True, exist_ok=True)
    changed_file.write_text("before\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "baseline")
    base = git("rev-parse", "HEAD")
    changed_file.write_text("after\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "update one lockfile")
    head = git("rev-parse", "HEAD")

    steps = _load_workflow()["jobs"]["dependency-review"]["steps"]
    detection = next(step for step in steps if step.get("id") == "dependency-changes")
    script = detection["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    output = tmp_path / "output"
    summary = tmp_path / "summary"
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo,
        env={
            **os.environ,
            "BASE_SHA": base,
            "HEAD_SHA": head,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        },
        check=True,
        capture_output=True,
        text=True,
    )
    assert output.read_text() == (
        f"changed={str(expected_changed).lower()}\ncount={int(expected_changed)}\n"
    )
    if expected_changed:
        assert f"- `{changed_path}`" in summary.read_text()
    else:
        assert "No dependency manifests" in summary.read_text()


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
        "constraints",
        "package-lock.json",
        "package.json",
        "bun.lock",
        "deno.lock",
        "Directory.Packages.props",
        "mix.lock",
        "stack.yaml.lock",
        "settings.gradle",
        "gradle.properties",
        "Package.resolved",
        "environment.yml",
        "vendor/modules.txt",
        "Dockerfile",
        ".github/dependabot.yaml",
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

    no_delta = next(
        step for step in steps if step["name"] == "Record no dependency delta"
    )
    assert "steps.dependency-changes.outputs.changed == 'false'" in no_delta["if"]
