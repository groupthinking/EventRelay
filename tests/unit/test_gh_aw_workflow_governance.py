from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import conftest as suite_conftest
import pytest
import yaml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict:
    assert path.exists(), f"Expected file to exist: {path}"
    return yaml.safe_load(path.read_text())


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), f"Expected YAML frontmatter: {path}"
    frontmatter, _body = text[4:].split("\n---\n", maxsplit=1)
    return yaml.safe_load(frontmatter)


def _run_pr_iteration_selection(
    *,
    event_name: str,
    event_payload: dict,
    runs: list[dict],
    pulls: list[dict],
    issues: list[dict],
) -> dict:
    if shutil.which("node") is None:
        pytest.skip("node is required to replay the workflow selection script")
    workflow = _load_frontmatter(ROOT / ".github/workflows/pr-iteration-loop.md")
    script = workflow["jobs"]["selection"]["steps"][0]["with"]["script"]
    runner = """
const script = process.env.SELECTION_SCRIPT;
const eventName = process.env.EVENT_NAME;
const payload = JSON.parse(process.env.EVENT_PAYLOAD);
const runs = JSON.parse(process.env.RUNS);
const pulls = JSON.parse(process.env.PULLS);
const issues = JSON.parse(process.env.ISSUES);
const outputs = {};
const files = {};
const marker = {
  actionsList: {},
  pullsList: {},
  issuesList: {},
};
const github = {
  rest: {
    actions: { listWorkflowRunsForRepo: marker.actionsList },
    pulls: {
      list: marker.pullsList,
      get: async ({ pull_number }) => {
        const found = pulls.find((pr) => pr.number === pull_number);
        if (!found) throw new Error(`missing pull ${pull_number}`);
        return { data: found };
      },
    },
    issues: { listForRepo: marker.issuesList },
  },
  paginate: async (method) => {
    if (method === marker.actionsList) return runs;
    if (method === marker.pullsList) return pulls;
    if (method === marker.issuesList) return issues;
    return [];
  },
};
const context = {
  eventName,
  payload,
  repo: { owner: "groupthinking", repo: "EventRelay" },
};
const core = {
  setOutput: (name, value) => {
    outputs[name] = String(value);
  },
};
const fs = {
  writeFileSync: (path, content) => {
    files[path] = content;
  },
};
const run = new Function("github", "context", "core", "fs", `return (async () => {${script}\\n})();`);
run(github, context, core, fs)
  .then(() => {
    process.stdout.write(JSON.stringify({ outputs, files }));
  })
  .catch((error) => {
    process.stderr.write(String(error && error.stack ? error.stack : error));
    process.exit(1);
  });
"""
    try:
        result = subprocess.run(
            ["node", "-e", runner],
            check=True,
            text=True,
            capture_output=True,
            env={
                **os.environ,
                "SELECTION_SCRIPT": script,
                "EVENT_NAME": event_name,
                "EVENT_PAYLOAD": json.dumps(event_payload),
                "RUNS": json.dumps(runs),
                "PULLS": json.dumps(pulls),
                "ISSUES": json.dumps(issues),
            },
        )
    except FileNotFoundError:
        pytest.skip("node is required to replay the workflow selection script")
    return json.loads(result.stdout)


def _selection_payload(selection_result: dict) -> dict:
    context_b64 = selection_result["outputs"]["context_json_b64"]
    return json.loads(base64.b64decode(context_b64.encode("utf-8")).decode("utf-8"))



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
    assert "--cov-fail-under=88.1833" in run_script
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
    assert "--cov=src/youtube_extension" in test_script
    # The unit-only CI job must NOT enforce the full-suite baseline: 88.1833%
    # (19,761 / 22,409 statements) is measured over the complete `tests/` suite
    # in coverage.yml. Enforcing it on this reduced scope, against the same
    # package-wide denominator, would fail every run. coverage.yml is authoritative.
    assert "--cov-fail-under" not in test_script
    assert "--override-ini" not in test_script
    for suppression in ("|| true", "2>/dev/null", "set +e"):
        assert suppression not in install_script


