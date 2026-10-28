"""Save the complete GitHub dependency diff without Actions output expansion."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen


def record_dependency_review(
    environment: dict[str, str],
    destination: Path,
    opener=urlopen,
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
            "Dependency graph reported missing snapshots; refusing to save "
            "an incomplete comparison as review evidence"
        )
    changes = json.loads(raw_diff)
    if not isinstance(changes, list) or not all(isinstance(item, dict) for item in changes):
        raise ValueError("Dependency diff API did not return a complete change list")

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
