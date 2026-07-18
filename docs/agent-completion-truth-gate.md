# Agent Completion Truth Gate

The truth gate converts repository evidence into one deterministic verdict. It never asks an LLM whether work is complete and it never approves, merges, closes, or reopens anything.

## Enforcement lifecycle

Before delegation, create the task with the Agent task issue form. Agent login, run ID, objective, acceptance criteria, exact file scope, allowed extras, and focused test paths are the intent contract. Unrestricted scope also requires the maintainer-controlled scope-unrestricted-approved label.

When a complete agent task is opened or first labeled, the default-branch workflow writes a github-actions[bot] comment containing the SHA-256 digest of the normalized issue body and the unrestricted-scope approval state. The collector requires that snapshot, requires it to predate the PR, and blocks if the issue body or approval state later changes. Existing tasks must be labeled again by a maintainer to create their one-time snapshot before dispatch. Create a new task for materially changed intent; do not broaden a dispatched task in place.

Agent pull requests link exactly one task with a closing keyword and include the agent-lock-manifest comment shown in the PR template. GitHub's authoritative closingIssuesReferences, the textual link, and the manifest must agree. The manifest login and run ID must exactly match the snapshotted issue. The declared agent publishes structured result evidence containing that run ID and the current PR head SHA; legacy unstructured readiness is never sufficient by itself.

The trusted workflow runs on pull-request changes and serializes all evaluation for one PR. Linked-issue/result-comment changes and completed CI runs dispatch into that same queue; a 15-minute sweep refreshes all open PRs. Review decisions and thread resolution therefore converge within 15 minutes. It checks out only the default-branch gate and never executes code from the PR head.

The workflow publishes all of the following:

- commit status agent-completion/truth-gate;
- one updatable PR comment with marker agent-completion-truth-gate:v1;
- an Actions summary;
- gate-input.json and gate-verdict.json artifacts.

For the normal trust model—agents cannot write default-branch workflows or forge repository statuses—configure branch protection or the repository ruleset to require agent-completion/truth-gate, at least one approving review, and conversation resolution. Until those rules are configured, the workflow reports failures but cannot itself prevent a merge. Native review/conversation rules close the window between a new review comment and the scheduled refresh.

Each serialized run first posts a pending status tied to its Actions run. It uploads evidence and updates the PR comment before publishing a terminal status. A compare-and-swap check rejects superseded publication; an always-running finalizer turns publication failures into a failure status. Actions are pinned to full commit SHAs. Only refresh-dispatch jobs receive actions: write.

If an agent has repository-write credentials that can create Actions workflows or post statuses/comments, github-actions[bot] and a status-context string are not independent provenance. In that threat model, keep this workflow advisory until snapshot and check publication move to a dedicated GitHub App (or an organization ruleset-required trusted workflow) and bind the required check to that identity.

## Applicability

The gate applies when any of these signals identify agent work:

- a known agent bot authored the PR;
- the branch starts with agent/, claude/, codex/, copilot/, or jules/;
- the PR or linked issue has agent, agent-task, or mcp/agent;
- the PR contains an agent-lock-manifest comment.

Dependabot is exempt. Other human-authored PRs receive not_applicable.

## Input schema

The CLI accepts one JSON object:

    {
      "policy": {
        "applicable": true,
        "agent_login": "google-labs-jules[bot]",
        "run_id": "provider-run-id",
        "head_sha": "1111111111111111111111111111111111111111"
      },
      "issue": {
        "number": 802,
        "description": "Required objective",
        "acceptance_criteria": ["Observable criterion"],
        "declared_files": ["src/example.py", "tests/unit/test_example.py"],
        "allowed_extra_files": ["docs/example.md"],
        "scope_unrestricted": false
      },
      "pull_request": {
        "number": 813,
        "changed_files": ["src/example.py", "tests/unit/test_example.py"],
        "merged": false,
        "draft": false,
        "title_valid": true,
        "required_checks_passed": true,
        "post_merge_checks_passed": false
      },
      "events": [
        {"kind": "artifact_ready", "sequence": 1, "run_id": "provider-run-id", "head_sha": "1111111111111111111111111111111111111111"},
        {"kind": "error", "sequence": 2, "run_id": "provider-run-id", "head_sha": "1111111111111111111111111111111111111111"}
      ],
      "reviews": [
        {"blocking": true, "resolved": false, "source": "thread-id"}
      ],
      "evidence": {
        "behavior_changed_files": ["src/example.py"],
        "focused_test_files": ["tests/unit/test_example.py"],
        "focused_tests_passed": true
      },
      "collection_errors": []
    }

Run it with:

    python3 scripts/ci/agent_completion_gate.py gate-input.json

The CLI prints JSON to standard output. Exit status 1 means blocked; ready, completed, and not_applicable return 0.

## Verdict schema

Every result has the same shape:

    {
      "verdict": "blocked",
      "reasons": ["scope_drift"],
      "details": {
        "undeclared_files": ["package-lock.json"]
      }
    }

Verdict meanings:

- blocked: one or more rules failed.
- ready: pre-merge evidence agrees, but the PR is not complete.
- completed: the PR is merged and required post-merge checks passed.
- not_applicable: policy explicitly exempted the PR.

## Fail-closed rules

The gate blocks a missing, late, or changed intent snapshot; agent/run/head identity mismatches; blank intent; missing acceptance criteria; missing scope; undeclared paths (including a rename's previous path); unapproved unrestricted scope; failed evidence collection; missing current-run output; current-run agent errors; contradictory readiness/completion and error events; unresolved blocking reviews; failed required checks; draft or invalidly titled PRs; missing, deleted, or failing focused Python unit-test evidence; and merged work without passing post-merge checks on the merge SHA.

Artifact ready is not completion. A Ready for review comment followed by an error is agent_run_failed. Generic green CI never overrides an unresolved review. An unmerged PR can be ready, but it can never be completed.

The workflow also fails closed if checkout, evidence collection, evaluation, evidence upload, comment publication, or final status publication fails. The snapshot assumes repository write access and the default branch are trusted; organizations that delegate repository-write credentials to agents should move snapshot creation behind a protected environment or an independently authenticated GitHub App.
