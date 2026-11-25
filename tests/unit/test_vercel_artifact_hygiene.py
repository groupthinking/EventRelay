from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_root_gitignore_blocks_vercel_build_and_diagnostic_artifacts() -> None:
    source = (ROOT / ".gitignore").read_text()

    assert ".vercel" in source
    assert "vercel-debug.log*" in source
