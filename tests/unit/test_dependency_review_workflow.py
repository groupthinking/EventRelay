from __future__ import annotations

import hashlib
import io
import json
import os
import runpy
import subprocess
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
    ):
        assert protected_input in detection_script
    assert '"git", "diff", "--name-only", "-z", base, head' in detection_script

    submission = next(
        step for step in steps if step["name"] == "Submit dependency snapshots"
    )
    assert "github.event_name == 'push'" in submission["if"]
    assert "steps.dependency-changes.outputs.changed == 'true'" in submission["if"]
    assert "snapshot_detector" not in submission["if"]
    assert not any("focused" in step["name"].lower() for step in steps)
    assert submission["with"]["snapshot-sha"] == (
        "${{ github.event_name == 'pull_request' && "
        "github.event.pull_request.head.sha || github.sha }}"
    )
    assert submission["with"]["snapshot-ref"] == (
        "${{ github.event_name == 'pull_request' && "
        "format('refs/heads/{0}', github.event.pull_request.head.ref) || github.ref }}"
    )
    assert submission["env"] == {"PipReportFileLevelTimeoutSeconds": "120"}
    assert (
        0
        < int(submission["env"]["PipReportFileLevelTimeoutSeconds"])
        < (job["timeout-minutes"] * 60)
    )
    assert "detectorsFilter" not in submission["with"]

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
    ("changed_paths", "expected_changed", "expected_count"),
    [
        (["pyproject.toml", "uv.lock"], "true", 2),
        (["apps/web/package.json", "apps/web/package-lock.json"], "true", 2),
        (["requirements.txt"], "true", 1),
        (["uv.lock", "requirements.txt"], "true", 2),
        ([".github/workflows/dependency-review.yml"], "false", 0),
        ([".github/dependabot.yml"], "false", 0),
        ([".github/dependabot.yaml"], "false", 0),
        ([".github/dependabot.yml", "apps/web/package.json"], "true", 1),
        (["src/app.py"], "false", 0),
    ],
)
def test_dependency_detection_selects_full_scan_for_manifest_changes(
    tmp_path: Path, changed_paths: list[str], expected_changed: str, expected_count: int
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in {
        "pyproject.toml",
        "uv.lock",
        "apps/web/package.json",
        "apps/web/package-lock.json",
        "requirements.txt",
        "src/app.py",
        ".github/workflows/dependency-review.yml",
        ".github/dependabot.yml",
        ".github/dependabot.yaml",
    }:
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
    assert values["changed"] == expected_changed
    assert values["count"] == str(expected_count)
    assert "snapshot_detector" not in values
    submission = next(
        step for step in steps if step["name"] == "Submit dependency snapshots"
    )
    assert "steps.dependency-changes.outputs.changed == 'true'" in submission["if"]
    assert "steps.dependency-changes.outputs.snapshot_detector" not in submission["if"]


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


@pytest.mark.parametrize("review_outcome", ["failure", "success"])
def test_dependency_review_evidence_preserves_large_complete_api_diff(
    tmp_path: Path, review_outcome: str
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
    assert record["run"] == "python3 scripts/ci/record_dependency_review.py"
    assert not any("steps.review.outputs" in value for value in record["env"].values())
    assert "github.event.pull_request.head.sha" in upload["with"]["name"]
    assert upload["with"]["path"] == "dependency-review-evidence/"
    assert upload["with"]["if-no-files-found"] == "error"

    expression = "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0"
    finding = {"name": "numpy", "version": "2.5.4", "license": expression}
    # This response exceeds the Actions template-object limit hit by grouped PRs.
    changes = [finding, finding, {"name": "$(touch injected)"}] + [
        {"name": f"package-{index}", "license": "MIT", "version": "1.0.0"}
        for index in range(1500)
    ]
    raw = json.dumps(changes).encode()
    assert len(raw) > 64_000
    environment = {
        "BASE_SHA": "a" * 40,
        "HEAD_SHA": "b" * 40,
        "GITHUB_REPOSITORY": "groupthinking/EventRelay",
        "GITHUB_API_URL": "https://api.github.com",
        "GITHUB_TOKEN": "dummy-test-token",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "2",
        "REVIEW_OUTCOME": review_outcome,
    }
    module = runpy.run_path(
        str(WORKFLOW_PATH.parents[2] / "scripts/ci/record_dependency_review.py")
    )
    seen_requests = []

    class ApiResponse(io.BytesIO):
        headers: dict[str, str] = {}

    def fetch(request, timeout):
        seen_requests.append((request, timeout))
        return ApiResponse(raw)

    destination = tmp_path / "dependency-review-evidence"
    module["record_dependency_review"](environment, destination, opener=fetch)
    saved = json.loads((destination / "review.json").read_text())
    assert saved["base_sha"] == "a" * 40
    assert saved["head_sha"] == "b" * 40
    assert saved["run_id"] == "123"
    assert saved["run_attempt"] == "2"
    assert saved["review_outcome"] == review_outcome
    assert saved["dependency_diff_count"] == len(changes)
    assert saved["dependency_diff_sha256"] == hashlib.sha256(raw).hexdigest()
    assert (destination / saved["dependency_diff_file"]).read_bytes() == raw
    assert saved["dependency_diff_source"] == seen_requests[0][0].full_url
    assert seen_requests[0][1] == 90
    assert seen_requests[0][0].get_header("Authorization") == "Bearer dummy-test-token"
    assert not (tmp_path / "injected").exists()


@pytest.mark.parametrize("raw", [b"[]", b'[{"name":"partial"}]'])
def test_dependency_review_evidence_rejects_snapshot_warnings_before_writing(
    tmp_path: Path, raw: bytes
) -> None:
    module = runpy.run_path(
        str(WORKFLOW_PATH.parents[2] / "scripts/ci/record_dependency_review.py")
    )
    environment = {
        "BASE_SHA": "a" * 40,
        "HEAD_SHA": "b" * 40,
        "GITHUB_REPOSITORY": "groupthinking/EventRelay",
        "GITHUB_TOKEN": "dummy-test-token",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "REVIEW_OUTCOME": "success",
    }

    class ApiResponse(io.BytesIO):
        headers = {
            "x-github-dependency-graph-snapshot-warnings": "bWlzc2luZyBzbmFwc2hvdHM="
        }

    destination = tmp_path / "dependency-review-evidence"
    with pytest.raises(ValueError, match="missing snapshots"):
        module["record_dependency_review"](
            environment, destination, opener=lambda request, timeout: ApiResponse(raw)
        )
    assert not destination.exists()


def test_dependency_review_evidence_saves_warning_free_empty_diff(
    tmp_path: Path,
) -> None:
    module = runpy.run_path(
        str(WORKFLOW_PATH.parents[2] / "scripts/ci/record_dependency_review.py")
    )
    environment = {
        "BASE_SHA": "a" * 40,
        "HEAD_SHA": "b" * 40,
        "GITHUB_REPOSITORY": "groupthinking/EventRelay",
        "GITHUB_TOKEN": "dummy-test-token",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "REVIEW_OUTCOME": "success",
    }

    class ApiResponse(io.BytesIO):
        headers: dict[str, str] = {}

    destination = tmp_path / "dependency-review-evidence"
    saved = module["record_dependency_review"](
        environment, destination, opener=lambda request, timeout: ApiResponse(b"[]")
    )
    assert saved["dependency_diff_count"] == 0
    assert (destination / "dependency-diff.json").read_bytes() == b"[]"
