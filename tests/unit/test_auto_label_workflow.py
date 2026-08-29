"""Regression tests for the Auto Label workflow.

Both defects these cover were silent: an unknown `pull_request` activity type is
ignored rather than rejected, and an unpaginated `listFiles` still concludes
green on a truncated diff. Neither produced a red check, so static assertions
alone would not have caught them — the pagination test below executes the
workflow's own embedded script and fails against the previous implementation.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/auto-label.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "Auto Label workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _get_script(workflow: dict) -> str:
    return workflow["jobs"]["label"]["steps"][0]["with"]["script"]


def test_auto_label_workflow_file_is_valid_yaml() -> None:
    workflow = _load_workflow()
    assert workflow["name"] == "Auto Label"


def test_auto_label_triggers_on_synchronize_not_synchronized() -> None:
    """`synchronized` is not a GitHub activity type; the real one is `synchronize`.

    GitHub ignores unknown activity types instead of rejecting the workflow, so
    the typo silently stopped the workflow from ever running on a push to an
    open PR.
    """
    workflow = _load_workflow()
    # PyYAML parses the YAML 'on' key as Python True.
    types = workflow[True]["pull_request"]["types"]
    assert "synchronize" in types
    assert "synchronized" not in types
    assert "opened" in types
    assert "reopened" in types


def test_auto_label_paginates_changed_files() -> None:
    """`pulls.listFiles` defaults to 30 per page; a larger PR must not truncate."""
    script = _get_script(_load_workflow())
    assert "github.paginate" in script
    assert "per_page: 100" in script


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_auto_label_labels_files_beyond_the_first_page(tmp_path: Path) -> None:
    """Execute the workflow's embedded script over a 120-file diff.

    The 120th file is the only `.py` in the diff, so the `python` label can only
    appear if the listing paginated past the first page. The mocked client
    raises if the unpaginated `pulls.listFiles` is called at all, which is what
    makes this fail against the previous implementation rather than pass
    vacuously.
    """
    script = _get_script(_load_workflow())
    script_path = tmp_path / "auto_label.js"
    script_path.write_text(script)

    harness = tmp_path / "harness.mjs"
    harness.write_text(textwrap.dedent("""
            import fs from 'fs';
            const script = fs.readFileSync(process.argv[2], 'utf8');

            const files = [];
            for (let i = 0; i < 119; i++) files.push({ filename: `apps/web/src/x${i}.ts` });
            files.push({ filename: 'src/late.py' });  // only reachable via pagination

            let added = null;
            const github = {
              paginate: async (_fn, opts) => {
                if (opts.per_page !== 100) throw new Error('per_page not set to 100');
                return files;
              },
              rest: {
                pulls: {
                  listFiles: async () => {
                    throw new Error('unpaginated listFiles called');
                  },
                },
                issues: { addLabels: async (o) => { added = o.labels; } },
              },
            };
            const context = {
              eventName: 'pull_request',
              repo: { owner: 'o', repo: 'r' },
              payload: { pull_request: { number: 1 } },
            };
            const core = { warning: () => {} };

            await new Function(
              'github', 'context', 'core',
              `return (async () => { ${script} })()`
            )(github, context, core);

            process.stdout.write(JSON.stringify(added ?? []));
            """).strip())

    result = subprocess.run(
        ["node", str(harness), str(script_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"harness failed: {result.stderr}"

    labels = json.loads(result.stdout)
    assert "python" in labels, (
        "the 120th changed file was not labelled, so the changed-file listing "
        "was truncated to the first page"
    )
    assert "javascript" in labels
