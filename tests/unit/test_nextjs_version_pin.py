from __future__ import annotations

import json
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_JSON = REPO_ROOT / "package.json"
WEB_PACKAGE_JSON = REPO_ROOT / "apps/web/package.json"
PACKAGE_LOCK = REPO_ROOT / "package-lock.json"
NEXT_VERSION = "15.5.24"


def _load_json(path: Path) -> dict:
    assert path.exists(), f"{path} should exist"
    return json.loads(path.read_text())


class NextVersionPinTest(unittest.TestCase):
    def test_active_manifests_pin_nextjs_15524(self) -> None:
        root_package = _load_json(PACKAGE_JSON)
        web_package = _load_json(WEB_PACKAGE_JSON)

        self.assertEqual(root_package["devDependencies"]["next"], NEXT_VERSION)
        self.assertEqual(root_package["overrides"]["next"], NEXT_VERSION)
        self.assertEqual(web_package["dependencies"]["next"], NEXT_VERSION)
        self.assertEqual(
            web_package["devDependencies"]["eslint-config-next"], NEXT_VERSION
        )

    def test_workspace_lockfile_resolves_pinned_nextjs_15524(self) -> None:
        packages = _load_json(PACKAGE_LOCK)["packages"]

        self.assertEqual(packages[""]["devDependencies"]["next"], NEXT_VERSION)
        self.assertEqual(packages["apps/web"]["dependencies"]["next"], NEXT_VERSION)
        self.assertEqual(
            packages["apps/web"]["devDependencies"]["eslint-config-next"], NEXT_VERSION
        )
        self.assertEqual(packages["node_modules/next"]["version"], NEXT_VERSION)
        self.assertEqual(
            packages["apps/web/node_modules/eslint-config-next"]["version"],
            NEXT_VERSION,
        )
