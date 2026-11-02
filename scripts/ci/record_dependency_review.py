"""Save the complete GitHub dependency diff without Actions output expansion."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qsl, urljoin, urlsplit
from urllib.request import Request, urlopen

from scripts.ci.submit_uv_lock_snapshot import uv_manifest


def _changed_files(base: str, head: str) -> set[str]:
    merge_base = subprocess.run(
        ["git", "merge-base", base, head],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    output = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", merge_base, head],
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
    components: dict[tuple[str, str], str] = {}
    for location, package in packages.items():
        if not isinstance(location, str) or not isinstance(package, dict):
            raise ValueError(f"Invalid npm lockfile entry in {sha}:{manifest}")
        if "node_modules/" not in location:
            continue
        name = package.get("name")
        if not name and "node_modules/" in location:
            name = location.rsplit("node_modules/", 1)[1]
        version = package.get("version")
        if isinstance(name, str) and isinstance(version, str):
            scope = "development" if package.get("dev") is True else "runtime"
            identity = (name, version)
            if identity not in components or scope == "runtime":
                components[identity] = scope
    return {(name, version, scope) for (name, version), scope in components.items()}


def _uv_lock_components(sha: str, manifest: str) -> set[tuple[str, str, str]]:
    result = subprocess.run(["git", "show", f"{sha}:{manifest}"], capture_output=True)
    if result.returncode:
        return set()
    lock = tomllib.loads(result.stdout.decode())
    resolved = uv_manifest(lock, manifest)["resolved"]
    return {
        (key.rsplit("@", 1)[0], key.rsplit("@", 1)[1], package["scope"])
        for key, package in resolved.items()
    }


def _unchanged_requirements_resolution(
    manifest: str, changes: list[dict], base: str, head: str
) -> dict:
    """Prove unchanged, self-contained source; retain the resolver's entire delta.

    An unlocked pip scan can choose a newer transitive release at the same
    source commit. This proof does not establish repeatable Python resolution
    or waive the dependency-review action's vulnerability/license verdict.
    """

    def reject(reason: str) -> None:
        raise ValueError(
            "Dependency graph includes an unverified change in an unchanged manifest: "
            f"{manifest!r} ({reason})"
        )

    path = PurePosixPath(manifest)
    if (
        path.is_absolute()
        or path.as_posix() != manifest
        or ".." in path.parts
        or any(ord(character) < 32 for character in manifest)
        or not re.fullmatch(r"requirements[A-Za-z0-9_.-]*\.(txt|in)", path.name)
    ):
        reject("not a supported requirements path")

    entries = []
    for sha in (base, head):
        result = subprocess.run(
            ["git", "--literal-pathspecs", "ls-tree", "-z", sha, "--", manifest],
            capture_output=True,
        )
        entries_on_side = [entry for entry in result.stdout.split(b"\0") if entry]
        if result.returncode or len(entries_on_side) != 1:
            reject("source is missing or unreadable")
        fields = entries_on_side[0].split(b"\t", 1)[0].split()
        if (
            len(fields) != 3
            or fields[0] not in {b"100644", b"100755"}
            or fields[1] != b"blob"
        ):
            reject("source is not a regular Git file")
        entries.append(fields)
    if entries[0] != entries[1]:
        reject("base and head source differ")
    blob_sha = entries[0][2].decode("ascii")
    content = subprocess.run(
        ["git", "cat-file", "blob", blob_sha], check=True, capture_output=True
    ).stdout
    try:
        lines = [
            line.partition("#")[0].strip()
            for line in content.decode("utf-8").splitlines()
        ]
    except UnicodeDecodeError:
        reject("source is not UTF-8")
    declarations = [line for line in lines if line]
    package_name = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
    # Includes, constraints, options, extras, markers, pinned ranges and local/
    # remote references need their own provenance. Never silently exempt them.
    if not declarations or not all(
        re.fullmatch(package_name, line) for line in declarations
    ):
        reject("source is not self-contained bare unpinned requirements")

    packages: dict[str, list[dict]] = {}
    for change in changes:
        name, version = change.get("name"), change.get("version")
        if (
            change.get("ecosystem") != "pip"
            or not isinstance(name, str)
            or not re.fullmatch(package_name, name)
            or not isinstance(version, str)
            or not re.fullmatch(r"[0-9][0-9A-Za-z.!+_-]*", version)
            or change.get("scope") not in {"runtime", "development"}
            or change.get("change_type") not in {"added", "removed"}
        ):
            reject("invalid pip resolution row")
        packages.setdefault(name, []).append(change)
    for rows in packages.values():
        if (
            len(rows) != 2
            or {row["change_type"] for row in rows} != {"added", "removed"}
            or len({row["version"] for row in rows}) != 2
            or len({row["scope"] for row in rows}) != 1
        ):
            reject("not a paired version-only resolution change")

    return {
        "manifest": manifest,
        "classification": "unchanged_unlocked_requirements_resolution",
        "base_blob_sha": blob_sha,
        "head_blob_sha": blob_sha,
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "declared_packages": declarations,
        "changes": changes,
        "limitation": (
            "The manifest is not a source change; its unlocked resolver delta is "
            "retained in full. This does not prove repeatable Python resolution "
            "or waive any vulnerability/license finding or the review outcome."
        ),
    }


def _validate_changes(
    changes: list[dict], base: str, head: str, changed_files: set[str]
) -> list[dict]:
    unchanged: dict[str, list[dict]] = {}
    for change in changes:
        manifest = change.get("manifest")
        if isinstance(manifest, str) and manifest not in changed_files:
            unchanged.setdefault(manifest, []).append(change)
    resolutions = [
        _unchanged_requirements_resolution(manifest, rows, base, head)
        for manifest, rows in sorted(unchanged.items())
    ]
    npm_locks: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    observed_npm: dict[str, dict[str, set[tuple[str, str, str]]]] = {}
    uv_locks: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    observed_uv: dict[str, dict[str, set[tuple[str, str, str]]]] = {}
    for change in changes:
        manifest = change.get("manifest")
        if not isinstance(manifest, str):
            raise ValueError(
                "Dependency graph includes a change in an unchanged manifest: "
                f"{manifest!r}"
            )
        if manifest in unchanged:
            continue
        if manifest == "uv.lock":
            name, version, scope, kind = (
                change.get("name"), change.get("version"),
                change.get("scope"), change.get("change_type"),
            )
            if not all(isinstance(value, str) for value in (name, version, scope)):
                raise ValueError("uv dependency change lacks name, version, or scope")
            if kind not in {"added", "removed"}:
                raise ValueError(f"Unexpected uv dependency change type: {kind!r}")
            observed_uv.setdefault(manifest, {"added": set(), "removed": set()})[kind].add(
                (name, version, scope)
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
            observed_npm.setdefault(manifest, {"added": set(), "removed": set()})[
                "added"
            ].add(component)
            continue
        if kind == "removed" and on_base and not on_head:
            observed_npm.setdefault(manifest, {"added": set(), "removed": set()})[
                "removed"
            ].add(component)
            continue
        raise ValueError(
            "npm dependency change does not match lockfile version/scope: "
            f"{manifest} {name}@{version} {scope} {kind}"
        )
    for manifest in changed_files:
        if not manifest.endswith("package-lock.json"):
            continue
        for sha in (base, head):
            if (sha, manifest) not in npm_locks:
                npm_locks[(sha, manifest)] = _npm_lock_components(sha, manifest)
        expected = {
            "added": npm_locks[(head, manifest)] - npm_locks[(base, manifest)],
            "removed": npm_locks[(base, manifest)] - npm_locks[(head, manifest)],
        }
        if observed_npm.get(manifest, {"added": set(), "removed": set()}) != expected:
            raise ValueError(f"Incomplete npm dependency diff for {manifest}")
    for manifest in changed_files:
        if manifest != "uv.lock":
            continue
        for sha in (base, head):
            uv_locks[(sha, manifest)] = _uv_lock_components(sha, manifest)
        expected = {
            "added": uv_locks[(head, manifest)] - uv_locks[(base, manifest)],
            "removed": uv_locks[(base, manifest)] - uv_locks[(head, manifest)],
        }
        if observed_uv.get(manifest, {"added": set(), "removed": set()}) != expected:
            raise ValueError("uv dependency diff does not match lockfile versions and scopes")

    return resolutions


MAX_COMPARE_PAGES = 1000


def _next_page_url(headers) -> str | None:
    link_header = headers.get("Link")
    if link_header is None or link_header == "":
        return None
    if not isinstance(link_header, str):
        raise ValueError("Invalid dependency pagination Link header")
    next_urls = []
    for part in re.split(r",\s*(?=<)", link_header):
        match = re.fullmatch(
            r"\s*<([^<>]+)>\s*((?:;\s*[A-Za-z][\w-]*\s*=\s*"
            r'(?:"[^"]*"|[^;\s,"]+)\s*)*)',
            part,
        )
        if not match:
            raise ValueError("Malformed dependency pagination Link header")
        parameters = re.findall(
            r';\s*([A-Za-z][\w-]*)\s*=\s*(?:"([^"]*)"|([^;\s,"]+))',
            match.group(2),
        )
        relations = [
            quoted or bare for name, quoted, bare in parameters if name.lower() == "rel"
        ]
        if len(relations) > 1:
            raise ValueError("Ambiguous dependency pagination relation")
        if relations and "next" in relations[0].lower().split():
            next_urls.append(match.group(1))
    if len(next_urls) > 1:
        raise ValueError("Ambiguous dependency pagination next page")
    return next_urls[0] if next_urls else None


def _pagination_identity(
    page_url: str, comparison_url: str, allowed_paths: set[str]
) -> tuple:
    page, comparison = urlsplit(page_url), urlsplit(comparison_url)
    if (
        page.scheme != comparison.scheme
        or page.netloc.lower() != comparison.netloc.lower()
        or page.path not in allowed_paths
        or page.fragment
    ):
        raise ValueError("Dependency pagination URL leaves the trusted comparison")
    query = parse_qsl(page.query, keep_blank_values=True)
    page_numbers = [value for name, value in query if name == "page"]
    if len(page_numbers) > 1:
        raise ValueError("Ambiguous dependency pagination page parameter")
    # An omitted page is GitHub's first page, so ``?page=1`` (or ``?page=01``)
    # must not be treated as a new page after the unpaginated initial request.
    page_number = page_numbers[0] if page_numbers else "1"
    if re.fullmatch(r"[0-9]+", page_number):
        page_number = str(int(page_number))
    query = [(name, value) for name, value in query if name != "page"]
    query.append(("page", page_number))
    return (
        page.scheme,
        page.netloc.lower(),
        comparison.path,
        tuple(sorted(query)),
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
    allowed_paths = {urlsplit(url).path}
    repository_id = environment.get("GITHUB_REPOSITORY_ID")
    if repository_id is not None:
        if not re.fullmatch(r"[0-9]+", repository_id):
            raise ValueError("Invalid GitHub repository ID for dependency pagination")
        # GitHub's Link URLs can use the stable repository-ID route.
        canonical_url = (
            f"{api_root}/repositories/{repository_id}/dependency-graph/"
            f"compare/{base}...{head}"
        )
        allowed_paths.add(urlsplit(canonical_url).path)
    page_url: str | None = request.full_url
    first_page: bytes | None = None
    visited: set[tuple] = set()
    changes: list[dict] = []
    while page_url:
        identity = _pagination_identity(page_url, url, allowed_paths)
        if identity in visited or len(visited) >= MAX_COMPARE_PAGES:
            raise ValueError(
                "Dependency pagination repeats a page or exceeds its limit"
            )
        visited.add(identity)
        page_request = Request(
            page_url,
            headers=request.headers,
        )
        with opener(page_request, timeout=90) as response:
            page_raw = response.read()
            if first_page is None:
                first_page = page_raw
            snapshot_warning = response.headers.get(
                "x-github-dependency-graph-snapshot-warnings"
            )
            if snapshot_warning:
                raise ValueError(
                    "Dependency graph reported snapshot warnings; refusing to save "
                    "an incomplete comparison as review evidence"
                )
            page_changes = json.loads(page_raw)
            if not isinstance(page_changes, list) or not all(
                isinstance(item, dict) for item in page_changes
            ):
                raise ValueError(
                    "Dependency diff API did not return a complete change list"
                )
            changes.extend(page_changes)
            next_url = _next_page_url(response.headers)
            page_url = urljoin(page_url, next_url) if next_url else None
    raw_diff = first_page if len(visited) == 1 else json.dumps(changes).encode()
    resolutions = _validate_changes(
        changes,
        base,
        head,
        changed_files if changed_files is not None else _changed_files(base, head),
    )

    evidence = {
        "schema_version": 3,
        "base_sha": base,
        "head_sha": head,
        "run_id": environment["GITHUB_RUN_ID"],
        "run_attempt": environment["GITHUB_RUN_ATTEMPT"],
        "review_outcome": environment["REVIEW_OUTCOME"],
        "dependency_diff_source": url,
        "dependency_diff_count": len(changes),
        "dependency_diff_sha256": hashlib.sha256(raw_diff).hexdigest(),
        "dependency_diff_file": "dependency-diff.json",
        "unchanged_requirements_resolutions": resolutions,
    }
    # Finish every environment lookup and hash before the first write, and
    # replace each file atomically, so an evidence-assembly failure cannot leave
    # a diff without its review record (the upload step runs after failures).
    destination.mkdir(parents=True, exist_ok=True)
    _write_atomically(destination / "dependency-diff.json", raw_diff)
    _write_atomically(
        destination / "review.json", (json.dumps(evidence, indent=2) + "\n").encode()
    )
    return evidence


def _write_atomically(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    result = record_dependency_review(os.environ, Path("dependency-review-evidence"))
    print(f"Saved {result['dependency_diff_count']} dependency changes")
