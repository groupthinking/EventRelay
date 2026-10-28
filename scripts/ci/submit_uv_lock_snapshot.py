"""Submit a uv.lock snapshot with scopes derived from the editable project root.

Component Detection currently treats an editable uv root as an ordinary package,
so its uv detector marks every package as runtime. This submission gives GitHub
the lockfile's actual runtime and development reachability for that manifest.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import tomllib
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

DEVELOPMENT_EXTRAS = frozenset({"dev", "docs"})
CORRELATOR = "0-eventrelay-uv-lock-scoped"


def _reachable(roots: set[str], packages_by_name: dict[str, list[dict]]) -> set[str]:
    visited: set[str] = set()
    pending = deque(roots)
    while pending:
        name = pending.popleft()
        if name in visited:
            continue
        visited.add(name)
        for package in packages_by_name.get(name, []):
            pending.extend(dependency["name"] for dependency in package.get("dependencies", []))
    return visited


def uv_manifest(lock: dict, location: str = "uv.lock") -> dict:
    if lock.get("version") != 1 or not isinstance(lock.get("package"), list):
        raise ValueError("Unsupported uv.lock format")
    packages = lock["package"]
    roots = [
        package for package in packages
        if "editable" in package.get("source", {}) or "virtual" in package.get("source", {})
    ]
    if len(roots) != 1:
        raise ValueError(f"Expected one uv project root; found {len(roots)}")
    root = roots[0]
    packages_by_name: dict[str, list[dict]] = defaultdict(list)
    for package in packages:
        packages_by_name[package["name"]].append(package)

    direct_runtime = {dependency["name"] for dependency in root.get("dependencies", [])}
    direct_development: set[str] = set()
    for extra, dependencies in root.get("optional-dependencies", {}).items():
        target = direct_development if extra in DEVELOPMENT_EXTRAS else direct_runtime
        target.update(dependency["name"] for dependency in dependencies)
    for group, dependencies in root.get("dev-dependencies", {}).items():
        target = direct_development if group in DEVELOPMENT_EXTRAS else direct_runtime
        target.update(dependency["name"] for dependency in dependencies)

    runtime = _reachable(direct_runtime, packages_by_name)
    development = _reachable(direct_development, packages_by_name)
    resolved = {}
    for package in packages:
        if "registry" not in package.get("source", {}):
            continue
        name, version = package["name"], package["version"]
        key = f"{name}@{version}"
        if key in resolved:
            raise ValueError(f"Duplicate uv package: {key}")
        dependency_keys = set()
        for dependency in package.get("dependencies", []):
            candidates = packages_by_name.get(dependency["name"], [])
            if "version" in dependency:
                candidates = [item for item in candidates if item["version"] == dependency["version"]]
            if not candidates:
                raise ValueError(f"Unresolved uv dependency: {name} -> {dependency['name']}")
            dependency_keys.update(
                f"{item['name']}@{item['version']}"
                for item in candidates if "registry" in item.get("source", {})
            )
        entry = {
            "package_url": f"pkg:pypi/{quote(name, safe='')}@{quote(version, safe='')}",
            "relationship": "direct" if name in direct_runtime | direct_development else "indirect",
            "scope": "development" if name in development and name not in runtime else "runtime",
            "dependencies": sorted(dependency_keys),
        }
        resolved[key] = entry
    return {"name": location, "file": {"source_location": location}, "resolved": resolved}


def submit_snapshot(lock_path: Path, environment: dict[str, str], opener=urlopen) -> dict:
    sha, ref = environment["SNAPSHOT_SHA"], environment["SNAPSHOT_REF"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not ref.startswith("refs/heads/"):
        raise ValueError("Snapshot requires an exact SHA and branch ref")
    repository = environment["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GitHub repository")
    with lock_path.open("rb") as stream:
        manifest = uv_manifest(tomllib.load(stream), lock_path.as_posix())
    snapshot = {
        "version": 0,
        "sha": sha,
        "ref": ref,
        "job": {
            "correlator": CORRELATOR,
            "id": environment["GITHUB_RUN_ID"],
            "html_url": f"https://github.com/{repository}/actions/runs/{environment['GITHUB_RUN_ID']}",
        },
        "detector": {
            "name": "EventRelay uv lock scope",
            "version": "1",
            "url": f"https://github.com/{repository}/blob/{sha}/scripts/ci/submit_uv_lock_snapshot.py",
        },
        "scanned": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "manifests": {lock_path.as_posix(): manifest},
    }
    request = Request(
        f"https://api.github.com/repos/{repository}/dependency-graph/snapshots",
        data=json.dumps(snapshot, separators=(",", ":")).encode(),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {environment['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    with opener(request, timeout=90) as response:
        result = json.load(response)
    if not isinstance(result, dict) or not result.get("id"):
        raise ValueError("GitHub did not return a dependency snapshot ID")
    return {"snapshot_id": result["id"], "package_count": len(manifest["resolved"])}


if __name__ == "__main__":
    print(json.dumps(submit_snapshot(Path("uv.lock"), os.environ), sort_keys=True))
