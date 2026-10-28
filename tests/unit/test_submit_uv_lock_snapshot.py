from __future__ import annotations

import io
import json
import runpy
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / "scripts/ci/submit_uv_lock_snapshot.py"))


def _lock(version: str) -> dict:
    return {
        "version": 1,
        "package": [
            {
                "name": "example", "version": "1.0", "source": {"editable": "."},
                "dependencies": [{"name": "shared"}],
                "optional-dependencies": {
                    "dev": [{"name": "black"}],
                    "docs": [{"name": "notebook"}],
                    "cloud": [{"name": "cloud-api"}],
                },
            },
            {"name": "shared", "version": "1.0", "source": {"registry": "https://pypi.org/simple"}},
            {
                "name": "black", "version": version,
                "source": {"registry": "https://pypi.org/simple"},
                "dependencies": [{"name": "shared"}, {"name": "dev-helper"}],
            },
            {"name": "notebook", "version": "2.0", "source": {"registry": "https://pypi.org/simple"}},
            {"name": "cloud-api", "version": "3.0", "source": {"registry": "https://pypi.org/simple"}},
            {"name": "dev-helper", "version": "4.0", "source": {"registry": "https://pypi.org/simple"}},
        ],
    }


def test_uv_manifest_classifies_editable_root_and_transitive_packages() -> None:
    resolved = MODULE["uv_manifest"](_lock("24.0"))["resolved"]
    assert len(resolved) == 5
    assert resolved["black@24.0"]["scope"] == "development"
    assert resolved["black@24.0"]["relationship"] == "direct"
    assert resolved["black@24.0"]["dependencies"] == ["dev-helper@4.0", "shared@1.0"]
    assert resolved["notebook@2.0"]["scope"] == "development"
    assert resolved["dev-helper@4.0"]["scope"] == "development"
    assert resolved["shared@1.0"]["scope"] == "runtime"
    assert resolved["cloud-api@3.0"]["scope"] == "runtime"


def test_current_uv_lock_keeps_dev_only_changes_out_of_runtime() -> None:
    with (ROOT / "uv.lock").open("rb") as stream:
        resolved = MODULE["uv_manifest"](tomllib.load(stream))["resolved"]
    for name in ("black", "notebook", "pyjwt", "brotli", "virtualenv"):
        assert next(value for key, value in resolved.items() if key.startswith(f"{name}@"))[
            "scope"
        ] == "development"
    assert next(value for key, value in resolved.items() if key.startswith("aiohttp@"))[
        "scope"
    ] == "runtime"


def test_snapshot_submission_uses_exact_commit_and_scoped_manifest(tmp_path: Path) -> None:
    # A compact TOML fixture keeps this test independent of any GitHub service.
    lock_path = tmp_path / "uv.lock"
    lock_path.write_text(
        'version = 1\n[[package]]\nname = "example"\nversion = "1.0"\n'
        'source = { editable = "." }\n[package.optional-dependencies]\n'
        'dev = [{ name = "black" }]\n[[package]]\nname = "black"\n'
        'version = "24.0"\nsource = { registry = "https://pypi.org/simple" }\n'
    )
    captured = {}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response(b'{"id": 1234}')

    sha = "a" * 40
    result = MODULE["submit_snapshot"](
        lock_path,
        {
            "SNAPSHOT_SHA": sha,
            "SNAPSHOT_REF": "refs/heads/codex/example",
            "GITHUB_REPOSITORY": "groupthinking/EventRelay",
            "GITHUB_RUN_ID": "123",
            "GITHUB_TOKEN": "dummy-test-token",
        },
        opener=opener,
    )
    assert result == {"snapshot_id": 1234, "package_count": 1}
    assert captured["body"]["sha"] == sha
    assert captured["body"]["ref"] == "refs/heads/codex/example"
    assert captured["body"]["manifests"][lock_path.as_posix()]["resolved"]["black@24.0"][
        "scope"
    ] == "development"
    assert captured["url"].endswith("/dependency-graph/snapshots")


def test_recorder_rejects_runtime_label_for_dev_only_uv_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "Test"],
        ["git", "config", "user.email", "test@example.com"],
    ):
        subprocess.run(command, cwd=repo, check=True)
    lock_path = repo / "uv.lock"

    def commit(version: str) -> str:
        lock_path.write_text(
            'version = 1\n[[package]]\nname = "example"\nversion = "1.0"\n'
            'source = { editable = "." }\n[package.optional-dependencies]\n'
            'dev = [{ name = "black" }]\n[[package]]\nname = "black"\n'
            f'version = "{version}"\n'
            'source = { registry = "https://pypi.org/simple" }\n'
        )
        subprocess.run(["git", "add", "uv.lock"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", version], cwd=repo, check=True)
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()

    base, head = commit("24.0"), commit("25.0")
    recorder = runpy.run_path(str(ROOT / "scripts/ci/record_dependency_review.py"))
    monkeypatch.chdir(repo)
    changes = [
        {"manifest": "uv.lock", "ecosystem": "pip", "name": "black", "version": version,
         "scope": scope, "change_type": kind}
        for kind, version, scope in (
            ("removed", "24.0", "runtime"), ("added", "25.0", "runtime")
        )
    ]
    with pytest.raises(ValueError, match="uv dependency diff"):
        recorder["_validate_changes"](changes, base, head, {"uv.lock"})
    for change in changes:
        change["scope"] = "development"
    recorder["_validate_changes"](changes, base, head, {"uv.lock"})