def test_ci_runs_supported_python_matrix_with_immutable_actions() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/ci.yml")
    workflow_on = workflow.get("on", workflow.get(True))
    test_job = workflow["jobs"]["test"]
    setup_python_steps = [
        step
        for step in test_job["steps"]
        if str(step.get("uses", "")).startswith("actions/setup-python@")
    ]
    assert len(setup_python_steps) == 1
    setup_python = setup_python_steps[0]
    run_tests = next(
        step for step in test_job["steps"] if step.get("name") == "Run tests"
    )
    lock_check = next(
        step for step in test_job["steps"] if step.get("name") == "Check lockfile"
    )

    assert workflow_on["push"]["branches"] == ["main"]
    assert workflow_on["pull_request"] is None
    assert test_job.get("if") is None
    assert test_job["strategy"] == {
        "fail-fast": False,
        "matrix": {"python-version": ["3.10", "3.11", "3.12"]},
    }
    python_versions = test_job["strategy"]["matrix"]["python-version"]
    assert python_versions == [
        "3.10",
        "3.11",
        "3.12",
    ]
    assert test_job["name"] == "test (Python ${{ matrix.python-version }})"
    merge_policy = (ROOT / "MERGE_POLICY.md").read_text()
    for python_version in python_versions:
        assert f"`test (Python {python_version})`" in merge_policy
    assert setup_python["with"]["python-version"] == "${{ matrix.python-version }}"
    assert lock_check.get("if") is None
    assert not lock_check.get("continue-on-error", False)
    assert lock_check["run"] == "uv lock --check"
    assert run_tests.get("if") is None
    test_script = run_tests["run"]
    assert test_script == (
        "PYTHONPATH=src python -m pytest tests/unit/ -v --timeout=120 "
        "--cov=src/youtube_extension "
        "--ignore=tests/unit/test_transcript_action_workflow.py -k \"not integration\""
    )
    assert not test_job.get("continue-on-error", False)
    assert not run_tests.get("continue-on-error", False)
    for suppression in ("|| true", "set +e", "--collect-only"):
        assert suppression not in test_script

    immutable_action = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
    immutable_container = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")
    immutable_image = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")

    def assert_immutable_uses(uses: str) -> None:
        if uses.startswith("./"):
            return
        if uses.startswith("docker://"):
            assert immutable_container.fullmatch(uses), uses
            return
        assert immutable_action.fullmatch(uses), uses

    for job in workflow["jobs"].values():
        reusable_workflow = job.get("uses")
        if reusable_workflow:
            assert_immutable_uses(reusable_workflow)
        container = job.get("container")
        if container:
            image = container if isinstance(container, str) else container["image"]
            assert immutable_image.fullmatch(image), image
        for service in job.get("services", {}).values():
            image = service if isinstance(service, str) else service["image"]
            assert immutable_image.fullmatch(image), image
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses:
                assert_immutable_uses(uses)


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


def test_ci_investigator_workflow_removed() -> None:
    """CI Investigator was retired (noise-only output); sources must stay gone."""
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
    setup_entry = actions_lock["entries"]["github/gh-aw-actions/setup@v0.88.7"]
    setup_cli_entry = actions_lock["entries"]["github/gh-aw-actions/setup-cli@v0.88.7"]
    assert setup_entry["sha"] == "5e508589e03a7757a7e05b26e834292f5445bfb6"
    assert setup_cli_entry["sha"] == "5e508589e03a7757a7e05b26e834292f5445bfb6"
    step_scripts = [step.get("run", "") for step in workflow["jobs"]["validate-gh-aw"]["steps"]]
    combined = "\n".join(step_scripts)
    assert "gh extension install github/gh-aw --pin v0.88.7" in combined
    assert "eventrelay-ci-investigator" not in combined
    assert "canonical-pr-remediator" in combined
    assert "focused-coverage-controller" in combined
    assert "pr-iteration-loop" in combined
    assert "repo-assist" in combined


def test_gh_aw_validation_tracks_poutine_policy_paths() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/gh-aw-validation.yml")
    workflow_on = workflow.get("on", workflow.get(True))

    assert workflow_on is not None
    assert ".poutine.yml" in workflow_on["push"]["paths"]
    assert ".poutine.yml" in workflow_on["pull_request"]["paths"]


def test_pr_iteration_requires_explicit_issue_pr_dispatch_and_repo_concurrency() -> None:
    workflow = _load_frontmatter(ROOT / ".github/workflows/pr-iteration-loop.md")
    workflow_on = workflow.get("on", workflow.get(True))

    assert workflow_on is not None
    assert workflow_on["workflow_dispatch"] is None
    assert workflow_on["issues"]["types"] == ["labeled"]
    assert workflow_on["pull_request"]["types"] == ["labeled"]
    assert workflow_on["issue_comment"]["types"] == ["created"]
    assert workflow_on["push"]["branches"] == ["main"]
    assert workflow_on["schedule"] == [{"cron": "0 9 * * 1-5"}]
    assert workflow["concurrency"] == {
        "group": "pr-iteration-loop-${{ github.repository }}",
        "cancel-in-progress": False,
    }


def test_pr_iteration_selection_uses_fingerprint_and_skip_reasons() -> None:
    workflow_source = (ROOT / ".github/workflows/pr-iteration-loop.md").read_text()

    assert "selection: {" in workflow_source
    assert "fingerprint" in workflow_source
    assert "marker_line" in workflow_source
    assert "skipped: []" in workflow_source
    assert "payload.selection.reasons.push" in workflow_source
    assert "payload.selection.duplicate_owner" in workflow_source
    assert "line.trim() === marker" in workflow_source
    assert "Targeted trigger observed without authorization; skipping ranked fallback." in workflow_source


