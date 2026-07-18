# Workflow catalog

`pr-checks.yml` remains the advisory evidence collector and publishes `agent-completion/truth-gate/pr-<number>` only. It is never a required status.

`agent-completion-enforcement.yml` is the separately named required workflow/check: **Agent completion enforcement**. It runs from the protected default branch on `pull_request_target`, reads the PR head SHA through the API, and accepts only the exact-head machine-readable report emitted by the configured trusted GitHub App. It never checks out or executes PR code. Missing, stale, ambiguous, mutable, or untrusted evidence fails closed.

The enforcement workflow has `checks: write`, `contents: read`, and `pull-requests: read`; it has no `statuses: write`. Its concurrency is GitHub's ordinary per-run scheduling because it never shares an advisory status lease. The trusted publisher is responsible for append-only event capture and for a report bound to pull number, head SHA, workflow/run identity, and per-path results.

Before enabling the required rule, provision `.github/agent-lock/trusted-publishers.json` through protected default-branch review with the dedicated App slug and trusted actor allowlists. Empty lists deliberately block. Configure the repository ruleset to require **Agent completion enforcement**, one independent approval, and resolved conversations; do not require `agent-completion/truth-gate`.
