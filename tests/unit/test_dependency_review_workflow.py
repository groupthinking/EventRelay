from __future__ import annotations

import json
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

    focused = next(
        step for step in steps if step["name"] == "Submit focused dependency snapshot"
    )
    assert "steps.dependency-changes.outputs.snapshot_detector != ''" in focused["if"]
    assert (
        "github.event.pull_request.head.repo.full_name == github.repository"
        in focused["if"]
    )
    assert focused["with"]["filePath"] == "${{ runner.temp }}/dependency-review-head"
    assert focused["with"]["correlator"] == "focused-lockfile-review"
    assert "UvLock=EnableIfDefaultOff" in focused["with"]["detectorArgs"]
    assert "NpmLockfile3=EnableIfDefaultOff" in focused["with"]["detectorArgs"]
    assert (
        focused["with"]["snapshot-sha"] == "${{ github.event.pull_request.head.sha }}"
    )

    focused_base = next(
        step
        for step in steps
        if step["name"] == "Submit focused base dependency snapshot"
    )
    assert (
        focused_base["with"]["filePath"] == "${{ runner.temp }}/dependency-review-base"
    )
    assert focused_base["with"]["correlator"] == focused["with"]["correlator"]
    assert (
        focused_base["with"]["snapshot-sha"]
        == "${{ github.event.pull_request.base.sha }}"
    )

    submission = next(
        step for step in steps if step["name"] == "Submit dependency snapshots"
    )
    assert "github.event_name == 'push'" in submission["if"]
    assert "steps.dependency-changes.outputs.changed == 'true'" in submission["if"]
    assert (
        "steps.dependency-changes.outputs.snapshot_detector == ''" in submission["if"]
    )
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
    assert review["with"]["base-ref"] == "${{ github.event.pull_request.base.sha }}"
    assert review["with"]["head-ref"] == "${{ github.event.pull_request.head.sha }}"

    no_delta = next(
        step for step in steps if step["name"] == "Record no dependency delta"
    )
    assert "steps.dependency-changes.outputs.changed == 'false'" in no_delta["if"]


