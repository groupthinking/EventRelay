# Agent Completion Truth Gate

The truth gate converts repository evidence into one deterministic verdict. It never asks an LLM whether work is complete and it never approves, merges, closes, or reopens anything.

## Required enforcement rollout

`agent-completion/truth-gate` remains advisory and must not be added as a required status. The separate **Agent completion enforcement** workflow is the required, head-bound Check run. It verifies an exact-head machine-readable report published through a dedicated GitHub App and rejects missing, stale, edited, deleted, ambiguous, or self-published agent evidence. The protected policy is `.github/agent-lock/trusted-publishers.json`. While its trusted-publisher and trusted-actor allowlists are empty (the App unprovisioned), the **Agent completion enforcement** Check reports **neutral (advisory)** rather than blocking — a permanently red gate on every PR trains reviewers to ignore CI and hides real failures. The gate returns to fail-closed only once all three allowlists are populated (the App provisioned) *and* the Check is added to branch-protection required checks. Genuine policy violations — untrusted publisher, head-SHA or PR-number mismatch, and, once provisioned, a missing report — still fail closed regardless. Custom roles are fail-closed.

The trusted publisher must bind report data to PR number, full head SHA, delivery/run identity, trusted label authorization, trusted human exemption (when applicable), append-only agent events, and per-path passed/failed/error counts. The required verifier never executes PR code. Repository rules must require **Agent completion enforcement**, one independent approval, and resolved conversations. They must not require the advisory custom status.

## Enforcement lifecycle

Before delegation, create the task with the Agent task issue form. Agent login, run ID, objective, acceptance criteria, exact file scope, allowed extras, and focused test paths are the intent contract. Unrestricted scope is intentionally unavailable in the form until #874 provisions the protected `scope-unrestricted-approved` label and its authorization policy; any hand-authored unrestricted request without that label fails closed.

When a complete agent task is opened or first labeled by an actor with a standard `triage`-or-higher role (or a custom role that GitHub reports at legacy `write` level), the default-branch workflow writes a github-actions[bot] comment containing the SHA-256 digest of the normalized issue body and the unrestricted-scope approval state. The same live permission lookup applies to both event paths; issue author association alone is not trusted. GitHub's collaborator response cannot distinguish a custom triage-derived role from a custom read-derived role, so custom roles reported at legacy `read` fail closed and a standard triage-or-higher user must relabel. The collector requires that snapshot and requires it to predate the PR. Any later issue edit or label transition appends a bot-owned invalidation marker. Treating every queued edit/label event as invalidating makes GitHub concurrency coalescing lossless: an event that replaces a pending invalidation is itself an invalidation. The trusted marker comment dispatches immediate reevaluation, and the scheduled scanner also blocks permanently even if the original body or label state is restored. Existing tasks must be labeled again by a trusted user to create their one-time snapshot before dispatch. Create a new task for any post-snapshot edit; do not broaden a dispatched task in place.

Agent pull requests link exactly one task with a closing keyword and include the agent-lock-manifest comment shown in the PR template. GitHub's authoritative closingIssuesReferences, the textual link, and the manifest must agree. The manifest login and run ID must exactly match the snapshotted issue. The declared agent publishes structured result evidence containing that run ID and the current PR head SHA; legacy unstructured readiness is never sufficient by itself.

The trusted workflow runs on pull-request changes and serializes all evaluation for one PR. Pull-request and linked-issue contract changes, declared-agent result comments, and completed CI runs dispatch into that same queue; ordinary discussion comments do not. Every 15 minutes one serialized scanner compares the last owning pending lease with declared-agent result comments, exact-head CI, current applicability, the three-way issue link, frozen intent, mutable PR policy (draft/title/manifest identity and the `copilot-rabbit` label), and current review evidence. An active pending run is left alone, while a completed, missing, or hour-stale owning run is finalized directly as failure without acquiring another lease. Unchanged terminal results produce no new status. Scanner API uncertainty retries without dispatching. Issue events dispatch immediately only when the sender's current repository role is standard `triage` or higher, or GitHub reports its legacy permission at `write` or higher; known agent identities do not bypass that lookup, and unverifiable or custom-read-level events fall back to the scheduled scan. Review decisions, applicability and policy changes, and thread resolution therefore converge within 15 minutes. It checks out only the default-branch gate and never executes code from the PR head.

The workflow publishes all of the following:

