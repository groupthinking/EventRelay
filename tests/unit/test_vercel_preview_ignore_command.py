from __future__ import annotations

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import json


REPO_ROOT = Path(__file__).resolve().parents[2]
APPS_WEB_VERCEL = REPO_ROOT / "apps/web/vercel.json"
IGNORE_SCRIPT = REPO_ROOT / "scripts/deployment/vercel-ignore-command.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _run_ignore(repo: Path) -> int:
    env = os.environ.copy()
    env["VERCEL_GIT_COMMIT_SHA"] = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
        )
        .stdout.strip()
    )
    env["VERCEL_GIT_PREVIOUS_SHA"] = (
        subprocess.run(
            ["git", "rev-parse", "HEAD~1"], cwd=repo, check=True, capture_output=True, text=True
        )
        .stdout.strip()
    )
    result = subprocess.run(
        ["bash", str(IGNORE_SCRIPT)],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode


def test_apps_web_vercel_uses_ignore_command() -> None:
    cfg = json.loads(APPS_WEB_VERCEL.read_text(encoding="utf-8"))
    assert cfg.get("ignoreCommand"), "apps/web/vercel.json should define ignoreCommand"
    assert "vercel-ignore-command.sh" in cfg["ignoreCommand"]


def test_ignore_script_skips_docs_only_changes() -> None:
    assert IGNORE_SCRIPT.exists(), "vercel ignore command script should exist"

    with TemporaryDirectory() as td:
        repo = Path(td)
        _git(repo, "init")
        _git(repo, "config", "user.email", "test@example.com")
        _git(repo, "config", "user.name", "test")
        _git(repo, "branch", "-m", "main")

        (repo / "docs").mkdir(parents=True)
        (repo / ".github/workflows").mkdir(parents=True)
        (repo / "apps/web/src").mkdir(parents=True)

        (repo / "docs/intro.md").write_text("base\n", encoding="utf-8")
        (repo / ".github/workflows/ci.yml").write_text("name: ci\n", encoding="utf-8")
        (repo / "apps/web/src/page.tsx").write_text("export default function Page(){}\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "base")

        (repo / "docs/intro.md").write_text("changed\n", encoding="utf-8")
        (repo / ".github/workflows/ci.yml").write_text("name: ci\non: pull_request\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "docs and workflow only")
        assert _run_ignore(repo) == 0


def test_ignore_script_keeps_preview_for_web_changes() -> None:
    with TemporaryDirectory() as td:
        repo = Path(td)
        _git(repo, "init")
        _git(repo, "config", "user.email", "test@example.com")
        _git(repo, "config", "user.name", "test")
        _git(repo, "branch", "-m", "main")

        (repo / "apps/web/src").mkdir(parents=True)
        (repo / "apps/web/src/page.tsx").write_text("export default function Page(){}\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "base")

        (repo / "apps/web/src/page.tsx").write_text("export default function Page(){return null}\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "web change")
        assert _run_ignore(repo) == 1
