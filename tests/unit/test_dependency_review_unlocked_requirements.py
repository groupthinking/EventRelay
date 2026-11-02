"""Keep complete source-verified evidence when an unlocked pip scan resolves again."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess

import pytest

from scripts.ci.record_dependency_review import record_dependency_review

MANIFEST = "docs/knowledge_prototypes/universal-automation-service/requirements.txt"
BARE_REQUIREMENTS = "python-dotenv\nrequests\ngoogle-generativeai\nyoutube-transcript-api\ntorch\ntransformers\nnumpy\npsutil\n"
# These two rows reproduce the actual 2026-11-02 PR2398 comparison, whose
# source manifest did not change between ffd07a and d6fef801.
PIP_ROWS = [
    {
        "change_type": "added",
        "manifest": MANIFEST,
        "ecosystem": "pip",
        "name": "filelock",
        "version": "4.2.7",
        "package_url": "pkg:pypi/filelock@4.2.7",
        "license": "MIT",
        "source_repository_url": None,
        "scope": "runtime",
        "vulnerabilities": [],
    },
    {
        "change_type": "removed",
        "manifest": MANIFEST,
        "ecosystem": "pip",
        "name": "filelock",
        "version": "4.2.6",
        "package_url": "pkg:pypi/filelock",
        "license": "MIT",
        "source_repository_url": None,
        "scope": "runtime",
        "vulnerabilities": [],
    },
]


@pytest.fixture
def comparison(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    def git(*args):
        return subprocess.run(
            [
                "git",
                "-c",
                "user.name=Evidence test",
                "-c",
                "user.email=evidence@example.invalid",
                *args,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-q")
    manifest = repo / MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(BARE_REQUIREMENTS)

    def commit(version, dev):
        (repo / "package-lock.json").write_text(
            json.dumps(
                {
                    "lockfileVersion": 3,
                    "packages": {
                        "node_modules/leaf": {"version": version},
                        "node_modules/vite": {"version": "8.3.0", **dev},
                    },
                }
            )
        )
        git("add", ".")
        git("commit", "-qm", version)
        return git("rev-parse", "HEAD")

    base = commit("1.0.0", {"dev": True})
    head = commit("2.0.0", {"devOptional": True})
    npm_rows = [
        {
            "manifest": "package-lock.json",
            "ecosystem": "npm",
            "name": name,
            "version": version,
            "scope": scope,
            "change_type": kind,
        }
        for name, version, scope, kind in [
            ("leaf", "1.0.0", "runtime", "removed"),
            ("leaf", "2.0.0", "runtime", "added"),
            ("vite", "8.3.0", "development", "removed"),
            ("vite", "8.3.0", "runtime", "added"),
        ]
    ]
    env = {
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "GITHUB_REPOSITORY": "groupthinking/EventRelay",
        "GITHUB_TOKEN": "offline-test-token",
        "GITHUB_RUN_ID": "41525920691",
        "GITHUB_RUN_ATTEMPT": "1",
        "REVIEW_OUTCOME": "failure",
    }
    return repo, manifest, git, env, npm_rows


def record(comparison, destination, rows, **kwargs):
    raw = json.dumps(rows).encode()

    class Response(io.BytesIO):
        headers = {}

    result = record_dependency_review(
        comparison[3],
        destination,
        opener=lambda request, timeout: Response(raw),
        **kwargs,
    )
    return result, raw


@pytest.mark.parametrize("outcome", ["success", "failure"])
def test_unchanged_unlocked_pip_resolution_keeps_all_rows_and_review_verdict(
    comparison, tmp_path, outcome
):
    comparison[3]["REVIEW_OUTCOME"] = outcome
    rows = comparison[4] + PIP_ROWS
    # A finding in these rows must remain visible and subject to the action's
    # existing policy; recording source provenance is never a security waiver.
    rows[3] = {
        **rows[3],
        "vulnerabilities": [
            {"advisory_ghsa_id": "GHSA-test-case-only", "severity": "high"}
        ],
    }
    rows[-2] = {
        **rows[-2],
        "vulnerabilities": [
            {"advisory_ghsa_id": "GHSA-resolution-test-only", "severity": "moderate"}
        ],
    }
    destination = tmp_path / "evidence"
    result, raw = record(comparison, destination, rows)
    assert (destination / "dependency-diff.json").read_bytes() == raw
    assert json.loads((destination / "review.json").read_text()) == result
    assert result["review_outcome"] == outcome
    assert result["dependency_diff_count"] == len(rows)
    assert result["dependency_diff_sha256"] == hashlib.sha256(raw).hexdigest()
    (proof,) = result["unchanged_requirements_resolutions"]
    assert proof["manifest"] == MANIFEST
    assert (
        proof["base_blob_sha"]
        == proof["head_blob_sha"]
        == comparison[2]("rev-parse", comparison[3]["HEAD_SHA"] + ":" + MANIFEST)
    )
    assert (
        proof["content_sha256"]
        == hashlib.sha256(BARE_REQUIREMENTS.encode()).hexdigest()
    )
    assert proof["classification"] == "unchanged_unlocked_requirements_resolution"
    assert proof["changes"] == rows[-2:]
    assert "not a source change" in proof["limitation"]


@pytest.mark.parametrize(
    "content",
    [
        "-r other.txt\n",
        "--requirement other.txt\n",
        "-c constraints.txt\n",
        "torch==9.0\n",
        "torch>=9\n",
        "torch[extra]\n",
        "-e .\n",
        "./local-package\n",
        "https://example.invalid/package.whl\n",
        "--index-url https://example.invalid\n",
        "torch; python_version > '3.10'\n",
        "# empty\n",
    ],
)
def test_unverifiable_requirement_forms_fail_closed(comparison, tmp_path, content):
    repo, manifest, git, env, npm_rows = comparison
    git("checkout", "--detach", env["BASE_SHA"])
    manifest.write_text(content)
    git("add", ".")
    git("commit", "-qm", "unsupported source")
    env["BASE_SHA"] = git("rev-parse", "HEAD")
    git("checkout", "--detach", env["HEAD_SHA"])
    manifest.write_text(content)
    git("add", ".")
    git("commit", "-qm", "unsupported source")
    env["HEAD_SHA"] = git("rev-parse", "HEAD")
    with pytest.raises(ValueError, match="unchanged manifest"):
        record(
            comparison,
            tmp_path / "evidence",
            npm_rows + PIP_ROWS,
            changed_files={"package-lock.json"},
        )
    assert not (tmp_path / "evidence").exists()


@pytest.mark.parametrize("change", ["changed", "missing", "symlink"])
def test_unchanged_claim_requires_existing_identical_regular_git_blobs(
    comparison, tmp_path, change
):
    repo, manifest, git, env, npm_rows = comparison
    if change == "changed":
        manifest.write_text("torch\nnew-package\n")
    elif change == "missing":
        manifest.unlink()
    else:
        manifest.unlink()
        manifest.symlink_to("torch")
    git("add", ".")
    git("commit", "-qm", change)
    env["HEAD_SHA"] = git("rev-parse", "HEAD")
    with pytest.raises(ValueError, match="unchanged manifest"):
        record(
            comparison,
            tmp_path / "evidence",
            npm_rows + PIP_ROWS,
            changed_files={"package-lock.json"},
        )
    assert not (tmp_path / "evidence").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-npm-row",
        "wrong-npm-scope",
        "extra-npm-version",
        "unpaired-pip",
        "duplicate-pip",
        "pip-scope-change",
        "wrong-ecosystem",
        "invalid-version",
        "traversal-path",
    ],
)
def test_resolution_drift_cannot_hide_real_graph_mismatch(
    comparison, tmp_path, mutation
):
    rows = [dict(row) for row in comparison[4] + PIP_ROWS]
    if mutation == "missing-npm-row":
        rows.pop(0)
    elif mutation == "wrong-npm-scope":
        rows[3]["scope"] = "development"
    elif mutation == "extra-npm-version":
        rows.append({**rows[1], "version": "99.0.0"})
    elif mutation == "unpaired-pip":
        rows.pop()
    elif mutation == "duplicate-pip":
        rows.append(rows[-1])
    elif mutation == "pip-scope-change":
        rows[-1]["scope"] = "development"
    elif mutation == "wrong-ecosystem":
        rows[-1]["ecosystem"] = "npm"
    elif mutation == "invalid-version":
        rows[-1]["version"] = " 4.2.6 "
    elif mutation == "traversal-path":
        for row in rows[-2:]:
            row["manifest"] = "../requirements.txt"
    with pytest.raises(ValueError):
        record(comparison, tmp_path / "evidence", rows)
    assert not (tmp_path / "evidence").exists()
