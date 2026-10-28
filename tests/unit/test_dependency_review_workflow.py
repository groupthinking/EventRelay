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
    assert review["with"]["base-ref"] == "${{ github.event.pull_request.base.sha }}"
    assert review["with"]["head-ref"] == "${{ github.event.pull_request.head.sha }}"

    no_delta = next(
        step for step in steps if step["name"] == "Record no dependency delta"
    )
    assert "steps.dependency-changes.outputs.changed == 'false'" in no_delta["if"]


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
