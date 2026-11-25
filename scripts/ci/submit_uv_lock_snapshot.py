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
PackageId = tuple[str, str, str]


def _package_id(package: dict) -> PackageId:
    return (
        package["name"], package["version"],
        json.dumps(package["source"], sort_keys=True, separators=(",", ":")),
    )


def _resolve_dependency(dependency: dict, packages_by_name: dict[str, list[dict]]) -> dict:
    candidates = [
        package for package in packages_by_name.get(dependency["name"], [])
        if all(field not in dependency or package[field] == dependency[field]
               for field in ("version", "source"))
    ]
    if not candidates:
        raise ValueError(f"Unresolved uv dependency: {dependency!r}")
    if len(candidates) != 1:
        raise ValueError(f"Ambiguous uv dependency: {dependency!r}")
    return candidates[0]


def _reachable(
    roots: list[dict], packages_by_name: dict[str, list[dict]]
) -> dict[PackageId, set[str]]:
    # Extras are traversal state, not part of a locked package's identity.
    # Keep each scope's requested extras separate even for a shared package.
    visited: set[tuple[PackageId, tuple[str, ...]]] = set()
    reachable: dict[PackageId, set[str]] = defaultdict(set)
    pending = deque(roots)
    while pending:
        dependency = pending.popleft()
        package = _resolve_dependency(dependency, packages_by_name)
        identity = _package_id(package)
        extras = tuple(sorted(set(dependency.get("extra", []))))
        if (identity, extras) in visited:
            continue
        visited.add((identity, extras))
        reachable[identity].update(extras)
        pending.extend(package.get("dependencies", []))
        for extra in extras:
            pending.extend(package.get("optional-dependencies", {}).get(extra, []))
    return reachable


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
    package_ids = set()
    registry_ids: dict[tuple[str, str], list[PackageId]] = defaultdict(list)
    for package in packages:
        identity = _package_id(package)
        if identity in package_ids:
            raise ValueError(f"Duplicate uv package: {identity!r}")
        package_ids.add(identity)
        packages_by_name[package["name"]].append(package)
        if "registry" in package["source"]:
            registry_ids[identity[:2]].append(identity)
    # Preserve existing keys for ordinary locks, but do not collapse distinct
    # sources of the same name/version into one scope or adjacency list.
    keys = {
        identity: f"{name}@{version}" + (
            f"?source={quote(identity[2], safe='')}" if len(identities) > 1 else ""
        )
        for (name, version), identities in registry_ids.items()
        for identity in identities
    }

    runtime_roots = list(root.get("dependencies", []))
    development_roots: list[dict] = []
    for extra, dependencies in root.get("optional-dependencies", {}).items():
        target = development_roots if extra in DEVELOPMENT_EXTRAS else runtime_roots
        target.extend(dependencies)
    for group, dependencies in root.get("dev-dependencies", {}).items():
        target = development_roots if group in DEVELOPMENT_EXTRAS else runtime_roots
        target.extend(dependencies)

    direct = {
        _package_id(_resolve_dependency(dependency, packages_by_name))
        for dependency in runtime_roots + development_roots
    }
    runtime = _reachable(runtime_roots, packages_by_name)
    development = _reachable(development_roots, packages_by_name)
    resolved = {}
    for package in packages:
        if "registry" not in package.get("source", {}):
            continue
        identity = _package_id(package)
        name, version = package["name"], package["version"]
        key = keys[identity]
        dependency_keys = set()
        dependencies = list(package.get("dependencies", []))
        for extra in runtime.get(identity, set()) | development.get(identity, set()):
            dependencies.extend(package.get("optional-dependencies", {}).get(extra, []))
        for dependency in dependencies:
            target = _package_id(_resolve_dependency(dependency, packages_by_name))
            if target in keys:
                dependency_keys.add(keys[target])
        entry = {
            "package_url": f"pkg:pypi/{quote(name, safe='')}@{quote(version, safe='')}",
            "relationship": "direct" if identity in direct else "indirect",
            "scope": "development" if identity in development and identity not in runtime else "runtime",
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
