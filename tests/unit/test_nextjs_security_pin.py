"""Regression tests for the repository's pinned Next.js version.

Critical RCE advisories affected previously allowed Next.js ranges. The fix for
this repository is to pin both workspace manifests and the generated root
lockfile to 15.5.24 so a fresh install cannot drift back to a vulnerable
release.
"""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_PACKAGE_JSON = REPO_ROOT / "package.json"
WEB_PACKAGE_JSON = REPO_ROOT / "apps/web/package.json"
PACKAGE_LOCK = REPO_ROOT / "package-lock.json"
PINNED_NEXT_VERSION = "15.5.24"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_nextjs_is_pinned_in_workspace_manifests_and_lockfile() -> None:
    root_pkg = _load_json(ROOT_PACKAGE_JSON)
    web_pkg = _load_json(WEB_PACKAGE_JSON)
    lock = _load_json(PACKAGE_LOCK)

    assert root_pkg["devDependencies"]["next"] == PINNED_NEXT_VERSION
    assert root_pkg["overrides"]["next"] == PINNED_NEXT_VERSION
    assert web_pkg["dependencies"]["next"] == PINNED_NEXT_VERSION
    assert web_pkg["devDependencies"]["eslint-config-next"] == PINNED_NEXT_VERSION
    assert lock["packages"][""]["devDependencies"]["next"] == PINNED_NEXT_VERSION
    assert lock["packages"]["apps/web"]["dependencies"]["next"] == PINNED_NEXT_VERSION
    assert (
        lock["packages"]["apps/web"]["devDependencies"]["eslint-config-next"]
        == PINNED_NEXT_VERSION
    )
    assert lock["packages"]["node_modules/next"]["version"] == PINNED_NEXT_VERSION
    assert (
        lock["packages"]["apps/web/node_modules/eslint-config-next"]["version"]
        == PINNED_NEXT_VERSION
    )