@pytest.mark.parametrize(
    ("changed_paths", "expected_changed", "expected_detector"),
    [
        (["pyproject.toml", "uv.lock"], "true", "UvLock"),
        (
            ["apps/web/package.json", "apps/web/package-lock.json"],
            "true",
            "NpmLockfile3",
        ),
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
        "pyproject.toml",
        "uv.lock",
        "apps/web/package.json",
        "apps/web/package-lock.json",
        "requirements.txt",
        "src/app.py",
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
    git(
        "-c",
        "user.name=Workflow test",
        "-c",
        "user.email=workflow@example.com",
        "commit",
        "-qm",
        "base",
    )
    base = git("rev-parse", "HEAD")
    for name in changed_paths:
        (repo / name).write_text("after\n")
    git("add", ".")
    git(
        "-c",
        "user.name=Workflow test",
        "-c",
        "user.email=workflow@example.com",
        "commit",
        "-qm",
        "change",
    )
    head = git("rev-parse", "HEAD")

    detection = next(
        step
        for step in _load_workflow()["jobs"]["dependency-review"]["steps"]
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
            step
            for step in _load_workflow()["jobs"]["dependency-review"]["steps"]
            if step["name"] == "Stage focused dependency inputs"
        )
        base_source = tmp_path / "focused-base"
        head_source = tmp_path / "focused-head"
        subprocess.run(
            ["bash", "-c", stage["run"]],
            cwd=repo,
            check=True,
            env=env
            | {
                "SNAPSHOT_BASE_SOURCE": str(base_source),
                "SNAPSHOT_HEAD_SOURCE": str(head_source),
                "SNAPSHOT_DETECTOR": expected_detector,
            },
        )
        expected = (
            {"uv.lock", "pyproject.toml"}
            if expected_detector == "UvLock"
            else {"apps/web/package-lock.json", "apps/web/package.json"}
            if expected_detector == "NpmLockfile3"
            else {
                "uv.lock",
                "pyproject.toml",
                "apps/web/package-lock.json",
                "apps/web/package.json",
            }
        )
        for source in (base_source, head_source):
            staged = {
                path.relative_to(source).as_posix()
                for path in source.rglob("*")
                if path.is_file()
            }
            assert staged == expected
        for name in changed_paths:
            if name in expected:
                assert (base_source / name).read_text() == "before\n"
                assert (head_source / name).read_text() == "after\n"


@pytest.mark.parametrize(
    ("changed_paths", "expected_detector"),
    [
        (["package-lock.json"], "NpmLockfile3"),
        (["package-lock.json", "apps/web/package.json"], "NpmLockfile3"),
        (["package-lock.json", "sdk/typescript/package.json"], ""),
        (["apps/web/package.json"], ""),
    ],
)
def test_root_npm_lock_stages_workspace_roots_and_rejects_uncovered_manifests(
    tmp_path: Path, changed_paths: list[str], expected_detector: str
) -> None:
    repo = tmp_path / "repo"
    for name, content in {
        "package.json": '{"workspaces": ["apps/*"]}\n',
        "package-lock.json": '{"packages": {"": {}, "apps/web": {}}}\n',
        "apps/web/package.json": '{"name": "eventrelay-web"}\n',
        "sdk/typescript/package.json": '{"name": "eventrelay-sdk"}\n',
    }.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("add", ".")
    git(
        "-c",
        "user.name=Workflow test",
        "-c",
        "user.email=workflow@example.com",
        "commit",
        "-qm",
        "base",
    )
    base = git("rev-parse", "HEAD")
    for name in changed_paths:
        path = repo / name
        path.write_text(path.read_text().rstrip()[:-1] + ', "test": "after"}\n')
    git("add", ".")
    git(
        "-c",
        "user.name=Workflow test",
        "-c",
        "user.email=workflow@example.com",
        "commit",
        "-qm",
        "change",
    )
    head = git("rev-parse", "HEAD")

    steps = _load_workflow()["jobs"]["dependency-review"]["steps"]
    detection = next(
        step for step in steps if step["name"] == "Detect dependency manifest changes"
    )
    output = tmp_path / "github-output"
    env = os.environ | {
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "github-summary"),
    }
    subprocess.run(["bash", "-c", detection["run"]], cwd=repo, env=env, check=True)
    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert values["snapshot_detector"] == expected_detector
    if expected_detector:
        stage = next(
            step for step in steps if step["name"] == "Stage focused dependency inputs"
        )
        base_source = tmp_path / "focused-base"
        head_source = tmp_path / "focused-head"
        subprocess.run(
            ["bash", "-c", stage["run"]],
            cwd=repo,
            check=True,
            env=env
            | {
                "SNAPSHOT_BASE_SOURCE": str(base_source),
                "SNAPSHOT_HEAD_SOURCE": str(head_source),
                "SNAPSHOT_DETECTOR": expected_detector,
            },
        )
        expected = {"package-lock.json", "package.json", "apps/web/package.json"}
        for source in (base_source, head_source):
            staged = {
                path.relative_to(source).as_posix()
                for path in source.rglob("*")
                if path.is_file()
            }
            assert staged == expected


def test_numpy_remains_subject_to_the_unchanged_license_policy() -> None:
    steps = _load_workflow()["jobs"]["dependency-review"]["steps"]
    review = next(step for step in steps if step["name"] == "Dependency Review")
    settings = review["with"]

    # NumPy's AND expression legitimately fails because Zlib is not approved.
    # Passing the latest graph delta must not become a package or license bypass.
    assert {item.strip() for item in settings["allow-licenses"].split(",")} == {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "Python-2.0",
        "BlueOak-1.0.0",
        "MPL-2.0",
        "CC0-1.0",
        "0BSD",
        "MIT-CMU",
        "Unlicense",
    }
    exclusions = settings["allow-dependencies-licenses"].split(",")
    assert not any(
        item.strip().split("@", 1)[0] == "pkg:pypi/numpy" for item in exclusions
    )
    assert settings.get("license-check", True) is True
    assert settings.get("warn-only", False) is False
    assert "continue-on-error" not in review
    assert review["uses"] == (
        "actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294"
    )


@pytest.mark.parametrize(
    "review_outcome,raw_output", [("failure", None), ("success", "")]
)
def test_dependency_review_evidence_preserves_composite_license_and_unknown_outputs(
    tmp_path: Path, review_outcome: str, raw_output: str | None
) -> None:
    steps = _load_workflow()["jobs"]["dependency-review"]["steps"]
    review = next(step for step in steps if step["name"] == "Dependency Review")
    record = next(
        step for step in steps if step["name"] == "Record dependency review evidence"
    )
    upload = next(
        step for step in steps if step["name"] == "Upload dependency review evidence"
    )
    assert review["id"] == "review"
    for step in (record, upload):
        assert "always()" in step["if"]
        assert "github.event_name == 'pull_request'" in step["if"]
        assert "steps.dependency-changes.outputs.changed == 'true'" in step["if"]
    assert record["env"]["INVALID_LICENSE_CHANGES"] == (
        "${{ steps.review.outputs.invalid-license-changes }}"
    )
    assert "github.event.pull_request.head.sha" in upload["with"]["name"]
    assert upload["with"]["path"] == "dependency-review-evidence/review.json"
    assert upload["with"]["if-no-files-found"] == "error"

    expression = "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0"
    finding = {"name": "numpy", "version": "2.5.4", "license": expression}
    # Keep duplicated occurrences, the full AND expression, and hostile text as data.
    invalid = json.dumps(
        {"forbidden": [finding, finding], "unresolved": [], "unlicensed": []}
    )
    dependencies = json.dumps([finding, {"name": "$(touch injected)"}])
    environment = {
        # A failing subprocess may print its environment in pytest's traceback.
        # Pass only this test's inputs, never credentials from the caller.
        "PATH": os.pathsep.join((str(Path(sys.executable).parent), os.defpath)),
        "BASE_SHA": "a" * 40,
        "HEAD_SHA": "b" * 40,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "2",
        "REVIEW_OUTCOME": review_outcome,
        "DEPENDENCY_CHANGES": dependencies if raw_output is None else raw_output,
        "INVALID_LICENSE_CHANGES": invalid if raw_output is None else raw_output,
        "VULNERABLE_CHANGES": "[]" if raw_output is None else raw_output,
        "DENIED_CHANGES": "",
    }
    subprocess.run(
        ["bash", "-e", "-c", record["run"]], cwd=tmp_path, env=environment, check=True
    )
    saved = json.loads((tmp_path / upload["with"]["path"]).read_text())
    assert saved["base_sha"] == "a" * 40
    assert saved["head_sha"] == "b" * 40
    assert saved["run_id"] == "123"
    assert saved["run_attempt"] == "2"
    assert saved["review_outcome"] == review_outcome
    assert saved["raw_outputs"] == {
        "dependency-changes": environment["DEPENDENCY_CHANGES"],
        "invalid-license-changes": environment["INVALID_LICENSE_CHANGES"],
        "vulnerable-changes": environment["VULNERABLE_CHANGES"],
        "denied-changes": "",
    }
    assert not (tmp_path / "injected").exists()
