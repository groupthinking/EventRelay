"""Guard against rot in scripts/deployment/one-click-deploy.sh.

The script's precheck aborts the whole deployment if any entry in its
REQUIRED_FILES array is missing, so a stale path makes the script
non-functional (see #1127, where two entries pointed at files that had
never existed and three more used pre-move ``k8s/...`` paths). This test
parses the array straight out of the script and asserts every entry
resolves from the repository root.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOY_SCRIPT = PROJECT_ROOT / "scripts" / "deployment" / "one-click-deploy.sh"


def _required_files(script_text: str) -> list[str]:
    match = re.search(r"REQUIRED_FILES=\((.*?)\)", script_text, re.DOTALL)
    assert match, "REQUIRED_FILES array not found in one-click-deploy.sh"
    return re.findall(r'"([^"]+)"', match.group(1))


def test_required_files_all_exist():
    assert DEPLOY_SCRIPT.exists(), f"{DEPLOY_SCRIPT} not found"

    entries = _required_files(DEPLOY_SCRIPT.read_text())
    assert entries, "REQUIRED_FILES is empty; the precheck validates nothing"

    missing = [entry for entry in entries if not (PROJECT_ROOT / entry).is_file()]
    assert not missing, (
        "REQUIRED_FILES in one-click-deploy.sh lists paths that do not exist "
        f"relative to the repo root: {missing}. The script exits on the first "
        "missing entry, so every path must resolve."
    )


def test_manifest_paths_in_script_exist():
    """Every ``-f <path>`` the script passes to kubectl/docker must resolve."""
    script_text = DEPLOY_SCRIPT.read_text()
    paths = re.findall(r"-f\s+((?:infrastructure|apps|k8s)/[\w./-]+)", script_text)
    assert paths, "No manifest/Dockerfile paths found in one-click-deploy.sh"

    missing = [p for p in paths if not (PROJECT_ROOT / p).exists()]
    assert not missing, (
        f"one-click-deploy.sh references nonexistent paths: {missing}"
    )