- per-PR commit status `agent-completion/truth-gate/pr-<number>`;
- one updatable PR comment with marker agent-completion-truth-gate:v1;
- an Actions summary;
- gate-input.json and gate-verdict.json artifacts.

Even in the normal trust model—agents cannot write default-branch workflows or forge repository statuses—the custom status emitted here remains advisory. Follow-up #874 must bind evaluation to an independently head-bound required workflow or check before branch protection or a repository ruleset treats the result as merge enforcement. That ruleset must also require the repository's Copilot review, at least one approving review, and conversation resolution. The gate itself requires the maintainer-applied `copilot-rabbit` label, a non-dismissed Copilot review bound to the current head, every AI review thread resolved (including outdated threads), and committed focused unit tests. It binds to the exact-head trusted CI run, requires its `test` job to succeed, and requires that job's verbose pytest log to report at least one passing test for every declared path; an absent, deselected, or all-skipped path blocks. Human approval alone cannot satisfy those signals. Native review/conversation rules close the window between a new review comment and the scheduled refresh.

Each serialized run first posts a pending status tied to its Actions run. It uploads evidence and updates the PR comment before publishing a terminal status. A compare-and-swap check rejects superseded publication; an always-running finalizer turns publication failures into a failure status only when the run proves it owns the pending lease (or supersedes a predecessor). Unknown ownership fails the workflow without touching the shared status, and the scheduled scanner supplies eventual fail-closed recovery. A recovered infrastructure/publication failure remains failed until a new evidence event or a maintainer manually dispatches the workflow; the scanner does not churn unchanged evidence merely to retry it. GitHub permits at most 1,000 statuses for one SHA and context, so the workflow refuses to acquire a new lease at 998 existing per-PR gate statuses. The scanner may use a remaining slot to fail a proven stuck pending lease or invalidate a successful terminal result after evidence changes, but it never starts another full evaluation at that threshold; the operator must then push a new head or complete #874's Checks/App migration. If pending-status creation fails on a reused head, a previous successful status can remain visible until recovery; overwriting it without a proven lease could instead clobber a successor. This transient stale-green window is why this status is advisory until #874 supplies independently head-bound enforcement. Actions are pinned to full commit SHAs. Only refresh-dispatch jobs receive actions: write.

Per-path focused-test proof currently parses terminal pytest outcomes from the exact-head trusted CI `test` job log. It handles both same-line verbose outcomes and node IDs followed by live-log output and a standalone terminal outcome. Exact path prefixes, whole-line terminal matching, test-node resets, and session-boundary resets prevent unrelated output from inheriting a prior test. A same-line candidate is deferred across blank lines so a following live-log header can disambiguate a parameter ID that resembles an outcome. Code executed by pytest can still deliberately forge console lines, so the required independent review remains part of the trust boundary. Follow-up #874 must move per-path evidence to a machine-readable report emitted and published by the protected CI workflow before this signal is treated as hostile-agent-resistant.

If an agent has repository-write credentials that can create Actions workflows or post statuses/comments, github-actions[bot] and a status-context string are not independent provenance. The collector also sees only the current comment bodies; an agent that can edit or delete its own result comment can erase contradictory self-reported history. In that threat model, keep this workflow advisory until snapshot, append-only result evidence, and check publication move to a dedicated GitHub App (or an organization ruleset-required trusted workflow) and bind the required check to that identity.

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
        "present_changed_files": ["src/example.py", "tests/unit/test_example.py"],
        "merged": false,
        "draft": false,
        "title_valid": true,
        "required_checks_passed": true,
        "post_merge_checks_passed": false
      },
      "events": [
        {"kind": "artifact_ready", "sequence": 1, "author": "google-labs-jules[bot]", "run_id": "provider-run-id", "head_sha": "1111111111111111111111111111111111111111"},
        {"kind": "error", "sequence": 2, "author": "google-labs-jules[bot]", "run_id": "provider-run-id", "head_sha": "1111111111111111111111111111111111111111"}
      ],
      "reviews": [
        {"blocking": true, "resolved": false, "source": "thread-id"}
      ],
      "evidence": {
        "behavior_changed_files": ["src/example.py"],
        "focused_test_files": ["tests/unit/test_example.py"],
        "focused_test_results": {
          "tests/unit/test_example.py": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}
        },
        "copilot_current_head_reviewed": true,
        "copilot_rabbit_label": true
      },
      "collection_errors": []
    }

Run it with:

    python3 scripts/ci/agent_completion_gate.py gate-input.json

