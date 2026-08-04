from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_JSON = ROOT / "package.json"
LOCKFILE = ROOT / "package-lock.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_brace_expansion_override_floors_exclude_oom_vulnerable_patches() -> None:
    package = _load_json(PACKAGE_JSON)
    overrides = package["overrides"]

    assert overrides["minimatch@3.1.5"]["brace-expansion"] == "^1.1.17"
    assert overrides["minimatch@9.0.9"]["brace-expansion"] == "^2.1.3"


def test_lockfile_nested_brace_expansion_resolutions_are_safe() -> None:
    lockfile = _load_json(LOCKFILE)
    packages = lockfile["packages"]

    minimatch_nested = packages["node_modules/minimatch/node_modules/brace-expansion"][
        "version"
    ]
    rimraf_nested = packages["node_modules/rimraf/node_modules/brace-expansion"][
        "version"
    ]

    assert tuple(map(int, minimatch_nested.split("."))) >= (1, 1, 17)
    assert tuple(map(int, rimraf_nested.split("."))) >= (2, 1, 3)
