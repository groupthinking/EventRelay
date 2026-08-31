---
on:
  workflow_dispatch:

permissions:
  actions: read
  checks: read
  contents: read
  issues: read
  pull-requests: read

engine: codex
model: gpt-5.4
network: defaults

tools:
  github:
    toolsets: [context, repos, issues, pull_requests, actions]

pre-agent-steps:
  - name: Require dedicated Codex credential
    env:
      CODEX_API_KEY: ${{ secrets.CODEX_API_KEY }}
    run: |
      if [ -z "${CODEX_API_KEY}" ]; then
        echo "::error::Dedicated CODEX_API_KEY is required"
        exit 1
      fi

safe-outputs:
  add-comment:
    max: 1
  report-incomplete: false
  threat-detection: true

---

# Focused Coverage Controller (read-only canary)

You are EventRelay's focused coverage controller. Use the configured Codex
engine for this canary; Jules remains enabled as an implementation agent and
must not be disabled or impersonated by this workflow.

This workflow is manual-only until the authoritative Coverage job produces an
exact-head artifact and the canary exit criteria in issue #920 are complete.

## Live Python lane

No Python live-smoke workflow is installed. This controller reads deterministic
CI and Coverage evidence only; it must not set `RUN_LIVE_E2E` or
`RUN_LIVE_DEPLOY`, and it must not claim that live Python smoke tests ran.
Ordinary pytest collection excludes the audited live/side-effect modules before
import. A future live lane needs its own focused issue, manual-only workflow,
declared service and credential prerequisites, and a separate explicit approval
before enabling deployment-capable smoke modules.

## Entry criteria

- Proceed only when a focused coverage child issue is active.
- Work from authoritative coverage artifacts tied to the exact tested SHA.
- Use a single canonical PR (no new PR creation).

## Canary constraints

- Read and classify exact-head evidence; do not commit, push, or mutate branches.
- Identify the smallest focused test increment for the existing canonical PR.
- Start at measured baseline + no-regression.
- Ratchet toward the declared target only after authoritative checks pass.
- Report whether Coverage + CI + Security are green on the same exact head.
- Enabling same-branch writes requires a separate approved GitHub App canary.

## Data sources to consume

- coverage JSON / lcov from exact tested SHA
- failing test logs from authoritative workflow run
- current canonical PR head checks

## Controller reporting requirement

Return an in-depth status report with:

- controller login and run ID
- canonical branch/PR, exact tested head, and latest heartbeat
- baseline coverage vs current head
- exact failing or passing gate names
- smallest next test-only increment
- explicit stop reason if prerequisites are missing
