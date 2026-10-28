"""Run the issue-closer gate against bot and human PR metadata."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github/workflows/require-issue-closer.yml"
)


@pytest.mark.parametrize(
    ("author", "head_repo", "head_ref", "body", "issue", "expected_pass"),
    [
        (
            "dependabot[bot]",
            "groupthinking/EventRelay",
            "dependabot/npm_and_yarn/ip-address-10.7.4",
            "",
            "",
            True,
        ),
        (
            "hayden",
            "groupthinking/EventRelay",
            "dependabot/npm_and_yarn/ip-address-10.7.4",
            "",
            "",
            False,
        ),
        (
            "dependabot[bot]",
            "another/EventRelay",
            "dependabot/npm_and_yarn/ip-address-10.7.4",
            "",
            "",
            False,
        ),
        (
            "dependabot[bot]",
            "groupthinking/EventRelay",
            "feature/no-issue",
            "",
            "",
            False,
        ),
        (
            "hayden",
            "groupthinking/EventRelay",
            "feature/has-issue",
            "Fixes #42",
            '{"state":"open","is_pr":"no"}',
            True,
        ),
        (
            "hayden",
            "groupthinking/EventRelay",
            "feature/closed-issue",
            "Fixes #42",
            '{"state":"closed","is_pr":"no"}',
            False,
        ),
    ],
)
def test_issue_closer_only_exempts_verified_dependabot_updates(
    tmp_path: Path,
    author: str,
    head_repo: str,
    head_ref: str,
    body: str,
    issue: str,
    expected_pass: bool,
) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    step = workflow["jobs"]["require-closing-keyword"]["steps"][0]
    assert step["name"] == "Verify Fixes/Closes targets an open issue"
    assert (
        workflow["jobs"]["require-closing-keyword"]["name"]
        == "Closing keyword to open issue"
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'case "$2" in\n'
        '  */pulls/*) printf "%s" "$GH_STUB_BODY" ;;\n'
        '  */issues/*) printf "%s" "$GH_STUB_ISSUE" ;;\n'
        "  *) exit 91 ;;\n"
        "esac\n"
    )
    gh.chmod(0o755)
    env = os.environ | {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GH_TOKEN": "test-only",
        "PR_NUMBER": "42",
        "REPO": "groupthinking/EventRelay",
        "PR_AUTHOR": author,
        "HEAD_REPO": head_repo,
        "HEAD_REF": head_ref,
        "GH_STUB_BODY": body,
        "GH_STUB_ISSUE": issue,
    }
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert (result.returncode == 0) is expected_pass, result.stdout + result.stderr
    if (
        author == "dependabot[bot]"
        and head_repo == env["REPO"]
        and head_ref.startswith("dependabot/")
    ):
        assert "verified same-repository Dependabot update" in result.stdout
    elif not expected_pass:
        assert "::error::" in result.stdout