def test_pr_iteration_no_candidate_short_circuits_before_dependency_install() -> None:
    workflow = _load_frontmatter(ROOT / ".github/workflows/pr-iteration-loop.md")
    selection_job = workflow["jobs"]["selection"]
    selection_step = selection_job["steps"][0]
    agent_job = workflow["jobs"]["agent"]

    assert selection_job["outputs"]["should_proceed"] == "${{ steps.select-checkpoint.outputs.should_proceed }}"
    assert selection_step["name"] == "Select deterministic checkpoint seed"
    assert selection_step["id"] == "select-checkpoint"
    assert "core.setOutput(\"should_proceed\", \"false\")" in selection_step["with"]["script"]
    assert "No candidate selected; exiting before dependency installation" in selection_step["with"]["script"]
    assert "needs.selection.outputs.should_proceed == 'true'" in agent_job["if"]
    assert "selection" in agent_job["needs"]


def test_pr_iteration_safe_outputs_disallow_automation_merge() -> None:
    workflow = _load_frontmatter(ROOT / ".github/workflows/pr-iteration-loop.md")
    safe_outputs = workflow["safe-outputs"]
    workflow_source = (ROOT / ".github/workflows/pr-iteration-loop.md").read_text()

    assert "merge-pull-request" not in safe_outputs
    assert safe_outputs["push-to-pull-request-branch"]["target"] == "*"
    assert safe_outputs["push-to-pull-request-branch"]["required-title-prefix"] == "[ai] "
    assert safe_outputs["push-to-pull-request-branch"]["required-labels"] == ["automation", "ai-agent"]
    assert '.filter((pr) => pr.head?.ref?.startsWith("pr-iteration/"))' in workflow_source


def test_pr_iteration_eval_requires_deterministic_observed_outcome_match() -> None:
    workflow = _load_frontmatter(ROOT / ".github/workflows/pr-iteration-loop.md")
    evals = workflow["evals"]
    eval_job = workflow["jobs"]["evals"]

    deterministic_eval = next(item for item in evals if item["id"] == "deterministic_postcondition")
    question = deterministic_eval["question"]
    assert "claimed_outcome" in question
    assert "observed_outcome" in question
    assert "match result" in question
    assert "safe-output apply result" in question
    assert "safe_outputs" in eval_job["needs"]


def test_pr_iteration_selection_replay_blocks_unauthorized_pr_label_without_fallback() -> None:
    pull = {
        "number": 42,
        "title": "Human PR",
        "html_url": "https://example/pr/42",
        "head": {"ref": "feature/human-change"},
        "updated_at": "2000-01-01T00:00:00Z",
        "labels": [],
        "state": "open",
        "body": "",
    }
    stale_issue = {
        "number": 7,
        "title": "Fallback issue",
        "html_url": "https://example/issues/7",
        "updated_at": "2000-01-01T00:00:00Z",
        "labels": [],
        "state": "open",
        "body": "",
    }
    result = _run_pr_iteration_selection(
        event_name="pull_request",
        event_payload={
            "action": "labeled",
            "label": {"name": "pr-iteration"},
            "pull_request": pull,
        },
        runs=[],
        pulls=[pull],
        issues=[stale_issue],
    )
    payload = _selection_payload(result)
    assert result["outputs"]["should_proceed"] == "false"
    assert payload["selection"]["authorized_trigger"] is False
    assert payload["selection"]["selected_kind"] is None
    assert (
        "Targeted trigger observed without authorization; skipping ranked fallback."
        in payload["selection"]["reasons"]
    )


def test_pr_iteration_selection_replay_uses_exact_marker_line_for_dedupe() -> None:
    selected_issue = {
        "number": 1,
        "title": "Stale issue",
        "html_url": "https://example/issues/1",
        "updated_at": "2000-01-01T00:00:00Z",
        "labels": [],
        "state": "open",
        "body": "",
    }
    near_match = {
        "number": 99,
        "title": "Near match",
        "html_url": "https://example/issues/99",
        "updated_at": "2000-01-01T00:00:00Z",
        "labels": [],
        "state": "open",
        "body": "pr-iteration-fingerprint: issue:10",
    }
    result = _run_pr_iteration_selection(
        event_name="workflow_dispatch",
        event_payload={},
        runs=[],
        pulls=[],
        issues=[selected_issue, near_match],
    )
    payload = _selection_payload(result)
    assert result["outputs"]["should_proceed"] == "true"
    assert payload["selection"]["fingerprint"] == "issue:1"
    assert payload["selection"]["duplicate_owner"] is None


def test_pr_iteration_push_rule_requires_ai_title_prefix() -> None:
    workflow_source = (ROOT / ".github/workflows/pr-iteration-loop.md").read_text()

    assert 'required-title-prefix: "[ai] "' in workflow_source
