from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/pr-governance.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "PR governance workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _get_script(workflow: dict) -> str:
    steps = workflow["jobs"]["policy"]["steps"]
    script_step = next(
        step
        for step in steps
        if "Validate delivery contract" in step.get("name", "")
    )
    return script_step["with"]["script"]


def test_governance_workflow_file_is_valid_yaml() -> None:
    workflow = _load_workflow()
    assert workflow["name"] == "PR Governance"


def test_governance_workflow_triggers_on_pull_request_target() -> None:
    workflow = _load_workflow()
    # PyYAML parses the YAML 'on' key as Python True.
    triggers = workflow[True]
    assert "pull_request_target" in triggers
    types = triggers["pull_request_target"]["types"]
    assert "opened" in types
    assert "synchronize" in types
    assert "ready_for_review" in types


def test_governance_workflow_uses_minimum_permissions() -> None:
    workflow = _load_workflow()
    perms = workflow["permissions"]
    assert perms.get("checks") == "write"
    assert perms.get("contents") == "read"
    assert perms.get("pull-requests") == "read"
    assert perms.get("issues") == "read"
    assert set(perms) == {"checks", "contents", "issues", "pull-requests"}


def test_governance_workflow_publishes_exact_head_check() -> None:
    script = _get_script(_load_workflow())
    assert 'name: "PR Governance"' in script
    assert "github.rest.checks.create" in script
    assert "head_sha: pr.head.sha" in script
    assert 'status: "completed"' in script


def test_governance_workflow_draft_bypass_is_head_bound() -> None:
    script = _get_script(_load_workflow())
    assert "pr.draft" in script
    assert '"neutral"' in script
    assert "Governance deferred for draft PR" in script
    assert "pr.head.sha" in script


def test_governance_workflow_rejects_default_placeholders() -> None:
    script = _get_script(_load_workflow())
    assert "placeholderPatterns" in script
    assert "hasMeaningfulContent" in script
    assert "Describe the user or operational result" in script
    assert "Risk level:" in script
    assert "Focused tests" in script
    assert "meaningfulLines.length > 0" in script
    assert r'replace(/<!--[\s\S]*?-->/g, "").trim()' in script
    assert r'replace(/<!--[\\s\\S]*?-->/g, "").trim()' not in script


def test_governance_workflow_validates_issue_via_api() -> None:
    script = _get_script(_load_workflow())
    assert "github.rest.issues.get" in script
    assert "pull_request" in script
    assert "issue.state" in script
    assert "404" in script


def test_governance_workflow_detects_competing_prs() -> None:
    script = _get_script(_load_workflow())
    assert "github.paginate" in script
    assert "github.rest.pulls.list" in script
    assert "competing" in script
    assert "another open implementation PR" in script


def test_governance_workflow_checks_issue_before_competitors() -> None:
    script = _get_script(_load_workflow())
    assert script.index("github.rest.issues.get") < script.index(
        "github.rest.pulls.list"
    )


# --------------------------------------------------------------------------
# Behavioural tests (#1419).
#
# The assertions above match strings in the script source, so they stay green
# even if the logic inverts. These run the real script under Node against
# synthetic payloads and assert on the conclusion it publishes.
# --------------------------------------------------------------------------

CONTRACT_BODY = """## Canonical issue

Closes #1419

## Outcome

Real outcome text.

## Risk

- Risk level: low
- Failure mode: none observed
- Rollback: git revert

## Verification

Ran the focused suite.

## Production evidence

Not applicable - workflow-only change.
"""

# Shape of a real Dependabot body: release notes and a commit list, none of
# the five required headings, no closing reference. Dependabot composes this
# from a fixed template and cannot be made to emit the contract.
DEPENDABOT_BODY = """Bumps [github/gh-aw-actions/setup](https://github.com/github/gh-aw-actions) from 0.82.14 to 0.84.2.

Release notes
<p><em>Sourced from setup's releases.</em></p>
Commits
<ul><li>fd783ac chore: sync actions from gh-aw@v0.84.2</li></ul>
"""

