"""Regression coverage for scripts/maintenance/branch-cleanup-delete.sh.

Locks in the fix for the ``stale`` batch, which previously fell through to
the script's ``usage: ... {safe|review}`` error path with ``exit 2`` because
``STALE_BRANCHES`` and the corresponding ``stale)`` case were missing, even
though the ``Branch Cleanup`` workflow (workflow_dispatch options and the
``[run-cleanup:stale]`` sentinel-commit regex) has always offered ``stale``
as a selectable batch.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "maintenance"
    / "branch-cleanup-delete.sh"
)


def _run(*args: str, dry_run: bool = True) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin"}
    if dry_run:
        env["DRY_RUN"] = "1"
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="bash script not runnable on Windows"
)
class TestBranchCleanupDeleteScript:
    def test_script_is_syntactically_valid(self):
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr

    def test_stale_batch_exits_zero(self):
        """Regression: `stale` must no longer hit the usage/exit-2 fallback."""
        result = _run("stale")
        assert result.returncode == 0, result.stderr

    def test_safe_batch_still_exits_zero(self):
        result = _run("safe")
        assert result.returncode == 0, result.stderr

    def test_review_batch_still_exits_zero(self):
        result = _run("review")
        assert result.returncode == 0, result.stderr

    def test_unknown_batch_still_rejected_with_exit_2(self):
        result = _run("bogus")
        assert result.returncode == 2
        assert "usage:" in result.stdout

    def test_no_batch_still_rejected_with_exit_2(self):
        result = _run()
        assert result.returncode == 2
        assert "usage:" in result.stdout

    def test_usage_string_documents_stale_option(self):
        result = _run("bogus")
        assert "{safe|stale|review}" in result.stdout
