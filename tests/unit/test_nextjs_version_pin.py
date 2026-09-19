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
    if not path.exists():
        raise FileNotFoundError(f"{path} should exist")
    return json.loads(path.read_text(encoding="utf-8"))


def _lockfile_package_entries(packages: dict, package_name: str) -> dict[str, dict]:
    suffix = f"node_modules/{package_name}"
    return {
        package_path: package_data
        for package_path, package_data in packages.items()
        if package_path == suffix or package_path.endswith(f"/{suffix}")
    }


class NextVersionPinTest(unittest.TestCase):
    def test_active_manifests_pin_next_version(self) -> None:
        root_package = _load_json(PACKAGE_JSON)
        web_package = _load_json(WEB_PACKAGE_JSON)

        self.assertEqual(root_package["devDependencies"]["next"], NEXT_VERSION)
        self.assertEqual(root_package["overrides"]["next"], NEXT_VERSION)
        self.assertEqual(web_package["dependencies"]["next"], NEXT_VERSION)
        self.assertEqual(
            web_package["devDependencies"]["eslint-config-next"], NEXT_VERSION
        )

    def test_workspace_lockfile_resolves_pinned_next_version(self) -> None:
        packages = _load_json(PACKAGE_LOCK)["packages"]

        self.assertEqual(packages[""]["devDependencies"]["next"], NEXT_VERSION)
        self.assertEqual(packages["apps/web"]["dependencies"]["next"], NEXT_VERSION)
        self.assertEqual(
            packages["apps/web"]["devDependencies"]["eslint-config-next"], NEXT_VERSION
        )
        for package_name in ("next", "eslint-config-next"):
            entries = _lockfile_package_entries(packages, package_name)
            self.assertTrue(entries, f"Expected {package_name} in package-lock packages")
            for package_path, package_data in entries.items():
                with self.subTest(package_path=package_path):
                    self.assertEqual(package_data["version"], NEXT_VERSION)
