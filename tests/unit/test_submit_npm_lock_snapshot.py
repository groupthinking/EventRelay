from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from scripts.ci.submit_npm_lock_snapshot import (
    CORRELATOR,
    npm_manifest,
    submit_snapshot,
    tracked_npm_locks,
)


def test_nested_npm_versions_survive_as_distinct_scoped_dependencies() -> None:
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": {
                "dependencies": {"app": "1.0.0"},
                "devDependencies": {"filelist": "1.0.0"},
            },
            "node_modules/app": {
                "version": "1.0.0",
                "dependencies": {"brace-expansion": "1.1.21"},
            },
            "node_modules/brace-expansion": {"version": "1.1.21"},
            "node_modules/filelist": {
                "version": "1.0.0",
                "dev": True,
                "dependencies": {"brace-expansion": "2.1.7"},
            },
            "node_modules/filelist/node_modules/brace-expansion": {
                "version": "2.1.7",
                "dev": True,
                "license": "MIT",
            },
        },
    }
    manifest = npm_manifest(lock, "docs/fetch/package-lock.json")
    rows = list(manifest["resolved"].values())
    braces = [row for row in rows if "brace-expansion" in row["package_url"]]
    assert len(braces) == 2
    assert {row["package_url"] for row in braces} == {
        "pkg:npm/brace-expansion@1.1.21",
        "pkg:npm/brace-expansion@2.1.7",
    }
    assert {row["scope"] for row in braces} == {"runtime", "development"}
    filelist = next(
        row for row in rows if row["package_url"] == "pkg:npm/filelist@1.0.0"
    )
    nested_key = next(
        key
        for key, row in manifest["resolved"].items()
        if row["package_url"] == "pkg:npm/brace-expansion@2.1.7"
    )
    assert nested_key in filelist["dependencies"]
    assert manifest["file"]["source_location"] == "docs/fetch/package-lock.json"


def test_real_npm_locks_include_all_resolved_versions() -> None:
    locks = tracked_npm_locks()
    assert {path.as_posix() for path in locks} == {
        "package-lock.json",
        "sdk/typescript/package-lock.json",
        "docs/knowledge_prototypes/mcp-servers/fetch-mcp/package-lock.json",
    }
    for path in locks:
        lock = json.loads(Path(path).read_text())
        manifest = npm_manifest(lock, path.as_posix())
        expected = len(
            {
                (
                    package.get("name") or location.rsplit("node_modules/", 1)[1],
                    package.get("version"),
                )
                for location, package in lock["packages"].items()
                if "node_modules/" in location
                and package.get("version")
                and not package.get("link")
            }
        )
        assert len(manifest["resolved"]) == expected


def test_duplicate_version_uses_runtime_scope_regardless_of_path_order() -> None:
    paths = [
        ("node_modules/dev/node_modules/lru-cache", {"version": "11.5.3", "dev": True}),
        ("node_modules/runtime/node_modules/lru-cache", {"version": "11.5.3"}),
    ]
    for ordered in (paths, list(reversed(paths))):
        lock = {"lockfileVersion": 3, "packages": dict(ordered)}
        rows = npm_manifest(lock, "package-lock.json")["resolved"]
        assert list(rows) == ["lru-cache@11.5.3"]
        assert rows["lru-cache@11.5.3"]["scope"] == "runtime"


def test_npm_manifest_rejects_unknown_lock_format() -> None:
    with pytest.raises(ValueError, match="Unsupported npm lockfile"):
        npm_manifest({"lockfileVersion": 1, "packages": {}}, "package-lock.json")


def test_snapshot_submits_all_tracked_locks_at_exact_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    lock = {
        "lockfileVersion": 3,
        "packages": {"node_modules/brace-expansion": {"version": "2.1.7", "dev": True}},
    }
    for path in (Path("package-lock.json"), Path("sdk/typescript/package-lock.json")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(lock))
    subprocess.run(["git", "add", "."], check=True)
    seen = []

    def opener(request, timeout):
        seen.append((request, timeout))
        return io.BytesIO(b'{"id": 12345}')

    result = submit_snapshot(
        {
            "SNAPSHOT_SHA": "a" * 40,
            "SNAPSHOT_REF": "refs/heads/codex/test",
            "GITHUB_REPOSITORY": "groupthinking/EventRelay",
            "GITHUB_RUN_ID": "987",
            "GITHUB_TOKEN": "test-token",
        },
        opener=opener,
    )
    assert result == {"snapshot_id": 12345, "manifest_count": 2, "package_count": 2}
    request, timeout = seen[0]
    snapshot = json.loads(request.data)
    assert timeout == 90
    assert snapshot["sha"] == "a" * 40
    assert snapshot["ref"] == "refs/heads/codex/test"
    assert snapshot["job"]["correlator"] == CORRELATOR
    assert set(snapshot["manifests"]) == {
        "package-lock.json",
        "sdk/typescript/package-lock.json",
    }
    assert request.get_header("Authorization") == "Bearer test-token"


def test_snapshot_combines_npm_and_scoped_uv_in_one_submission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    Path("package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {"node_modules/brace-expansion": {"version": "2.1.7"}},
            }
        )
    )
    Path("uv.lock").write_text(
        'version = 1\n[[package]]\nname = "example"\nversion = "1.0"\n'
        'source = { editable = "." }\n[package.optional-dependencies]\n'
        'dev = [{ name = "black" }]\n[[package]]\nname = "black"\n'
        'version = "24.0"\nsource = { registry = "https://pypi.org/simple" }\n'
    )
    subprocess.run(["git", "add", "."], check=True)
    seen = []

    def opener(request, timeout):
        seen.append((request, timeout))
        return io.BytesIO(b'{"id": 12345}')

    result = submit_snapshot(
        {
            "SNAPSHOT_SHA": "a" * 40,
            "SNAPSHOT_REF": "refs/heads/codex/test",
            "GITHUB_REPOSITORY": "groupthinking/EventRelay",
            "GITHUB_RUN_ID": "987",
            "GITHUB_TOKEN": "test-token",
        },
        opener=opener,
    )
    assert len(seen) == 1
    assert result == {"snapshot_id": 12345, "manifest_count": 2, "package_count": 2}
    snapshot = json.loads(seen[0][0].data)
    assert set(snapshot["manifests"]) == {"package-lock.json", "uv.lock"}
    assert (
        snapshot["manifests"]["uv.lock"]["resolved"]["black@24.0"]["scope"]
        == "development"
    )
