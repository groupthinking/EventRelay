"""Save the complete GitHub dependency diff without Actions output expansion."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen


def _changed_files(base: str, head: str) -> set[str]:
    output = subprocess.run(
        ["git", "diff", "--name-only", "-z", base, head],
        check=True,
        capture_output=True,
    ).stdout
    return {os.fsdecode(path) for path in output.split(b"\0") if path}


def _npm_lock_components(sha: str, manifest: str) -> set[tuple[str, str, str]]:
    result = subprocess.run(["git", "show", f"{sha}:{manifest}"], capture_output=True)
    if result.returncode:
        # A newly added or deleted lockfile is absent on one side of the diff.
        return set()
    lock = json.loads(result.stdout)
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise ValueError(f"Invalid npm lockfile in {sha}:{manifest}")
    components = set()
    for location, package in packages.items():
        if not isinstance(location, str) or not isinstance(package, dict):
            raise ValueError(f"Invalid npm lockfile entry in {sha}:{manifest}")
        name = package.get("name")
        if not name and "node_modules/" in location:
            name = location.rsplit("node_modules/", 1)[1]
        version = package.get("version")
        if isinstance(name, str) and isinstance(version, str):
            scope = "development" if package.get("dev") is True else "runtime"
            components.add((name, version, scope))
    return components


def _validate_changes(
    changes: list[dict], base: str, head: str, changed_files: set[str]
) -> None:
    npm_locks: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    for change in changes:
        manifest = change.get("manifest")
        if not isinstance(manifest, str) or manifest not in changed_files:
            raise ValueError(
                "Dependency graph includes a change in an unchanged manifest: "
                f"{manifest!r}"
            )
        if change.get("ecosystem") != "npm" or not manifest.endswith(
            "package-lock.json"
        ):
            continue
        name, version, scope = (
            change.get("name"),
            change.get("version"),
            change.get("scope"),
        )
        if not all(isinstance(value, str) for value in (name, version, scope)):
            raise ValueError("npm dependency change lacks name, version, or scope")
        for sha in (base, head):
            if (sha, manifest) not in npm_locks:
                npm_locks[(sha, manifest)] = _npm_lock_components(sha, manifest)
        component = (name, version, scope)
        on_base = component in npm_locks[(base, manifest)]
        on_head = component in npm_locks[(head, manifest)]
        kind = change.get("change_type")
        if kind == "added" and on_head and not on_base:
            continue
        if kind == "removed" and on_base and not on_head:
            continue
        raise ValueError(
            "npm dependency change does not match lockfile version/scope: "
            f"{manifest} {name}@{version} {scope} {kind}"
        )


def record_dependency_review(
    environment: dict[str, str],
    destination: Path,
    opener=urlopen,
    changed_files: set[str] | None = None,
) -> dict:
    base = environment["BASE_SHA"]
    head = environment["HEAD_SHA"]
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (base, head)):
        raise ValueError("Dependency review requires exact commit SHAs")

    repository = environment["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GitHub repository")

    api_root = environment.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    url = f"{api_root}/repos/{repository}/dependency-graph/compare/{base}...{head}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {environment['GITHUB_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with opener(request, timeout=90) as response:
        raw_diff = response.read()
        snapshot_warning = response.headers.get(
            "x-github-dependency-graph-snapshot-warnings"
        )
    if snapshot_warning:
        raise ValueError(
            "Dependency graph reported snapshot warnings; refusing to save "
            "an incomplete comparison as review evidence"
        )
    changes = json.loads(raw_diff)
    if not isinstance(changes, list) or not all(
        isinstance(item, dict) for item in changes
    ):
        raise ValueError("Dependency diff API did not return a complete change list")
    if changes:
        _validate_changes(
            changes,
            base,
            head,
            changed_files if changed_files is not None else _changed_files(base, head),
        )

    destination.mkdir(parents=True, exist_ok=True)
    (destination / "dependency-diff.json").write_bytes(raw_diff)
    evidence = {
        "schema_version": 2,
        "base_sha": base,
        "head_sha": head,
        "run_id": environment["GITHUB_RUN_ID"],
        "run_attempt": environment["GITHUB_RUN_ATTEMPT"],
        "review_outcome": environment["REVIEW_OUTCOME"],
        "dependency_diff_source": url,
        "dependency_diff_count": len(changes),
        "dependency_diff_sha256": hashlib.sha256(raw_diff).hexdigest(),
        "dependency_diff_file": "dependency-diff.json",
    }
    (destination / "review.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


if __name__ == "__main__":
    result = record_dependency_review(os.environ, Path("dependency-review-evidence"))
    print(f"Saved {result['dependency_diff_count']} dependency changes")
