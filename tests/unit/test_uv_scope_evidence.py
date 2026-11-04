from __future__ import annotations

import hashlib
import io
import json
import runpy
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

BASE_LOCK = '''version = 1
[[package]]
name = "example"
version = "1.0"
source = { editable = "." }
dependencies = [{ name = "split", version = "1.0", source = { registry = "https://pypi.org/simple" } }]
[[package]]
name = "split"
version = "1.0"
source = { registry = "https://pypi.org/simple" }
'''

SPLIT_LOCK = BASE_LOCK.replace(
    '[[package]]\nname = "split"',
    '[package.optional-dependencies]\n'
    'dev = [{ name = "split", version = "2.0", source = { registry = "https://pypi.org/simple" } }]\n'
    '[[package]]\nname = "split"',
) + '''[[package]]
name = "split"
version = "2.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [{ name = "dev-child" }]
[[package]]
name = "dev-child"
version = "1.0"
source = { registry = "https://pypi.org/simple" }
'''


def _source_lock(child_version: str) -> str:
    # Both split records have identical names/versions. Only the second source
    # owns the child; the runtime source must not make that child runtime.
    return SPLIT_LOCK.replace(
        'version = "2.0", source = { registry = "https://pypi.org/simple" }',
        'version = "1.0", source = { registry = "https://dev.example/simple" }',
    ).replace(
        'version = "2.0"\nsource = { registry = "https://pypi.org/simple" }',
        'version = "1.0"\nsource = { registry = "https://dev.example/simple" }',
    ).replace(
        'name = "dev-child"\nversion = "1.0"',
        f'name = "dev-child"\nversion = "{child_version}"',
    )


@pytest.fixture(params=["split-versions", "split-sources", "source-precedence"])
def scope_review(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict, list[dict], dict]:
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
            cwd=repo, check=True, capture_output=True, text=True,
        ).stdout.strip()

    git("init", "-q")

    def commit(lock: str, message: str) -> str:
        (repo / "uv.lock").write_text(lock)
        git("add", "uv.lock")
        git("commit", "-qm", message)
        return git("rev-parse", "HEAD")

    # These expected API rows are hand-authored independently of uv_manifest.
    # Building them with the classifier would reproduce its error as an oracle.
    if request.param == "split-versions":
        base, head = commit(BASE_LOCK, "base"), commit(SPLIT_LOCK, "head")
        expected = [
            {"name": "split", "version": "2.0", "change_type": "added"},
            {"name": "dev-child", "version": "1.0", "change_type": "added"},
        ]
    elif request.param == "split-sources":
        base = commit(_source_lock("1.0"), "base")
        head = commit(_source_lock("2.0"), "head")
        expected = [
            {"name": "dev-child", "version": "1.0", "change_type": "removed"},
            {"name": "dev-child", "version": "2.0", "change_type": "added"},
        ]
    else:
        base = commit('''version = 1
[[package]]
name = "example"
version = "1.0"
source = { editable = "." }
[package.optional-dependencies]
dev = [{ name = "split", version = "1.0", source = { registry = "https://dev.example/simple" } }]
[[package]]
name = "split"
version = "1.0"
source = { registry = "https://dev.example/simple" }
dependencies = [{ name = "dev-child" }]
[[package]]
name = "dev-child"
version = "1.0"
source = { registry = "https://pypi.org/simple" }
''', "base")
        head = commit(_source_lock("1.0"), "head")
        expected = [
            {"name": "split", "version": "1.0", "change_type": "removed"},
            {"name": "split", "version": "1.0", "change_type": "added", "scope": "runtime"},
        ]
    rows = [
        {"manifest": "uv.lock", "ecosystem": "pip", "scope": "development", **row}
        for row in expected
    ]
    recorder = runpy.run_path(str(ROOT / "scripts/ci/record_dependency_review.py"))
    monkeypatch.chdir(repo)
    if request.param == "source-precedence":
        assert recorder["_uv_lock_components"](head, "uv.lock") == {
            ("split", "1.0", "runtime"),
            ("dev-child", "1.0", "development"),
        }
    environment = {
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "GITHUB_REPOSITORY": "groupthinking/EventRelay",
        "GITHUB_TOKEN": "dummy-test-token",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "REVIEW_OUTCOME": "success",
    }
    return recorder, rows, environment


class ApiResponse(io.BytesIO):
    headers: dict[str, str] = {}


@pytest.mark.parametrize("corrupt_rows", [(0,), (1,), (0, 1)])
def test_recorder_rejects_split_identity_scope_errors_before_writing(
    scope_review: tuple[dict, list[dict], dict],
    tmp_path: Path,
    corrupt_rows: tuple[int, ...],
) -> None:
    recorder, rows, environment = scope_review
    corrupted = [
        {**row, "scope": "runtime" if row["scope"] == "development" else "development"}
        if index in corrupt_rows else row
        for index, row in enumerate(rows)
    ]
    raw = json.dumps(corrupted).encode()
    destination = tmp_path / "invalid-evidence"
    with pytest.raises(ValueError, match="uv dependency diff"):
        recorder["record_dependency_review"](
            environment, destination,
            opener=lambda request, timeout: ApiResponse(raw),
        )
    assert not destination.exists()


def test_recorder_persists_literal_correct_split_identity_scopes(
    scope_review: tuple[dict, list[dict], dict], tmp_path: Path
) -> None:
    recorder, rows, environment = scope_review
    raw = json.dumps(rows).encode()
    destination = tmp_path / "valid-evidence"
    recorder["record_dependency_review"](
        environment, destination,
        opener=lambda request, timeout: ApiResponse(raw),
    )
    assert json.loads((destination / "dependency-diff.json").read_text()) == rows
    saved = json.loads((destination / "review.json").read_text())
    assert saved["base_sha"] == environment["BASE_SHA"]
    assert saved["head_sha"] == environment["HEAD_SHA"]
    assert saved["dependency_diff_count"] == 2
    assert saved["dependency_diff_sha256"] == hashlib.sha256(raw).hexdigest()
