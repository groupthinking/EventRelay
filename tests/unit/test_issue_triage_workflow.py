from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
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


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_issue_triage_closes_generic_linear_bot_shells(tmp_path: Path) -> None:
    script = _get_script(_load_workflow())
    script_path = tmp_path / "issue_triage.js"
    script_path.write_text(script)

    harness = tmp_path / "harness.mjs"
    harness.write_text(
        textwrap.dedent(
            """
            import fs from 'fs';

            const script = fs.readFileSync(process.argv[2], 'utf8');
            const issue = {
              number: 1522,
              title: 'Addressing Issues',
              body: '<!-- linear-linkback -->\\n<p><a href="https://linear.app/myxstack/issue/GRV-403">GRV-403</a></p>',
              user: { type: 'Bot' },
            };

            const outcome = { comments: [], labels: null, update: null };
            const github = {
              rest: {
                issues: {
                  addLabels: async (payload) => { outcome.labels = payload.labels; },
                  createComment: async (payload) => { outcome.comments.push(payload.body); },
                  update: async (payload) => { outcome.update = payload; },
                },
              },
            };
            const context = {
              repo: { owner: 'groupthinking', repo: 'EventRelay' },
              payload: { issue },
            };

            await new Function(
              'github', 'context',
              `return (async () => { ${script} })()`
            )(github, context);

            process.stdout.write(JSON.stringify(outcome));
            """
        ).strip()
    )

    result = subprocess.run(
        ["node", str(harness), str(script_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"harness failed: {result.stderr}"

    outcome = json.loads(result.stdout)
    assert outcome["labels"] is None
    assert outcome["update"] is not None
    assert outcome["update"]["state"] == "closed"
    assert outcome["update"]["state_reason"] == "not_planned"
    assert any("Closing automatically" in body for body in outcome["comments"])
