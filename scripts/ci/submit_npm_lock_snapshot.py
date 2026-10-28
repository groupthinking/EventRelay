"""Submit every resolved npm lockfile version to GitHub's dependency graph.

Component Detection can omit a nested second version of one package.  Use the
lockfile's installed paths as unique keys so both versions reach the review API.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

CORRELATOR = "0-eventrelay-npm-lock-complete"


def _package_name(location: str, package: dict) -> str | None:
    name = package.get("name")
    if isinstance(name, str) and name:
        return name
    if "node_modules/" in location:
        return location.rsplit("node_modules/", 1)[1]
    return None


def _resolve_child(location: str, name: str, locations: set[str]) -> str | None:
    cursor = location
    while True:
        candidate = (
            f"{cursor}/node_modules/{name}" if cursor else f"node_modules/{name}"
        )
        if candidate in locations:
            return candidate
        if "/node_modules/" in cursor:
            cursor = cursor.rsplit("/node_modules/", 1)[0]
        elif cursor.startswith("node_modules/"):
            cursor = ""
        else:
            cursor = ""
        if not cursor:
            candidate = f"node_modules/{name}"
            return candidate if candidate in locations else None


def npm_manifest(lock: dict, location: str) -> dict:
    packages = lock.get("packages")
    if lock.get("lockfileVersion") not in {2, 3} or not isinstance(packages, dict):
        raise ValueError(f"Unsupported npm lockfile: {location}")
    direct_names: set[str] = set()
    for package_location, package in packages.items():
        if not isinstance(package_location, str) or not isinstance(package, dict):
            raise ValueError(
                f"Invalid npm lockfile entry: {location}:{package_location}"
            )
        if "node_modules/" in package_location:
            continue
        for field in ("dependencies", "devDependencies", "optionalDependencies"):
            direct_names.update(package.get(field, {}))

    entries: dict[str, tuple[str, str, dict]] = {}
    for package_location, package in packages.items():
        if "node_modules/" not in package_location:
            continue
        name = _package_name(package_location, package)
        version = package.get("version")
        if name and isinstance(version, str) and not package.get("link"):
            entries[package_location] = (name, version, package)

    keys = {
        path: f"{name}@{version}#{hashlib.sha256(path.encode()).hexdigest()[:12]}"
        for path, (name, version, _) in entries.items()
    }
    locations = set(entries)
    resolved = {}
    for path, (name, version, package) in entries.items():
        children = set()
        for field in ("dependencies", "optionalDependencies"):
            for child_name in package.get(field, {}):
                child = _resolve_child(path, child_name, locations)
                if child is not None:
                    children.add(keys[child])
        resolved[keys[path]] = {
            "package_url": f"pkg:npm/{quote(name, safe='/')}@{quote(version, safe='')}",
            "relationship": "direct" if name in direct_names else "indirect",
            "scope": "development" if package.get("dev") is True else "runtime",
            "dependencies": sorted(children),
        }
    return {
        "name": location,
        "file": {"source_location": location},
        "resolved": resolved,
    }


def tracked_npm_locks() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z", "*package-lock.json"],
        check=True,
        capture_output=True,
    ).stdout
    return [Path(os.fsdecode(path)) for path in output.split(b"\0") if path]


def submit_snapshot(environment: dict[str, str], opener=urlopen) -> dict:
    sha, ref = environment["SNAPSHOT_SHA"], environment["SNAPSHOT_REF"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not ref.startswith("refs/heads/"):
        raise ValueError("Snapshot requires an exact SHA and branch ref")
    repository = environment["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GitHub repository")
    manifests = {}
    for path in tracked_npm_locks():
        manifests[path.as_posix()] = npm_manifest(
            json.loads(path.read_text()), path.as_posix()
        )
    if not manifests:
        return {"snapshot_id": None, "manifest_count": 0, "package_count": 0}
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
            "name": "EventRelay complete npm lock",
            "version": "1",
            "url": f"https://github.com/{repository}/blob/{sha}/scripts/ci/submit_npm_lock_snapshot.py",
        },
        "scanned": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "manifests": manifests,
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
    return {
        "snapshot_id": result["id"],
        "manifest_count": len(manifests),
        "package_count": sum(len(item["resolved"]) for item in manifests.values()),
    }


if __name__ == "__main__":
    print(json.dumps(submit_snapshot(os.environ), sort_keys=True))
