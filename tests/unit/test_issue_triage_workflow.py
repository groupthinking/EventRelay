from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/issue-triage.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "Issue triage workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _get_script(workflow: dict) -> str:
    return workflow["jobs"]["triage"]["steps"][0]["with"]["script"]


def test_issue_triage_workflow_file_is_valid_yaml() -> None:
    workflow = _load_workflow()
    assert workflow["name"] == "Issue Triage"


def test_issue_triage_closes_blank_bot_issues_before_labeling() -> None:
    script = _get_script(_load_workflow())
    assert "issue.user &&" in script
    assert "Addressing Issues" in script
    assert "state_reason: 'not_planned'" in script


def test_issue_triage_closes_generic_addressing_issues_shells() -> None:
    script = _get_script(_load_workflow())
    script_path = Path("/tmp/issue_triage_test.js")
    script_path.write_text(script)

    harness = textwrap.dedent(
        """
        const fs = require('fs');
        const path = process.argv[1];
        const script = fs.readFileSync(path, 'utf8');
        const calls = { comments: [], update: [], labels: [] };
        const github = {
          rest: {
            issues: {
              createComment: async (args) => calls.comments.push(args),
              update: async (args) => calls.update.push(args),
              addLabels: async (args) => calls.labels.push(args),
            },
          },
        };
        const context = {
          repo: { owner: 'o', repo: 'r' },
          payload: {
            issue: {
              number: 42,
              title: 'Addressing Issues',
              body: '   ',
              user: { type: 'Bot' },
            },
          },
        };
        const core = { warning: () => {} };
        (async () => {
          await new Function('github', 'context', 'core', `return (async () => { ${script} })()`)(github, context, core);
          process.stdout.write(JSON.stringify(calls));
        })().catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """
    )
    result = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["comments"]
    assert payload["update"][0]["state"] == "closed"
    assert payload["update"][0]["state_reason"] == "not_planned"
    assert not payload["labels"]
    script_path.unlink(missing_ok=True)
