from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_PACKAGE_JSON = REPO_ROOT / "package.json"
WEB_PACKAGE_JSON = REPO_ROOT / "apps/web/package.json"
PACKAGE_LOCK = REPO_ROOT / "package-lock.json"
SAFE_NEXT_VERSION = "15.5.24"


def _load_json(path: Path) -> dict:
    assert path.exists(), f"{path} should exist"
    return json.loads(path.read_text())


def test_nextjs_is_pinned_to_safe_version_in_manifests_and_lockfile() -> None:
    root_package = _load_json(ROOT_PACKAGE_JSON)
    web_package = _load_json(WEB_PACKAGE_JSON)
    package_lock = _load_json(PACKAGE_LOCK)

    assert root_package["devDependencies"]["next"] == SAFE_NEXT_VERSION
    assert root_package["overrides"]["next"] == SAFE_NEXT_VERSION
    assert web_package["dependencies"]["next"] == SAFE_NEXT_VERSION
    assert (
        package_lock["packages"][""]["devDependencies"]["next"] == SAFE_NEXT_VERSION
    )
    assert (
        package_lock["packages"]["apps/web"]["dependencies"]["next"]
        == SAFE_NEXT_VERSION
    )
    assert package_lock["packages"]["node_modules/next"]["version"] == SAFE_NEXT_VERSION
