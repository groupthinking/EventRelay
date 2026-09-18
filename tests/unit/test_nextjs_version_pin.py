from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PINNED_NEXT_VERSION = "15.5.24"


def _load_json(relative_path: str) -> dict:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_nextjs_is_pinned_in_workspace_manifests_and_lockfile() -> None:
    root_package = _load_json("package.json")
    web_package = _load_json("apps/web/package.json")
    lockfile = _load_json("package-lock.json")

    assert root_package["devDependencies"]["next"] == PINNED_NEXT_VERSION
    assert root_package["overrides"]["next"] == PINNED_NEXT_VERSION
    assert web_package["dependencies"]["next"] == PINNED_NEXT_VERSION

    packages = lockfile["packages"]
    assert packages[""]["devDependencies"]["next"] == PINNED_NEXT_VERSION
    assert packages["apps/web"]["dependencies"]["next"] == PINNED_NEXT_VERSION
    assert packages["node_modules/next"]["version"] == PINNED_NEXT_VERSION
