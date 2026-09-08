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
def test_issue_triage_closes_linear_linkback_only_bot_shells(tmp_path: Path) -> None:
    script = _get_script(_load_workflow())
    script_path = tmp_path / "issue_triage.js"
    script_path.write_text(script)

    harness = tmp_path / "harness.mjs"
    harness.write_text(
        textwrap.dedent(
            """
            import fs from 'fs';
            const script = fs.readFileSync(process.argv[2], 'utf8');

            const calls = { addLabels: 0, update: 0, comments: [] };
            const github = {
              rest: {
                issues: {
                  addLabels: async () => { calls.addLabels += 1; },
                  update: async () => { calls.update += 1; },
                  createComment: async (payload) => { calls.comments.push(payload.body); },
                },
              },
            };

            const context = {
              repo: { owner: 'o', repo: 'r' },
              payload: {
                issue: {
                  number: 1553,
                  title: 'Addressing Issues',
                  body: '<!-- linear-linkback -->\\n<p><a href="https://linear.app/myxstack/issue/GRV-423">GRV-423</a></p>',
                  user: { type: 'Bot' },
                },
              },
            };

            await new Function(
              'github', 'context',
              `return (async () => { ${script} })()`
            )(github, context);

            process.stdout.write(JSON.stringify(calls));
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

    calls = json.loads(result.stdout)
    assert calls["update"] == 1, "linkback-only bot shells should be auto-closed"
    assert calls["addLabels"] == 0, "auto-closed bot shells must not be triage-labeled"
    assert any(
        "Closing automatically" in comment for comment in calls["comments"]
    ), "auto-close comment should be posted"