_DRIVER = """
const fs = require('fs');
const source = fs.readFileSync(process.argv[2], 'utf8');
const pr = JSON.parse(process.argv[3]);

(async () => {
  const published = [];
  const context = {
    payload: { pull_request: pr },
    repo: { owner: 'groupthinking', repo: 'EventRelay' },
    runId: 1,
    serverUrl: 'https://github.com',
  };
  const core = { setFailed: () => {} };
  const github = {
    rest: {
      checks: { create: async (args) => { published.push(args); } },
      // Canonical issue resolves to a real, open, non-PR issue.
      issues: { get: async () => ({ data: { number: 1419, state: 'open' } }) },
      pulls: { list: 'list' },
    },
    paginate: async () => [],   // no competing PRs
  };
  const fn = new Function(
    'context', 'core', 'github',
    `return (async () => {${source}})();`
  );
  await fn(context, core, github);
  process.stdout.write(JSON.stringify({
    conclusion: published[0] && published[0].conclusion,
    title: published[0] && published[0].output && published[0].output.title,
  }));
})();
"""


def _run_gate(tmp_path: Path, pull_request: dict) -> dict:
    """Execute the real governance script against a synthetic PR payload."""
    script = _get_script(_load_workflow())
    source_path = tmp_path / "gov_source.js"
    source_path.write_text(script)
    driver_path = tmp_path / "driver.js"
    driver_path.write_text(textwrap.dedent(_DRIVER))

    result = subprocess.run(
        ["node", str(driver_path), str(source_path), json.dumps(pull_request)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"driver failed: {result.stderr}"
    return json.loads(result.stdout)


requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is required to execute the gate"
)


@requires_node
def test_gate_is_not_applicable_to_dependabot(tmp_path: Path) -> None:
    """Dependabot cannot author the contract, so the gate must not fail it.

    Regression guard for #1419: PR #1171 was permanently red on this check.
    """
    verdict = _run_gate(
        tmp_path,
        {
            "number": 1171,
            "draft": False,
            "user": {"login": "dependabot[bot]"},
            "body": DEPENDABOT_BODY,
            "head": {"sha": "bfb1bb7"},
        },
    )
    assert verdict["conclusion"] == "neutral"
    # "neutral", not "success": the contract is not applicable, not satisfied.
    assert "not applicable" in verdict["title"].lower()


@requires_node
def test_gate_still_fails_a_human_with_the_same_body(tmp_path: Path) -> None:
    """The exemption is keyed on author, not on body shape.

    Without this, a fix that simply stopped requiring the sections would also
    pass test_gate_is_not_applicable_to_dependabot.
    """
    verdict = _run_gate(
        tmp_path,
        {
            "number": 9001,
            "draft": False,
            "user": {"login": "groupthinking"},
            "body": DEPENDABOT_BODY,
            "head": {"sha": "deadbee"},
        },
    )
    assert verdict["conclusion"] == "failure"


@requires_node
def test_gate_still_fails_other_bots(tmp_path: Path) -> None:
    """Only automated dependency authors are exempt, not every bot."""
    verdict = _run_gate(
        tmp_path,
        {
            "number": 9003,
            "draft": False,
            "user": {"login": "google-labs-jules[bot]"},
            "body": DEPENDABOT_BODY,
            "head": {"sha": "abc0001"},
        },
    )
    assert verdict["conclusion"] == "failure"


@requires_node
def test_gate_passes_a_complete_contract(tmp_path: Path) -> None:
    verdict = _run_gate(
        tmp_path,
        {
            "number": 9002,
            "draft": False,
            "user": {"login": "groupthinking"},
            "body": CONTRACT_BODY,
            "head": {"sha": "cafe123"},
        },
    )
    assert verdict["conclusion"] == "success"


@requires_node
def test_gate_tolerates_a_missing_user_object(tmp_path: Path) -> None:
    """The author lookup must not throw when `user` is absent."""
    verdict = _run_gate(
        tmp_path,
        {
            "number": 9004,
            "draft": False,
            "body": CONTRACT_BODY,
            "head": {"sha": "f00d111"},
        },
    )
    assert verdict["conclusion"] == "success"
