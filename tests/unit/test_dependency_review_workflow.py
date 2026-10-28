from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/dependency-review.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "dependency-review workflow should exist"
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    return workflow if "on" in workflow else {**workflow, "on": workflow[True]}


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

    focused = next(step for step in steps if step["name"] == "Submit focused dependency snapshot")
    assert "steps.dependency-changes.outputs.snapshot_detector != ''" in focused["if"]
    assert "github.event.pull_request.head.repo.full_name == github.repository" in focused["if"]
    assert focused["with"]["filePath"] == "${{ runner.temp }}/dependency-review-input"
    assert "UvLock=EnableIfDefaultOff" in focused["with"]["detectorArgs"]
    assert "NpmLockfile3=EnableIfDefaultOff" in focused["with"]["detectorArgs"]
    assert focused["with"]["snapshot-sha"] == "${{ github.event.pull_request.head.sha }}"

    submission = next(step for step in steps if step["name"] == "Submit dependency snapshots")
    assert "github.event_name == 'push'" in submission["if"]
    assert "steps.dependency-changes.outputs.changed == 'true'" in submission["if"]
    assert "steps.dependency-changes.outputs.snapshot_detector == ''" in submission["if"]
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

    no_delta = next(step for step in steps if step["name"] == "Record no dependency delta")
    assert "steps.dependency-changes.outputs.changed == 'false'" in no_delta["if"]


@pytest.mark.parametrize(
    ("changed_paths", "expected_changed", "expected_detector"),
    [
        (["pyproject.toml", "uv.lock"], "true", "UvLock"),
        (["apps/web/package.json", "apps/web/package-lock.json"], "true", "NpmLockfile3"),
        (["requirements.txt"], "true", ""),
        (["uv.lock", "requirements.txt"], "true", ""),
        ([".github/workflows/dependency-review.yml"], "true", "UvLock,NpmLockfile3"),
        (["src/app.py"], "false", ""),
    ],
)
def test_snapshot_detector_keeps_unrelated_pip_resolves_out_of_lockfile_prs(
    tmp_path: Path,
    changed_paths: list[str],
    expected_changed: str,
    expected_detector: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    all_paths = {
        "pyproject.toml", "uv.lock", "apps/web/package.json",
        "apps/web/package-lock.json", "requirements.txt", "src/app.py",
        ".github/workflows/dependency-review.yml",
    }
    for name in all_paths:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("before\n")

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=Workflow test", "-c", "user.email=workflow@example.com", "commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    for name in changed_paths:
        (repo / name).write_text("after\n")
    git("add", ".")
    git("-c", "user.name=Workflow test", "-c", "user.email=workflow@example.com", "commit", "-qm", "change")
    head = git("rev-parse", "HEAD")

    detection = next(
        step for step in _load_workflow()["jobs"]["dependency-review"]["steps"]
        if step["name"] == "Detect dependency manifest changes"
    )
    output = tmp_path / "github-output"
    summary = tmp_path / "github-summary"
    env = os.environ | {
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(summary),
    }
    subprocess.run(["bash", "-c", detection["run"]], cwd=repo, env=env, check=True)
    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert values["changed"] == expected_changed
    assert values["snapshot_detector"] == expected_detector
    if expected_detector:
        stage = next(
            step for step in _load_workflow()["jobs"]["dependency-review"]["steps"]
            if step["name"] == "Stage focused dependency inputs"
        )
        source = tmp_path / "focused-inputs"
        subprocess.run(
            ["bash", "-c", stage["run"]], cwd=repo, check=True,
            env=env | {
                "SNAPSHOT_SOURCE": str(source),
                "SNAPSHOT_DETECTOR": expected_detector,
            },
        )
        staged = {path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file()}
        assert staged == (
            {"uv.lock", "pyproject.toml"}
            if expected_detector == "UvLock" else
            {"apps/web/package-lock.json", "apps/web/package.json"}
            if expected_detector == "NpmLockfile3" else
            {"uv.lock", "pyproject.toml", "apps/web/package-lock.json", "apps/web/package.json"}
        )