The CLI prints JSON to standard output. Exit status 1 means blocked; ready, completed, and not_applicable return 0.
An applicable policy must explicitly provide `applicable: true`, a nonblank `agent_login` and `run_id`, a 40-character hexadecimal `head_sha`, and a positive JSON integer `issue.number`. Object sections must be JSON objects; every event requires an `author` exactly equal to `policy.agent_login`, a supported `kind`, and an integer `sequence`, with any supplied run/head metadata strictly typed; and every review requires a nonblank source plus JSON booleans for `blocking` and `resolved`. `changed_files` contains every touched current and previous path, including removals, while `present_changed_files` contains only nonremoved current paths and must be a subset of `changed_files`. Every declared file is a required deliverable that must remain present at its exact path on the PR head, while allowed-extra files remain optional; for a rename, declare the destination and allowlist the source. Supplied criteria and path entries must contain non-whitespace text. Focused-test results must contain exactly one result object per declared focused-test path, with nonnegative integer counts for passed, failed, errors, skipped, xfailed, and xpassed; each path needs at least one pass and no failure or error. `copilot_current_head_reviewed` means a non-dismissed submitted Copilot review (`APPROVED`, `COMMENTED`, or `CHANGES_REQUESTED`) whose `commit_id` equals the current PR head; it is evidence of a current-head review, not native GitHub approval. Missing evidence sections, falsey containers such as `[]`, and stringified booleans are invalid payloads; they never inherit defaults. A policy containing only `applicable: false` remains a valid non-agent exemption.

## Verdict schema

Every result has the same shape:

    {
      "verdict": "blocked",
      "reasons": ["scope_drift"],
      "details": {
        "undeclared_files": ["package-lock.json"],
        "identity_projection": {
          "issue_number": 870,
          "agent_login": "example-agent[bot]",
          "run_id": "provider-run-id"
        }
      }
    }

Every evaluated applicable result carries the selected issue/agent/run identity so the scheduled fallback can detect a same-head contract switch even when both old and new contracts are otherwise valid. Hard-unknown infrastructure verdicts are not used as a comparison baseline.

Verdict meanings:

- blocked: one or more rules failed.
- ready: pre-merge evidence agrees, but the PR is not complete.
- completed: the PR is merged and required post-merge checks passed.
- not_applicable: policy explicitly exempted the PR.

## Fail-closed rules

The gate blocks a missing, late, or changed intent snapshot; agent/run/head identity mismatches; blank intent; missing acceptance criteria; missing scope; an empty PR diff; omitted, deleted, or renamed-away declared files; undeclared paths (including a rename's previous path); unapproved unrestricted scope; failed evidence collection; missing current-run output; current-run agent errors; contradictory readiness/completion and error events; a missing current-head Copilot review or `copilot-rabbit` label; unresolved AI or other blocking reviews; failed required checks; draft or invalidly titled PRs; missing, deleted, deselected, all-skipped, or failing focused Python unit-test evidence; and merged work without passing post-merge checks on the merge SHA.

Artifact ready is not completion. A Ready for review comment followed by an error is agent_run_failed. Generic green CI never overrides an unresolved review. An unmerged PR can be ready, but it can never be completed.

The deterministic evaluator blocks, and the workflow run fails, if checkout, evidence collection, evaluation, evidence upload, comment publication, or final status publication fails. Every terminal status carries the immutable pending-status ID [acquired lease]; status handoff compares those owner IDs so a newer lease overrides a late predecessor while an older lease yields to a successor. Unknown or malformed ownership fails the run without publishing from an unproven lease. Because an older success can remain visible during that recovery window, this custom status alone is not fail-closed merge enforcement. The snapshot assumes repository write access and the default branch are trusted; organizations that delegate repository-write credentials to agents should move snapshot creation behind a protected environment or an independently authenticated GitHub App.

## Technical Constraints

- **Snapshot creation is label-event-only**: Snapshot comments are generated exclusively during issue label actions to guarantee security boundaries and ensure metadata stability.
- **Recursion protection**: Status checks and gate evaluation does not recursively trigger `issue_comment` events to prevent infinite automated loop cycles.
- **Trace parameters**: Resolve-time, collection-time, and publication-time PR base and head SHAs are captured explicitly to prevent race conditions during concurrent runs.
- **Commit comparisons**: Every verdict includes an immutable resolved base/head commit comparison to guarantee that evaluations apply exactly to the proposed diff.
