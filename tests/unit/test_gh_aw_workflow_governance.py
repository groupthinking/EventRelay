from __future__ import annotations

import json
from pathlib import Path

import conftest as suite_conftest
import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[2]



def _load_yaml(path: Path) -> dict:
    assert path.exists(), f"Expected file to exist: {path}"
    return yaml.safe_load(path.read_text())


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), f"Expected YAML frontmatter: {path}"
    frontmatter, _body = text[4:].split("\n---\n", maxsplit=1)
    return yaml.safe_load(frontmatter)



def test_coverage_workflow_is_authoritative() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/coverage.yml")
    job = workflow["jobs"]["coverage"]
    steps = job["steps"]
    run_step = next(step for step in steps if step.get("name") == "Run tests with coverage")
    artifact_step = next(
        step for step in steps if step.get("name") == "Upload coverage artifacts"
    )
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    coverage_report = config["tool"]["coverage"]["report"]
    pytest_addopts = config["tool"]["pytest"]["ini_options"]["addopts"]

    assert 0 < int(job["timeout-minutes"]) <= 45
    assert "continue-on-error" not in job
    assert "continue-on-error" not in run_step
    run_script = run_step["run"]
    assert "pytest tests/" in run_script
    assert "--cov=src/youtube_extension" in run_script
    assert "--cov-fail-under" not in run_script
    assert "--cov-fail-under" not in pytest_addopts
    assert "--timeout=120" in run_script
    assert ".[dev,youtube]" in next(
        step for step in steps if step.get("name") == "Install dependencies"
    )["run"]
    assert 88.1833 <= float(coverage_report["fail_under"]) <= 90
    assert int(coverage_report["precision"]) >= 4
    for suppression in ("|| true", "set +e"):
        assert suppression not in run_script
    assert artifact_step["if"] == "always()"
    assert "--cov-report=json:reports/coverage.json" in run_script
    assert "reports/coverage.json" in artifact_step["with"]["path"]
    assert artifact_step["with"]["if-no-files-found"] == "error"


def test_ci_installs_the_authoritative_python_environment() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/ci.yml")
    steps = workflow["jobs"]["test"]["steps"]
    install_script = next(
        step for step in steps if step.get("name") == "Install dependencies"
    )["run"]
    test_script = next(
        step for step in steps if step.get("name") == "Run tests"
    )["run"]

    assert 'python -m pip install -e ".[dev,youtube]"' in install_script
    assert "--timeout=120" in test_script
    for suppression in ("|| true", "2>/dev/null", "set +e"):
        assert suppression not in install_script



def test_obsolete_agentic_verification_loop_removed() -> None:
    assert not (ROOT / ".github/agentic/verification-loop.aw.yml").exists()


def test_focused_coverage_controller_can_read_authoritative_runs() -> None:
    workflow = _load_frontmatter(
        ROOT / ".github/workflows/focused-coverage-controller.md"
    )
    toolsets = workflow["tools"]["github"]["toolsets"]
    credential_gate = next(
        step
        for step in workflow["pre-agent-steps"]
        if step.get("name") == "Require dedicated Codex credential"
    )

    assert "actions" in toolsets
    assert credential_gate["env"]["CODEX_API_KEY"] == "${{ secrets.CODEX_API_KEY }}"
    assert "Dedicated CODEX_API_KEY is required" in credential_gate["run"]
    assert "OPENAI_API_KEY" not in credential_gate["run"]
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["permissions"]["pull-requests"] == "read"

    source = (ROOT / ".github/workflows/focused-coverage-controller.md").read_text()
    assert "Focused Coverage Controller (read-only canary)" in source
    assert "do not commit, push, or mutate branches" in source
    assert "requires a separate approved GitHub App canary" in source


def test_obsolete_ci_investigator_workflow_removed() -> None:
    # The EventRelay CI Investigator workflow (source .md and compiled .lock.yml)
    # was intentionally removed in 07b8a2e ("noise-only output; per repo cleanup").
    # Guard against reintroduction; canonical-pr-remediator and
    # focused-coverage-controller remain the authoritative agentic workflows.
    assert not (ROOT / ".github/workflows/eventrelay-ci-investigator.md").exists()
    assert not (ROOT / ".github/workflows/eventrelay-ci-investigator.lock.yml").exists()


def test_live_smoke_modules_are_excluded_before_import(monkeypatch) -> None:
    monkeypatch.delenv("RUN_LIVE_E2E", raising=False)
    monkeypatch.delenv("RUN_LIVE_DEPLOY", raising=False)

    assert len(suite_conftest._LIVE_E2E_TESTS) == 16
    assert suite_conftest._LIVE_DEPLOY_TESTS < suite_conftest._LIVE_E2E_TESTS
    for relative_path in suite_conftest._LIVE_E2E_TESTS:
        assert suite_conftest.pytest_ignore_collect(
            ROOT / "tests" / relative_path, None
        ), relative_path

    assert not suite_conftest.pytest_ignore_collect(
        ROOT / "tests/unit/test_video_utils.py", None
    )


def test_live_deployment_requires_a_second_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("RUN_LIVE_E2E", "1")
    monkeypatch.delenv("RUN_LIVE_DEPLOY", raising=False)

    for relative_path in suite_conftest._LIVE_DEPLOY_TESTS:
        assert suite_conftest.pytest_ignore_collect(
            ROOT / "tests" / relative_path, None
        ), relative_path

    non_deploy = suite_conftest._LIVE_E2E_TESTS - suite_conftest._LIVE_DEPLOY_TESTS
    for relative_path in non_deploy:
        assert not suite_conftest.pytest_ignore_collect(
            ROOT / "tests" / relative_path, None
        ), relative_path

    monkeypatch.setenv("RUN_LIVE_DEPLOY", "1")
    for relative_path in suite_conftest._LIVE_DEPLOY_TESTS:
        assert not suite_conftest.pytest_ignore_collect(
            ROOT / "tests" / relative_path, None
        ), relative_path


def test_controller_does_not_claim_an_unavailable_live_lane() -> None:
    source = (ROOT / ".github/workflows/focused-coverage-controller.md").read_text()

    assert "No Python live-smoke workflow is installed" in source
    assert "must not set `RUN_LIVE_E2E`" in source
    assert "must not claim that live Python smoke tests ran" in source
    assert "## Controller reporting requirement" in source
    assert "controller login and run ID" in source
    assert "## Jules reporting requirement" not in source



def test_gh_aw_validation_pins_runtime_version() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/gh-aw-validation.yml")
    actions_lock = json.loads((ROOT / ".github/aw/actions-lock.json").read_text())

    assert workflow["name"] == "gh-aw Validation"
    entry = actions_lock["entries"]["github/gh-aw-actions/setup@v0.82.14"]
    assert entry["sha"] == "b6d1443e05b8716267fa19425b99aa4f12006b4a"
    step_scripts = [step.get("run", "") for step in workflow["jobs"]["validate-gh-aw"]["steps"]]
    combined = "\n".join(step_scripts)
    assert "gh extension install github/gh-aw --pin v0.82.14" in combined
    # eventrelay-ci-investigator was removed (07b8a2e); validation must no longer
    # compile or diff it, otherwise the gh-aw Validation workflow fails at runtime
    # against a source/lock file that no longer exists.
    assert "eventrelay-ci-investigator" not in combined
    assert "canonical-pr-remediator" in combined
    assert "focused-coverage-controller" in combined
