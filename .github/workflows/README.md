# GitHub Actions Workflows

This directory contains the CI/CD, security, automation, and operational
workflows for EventRelay. Each file is a self-contained GitHub Actions
workflow; this README is the index.

## Workflow Catalog

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI | `ci.yml` | push / PR to `main` | Type-check + lint `apps/web`, build the web app, lint Python (informational), run unit tests |
| Coverage | `coverage.yml` | push / PR to `main`,`develop`; manual | Generate pytest coverage and upload lcov to Qlty |
<<<<<<< HEAD
=======
| gh-aw Validation | `gh-aw-validation.yml` | push / PR to `main` on gh-aw files; manual | Pin `gh aw` to `v0.82.14`, compile custom EventRelay `.md` workflows, and run validate + actionlint + zizmor + poutine checks |
>>>>>>> origin/main
| CodeQL Analysis | `codeql-analysis.yml` | push / PR to `main`; weekly (Mon 06:00 UTC) | Static security analysis for JavaScript/TypeScript and Python |
| Security Scan | `security.yml` | push / PR to `main`; weekly (Sun 00:00 UTC) | npm audit, Python safety, bandit, Trivy image scan |
| Dependency Review | `dependency-review.yml` | PR to `main`,`develop` | Review new dependencies for vulnerabilities and license policy |
| Secret Scan | `secret-scan.yml` | push to `main`; all PRs | gitleaks scan of the working tree |
| Dependabot Auto Merge | `dependabot-auto-merge.yml` | `pull_request_target`, `check_suite` | Approve and auto-merge patch/minor Dependabot PRs (majors excluded) |
| PR Checks | `pr-checks.yml` | PR opened/edited/synchronize | Validate PR title (conventional commits) and description |
| Auto Label | `auto-label.yml` | PR opened/reopened/synchronize | Label PRs by changed file type (docs, tests, python, etc.) |
| Auto-Assign Issues | `auto-assign.yml` | issue opened | Assign new issues to the repository owner |
| Issue Triage | `issue-triage.yml` | issue opened | Auto-label new issues by keyword and post a triage comment |
| Phase Goal Tracker | `phase-goal-tracker.yml` | issue opened/edited/reopened; manual | Track phase checklist progress, comment status, auto-close when complete |
| Bulk Issue Processor | `bulk-issue-processor.yml` | manual | Bulk label / summarize / close-stale across many issues |
| Close stale issues | `stale.yml` | daily (00:00 UTC) | Mark and close stale issues and PRs |
| Branch Cleanup | `branch-cleanup.yml` | manual; push sentinel on `claude/branch-cleanup-*` | Gated archive-then-delete of branches (dry-run by default); push `[restore-branch:<branch>]` sentinel to restore a deleted branch from its archive tag |
| E2E Tests | `e2e-tests.yml` | push / PR to `main` | Run Vitest E2E pipeline tests against production or the PR's Vercel preview deployment and report results on the PR |
<<<<<<< HEAD
| Autonomous Video Processing | `autonomous-video-processing.yml` | manual | Batch-process YouTube videos by category (matrix) |
=======
| Autonomous Video Processing | `autonomous-video-processing.yml` | manual; `workflow_call` | Batch-process YouTube videos by category (matrix) through the ATLAS→PRISM→FORGE→SENTINEL stage pipeline, emitting per-video correlation-ID manifests |
>>>>>>> origin/main
| Real Video Processing (Cloud) | `real-processing.yml` | manual | Process a single video: transcript and/or AI analysis |
| API-cost PostgreSQL | `api-cost-postgres.yml` | push / PR when substrate changes; manual | Exercise fresh, upgrade-from-002, and round-trip migrations plus runtime-role integration tests on PostgreSQL 16 |
| Deploy to Google Cloud Run | `deploy-cloud-run.yml` | manual | Run migrations, deploy the bounded delivery-disabled worker, then promote a tested API candidate |
| Emergency Stop | `emergency-stop.yml` | manual (typed confirmation) | Operational kill-switch announcement for running automation |

## Key Workflows

### CodeQL Analysis — `codeql-analysis.yml`

Static analysis for security vulnerabilities and code-quality issues using
GitHub CodeQL.

- Runs on push and PRs to `main`, plus a weekly scheduled scan (Mondays 06:00 UTC).
- Matrix over JavaScript/TypeScript and Python.
- Uses the custom config at `.github/codeql/codeql-config.yml` (path exclusions,
  `security-extended` query suite).
- Requires permissions: `contents: read`, `security-events: write`, `actions: read`.

Dependency / supply-chain scanning is intentionally **not** part of this
workflow — it is covered by `dependency-review.yml` (PR time) and `security.yml`
(scheduled and push).

### Security Scan — `security.yml`

Comprehensive dependency and image scanning:

- **npm audit** — Node dependency vulnerabilities.
- **safety** — Python dependency vulnerabilities.
- **bandit** — Python static security analysis.
- **trivy** — builds the Docker image and scans OS + library layers; uploads
  SARIF to the Security tab.

Runs on push and PRs to `main` and weekly on Sunday at midnight UTC.

### Coverage — `coverage.yml`

Generates pytest coverage and uploads lcov to Qlty.

- Runs on push/PR to `main` and `develop`, and can be run manually
  (`workflow_dispatch`).
- Requires the `QLTY_COVERAGE_TOKEN` repository secret. Get the token from
  <https://qlty.sh>, then add it under **Settings → Secrets and variables →
  Actions**.
- Coverage HTML and lcov are stored as artifacts for 30 days.
<<<<<<< HEAD
=======
- The test step is authoritative (`--cov-fail-under=90`, no `continue-on-error`,
  no `|| true`) so failures cannot report green.

### Autonomous Video Processing — `autonomous-video-processing.yml`

The batch video pipeline. It is the repository's first reusable workflow
(`workflow_call`), so it also establishes the convention: `workflow_dispatch`
and `workflow_call` declare the *same* input names and every step reads them
through the `inputs` context (never `github.event.inputs`), so a single job body
serves both triggers.

All logic lives in versioned, unit-tested scripts rather than inline heredocs:

| Script | Job | Responsibility |
|--------|-----|----------------|
| `scripts/ci/autonomous_video_plan.py` | `prepare` | Build the category matrix; fail closed if the batch exceeds the video or model-call cap |
| `scripts/ci/autonomous_video_processing.py` | `process` | Discover videos, run the stage pipeline, write the manifest tree |
| `scripts/ci/autonomous_video_summary.py` | `summary` | Aggregate per-category manifests into the run status and workflow outputs |

**Modes.** `pipeline_mode: discovery` (default) discovers candidates and writes
manifests without invoking any generation API — this is the dry-run path for the
whole pipeline. `pipeline_mode: full` executes every stage and fails closed while
the Phase 2 agents are unimplemented.

**Stage roles.** ATLAS, PRISM, FORGE and SENTINEL are role labels mapped onto the
existing `PipelineOrchestrator` stages (`video-ingest`, `research-grounding`,
`code-gen`, `quality-gate`) — see `STAGES` in
`scripts/ci/autonomous_video_processing.py`. They are deliberately *not* a second
agent system.

**Evidence.** Each run writes a manifest tree retained for 30 days:

```
pipeline_output/<category>/run.json
pipeline_output/<category>/videos/<video_id>/manifest.json
pipeline_output/<category>/videos/<video_id>/stages/{atlas,prism,forge,sentinel}.json
```

Every video carries a deterministic correlation ID that is repeated in each stage
record, so any artifact can be linked back to its originating run.

**Guardrails.**

- `max_videos_per_run` and `max_model_calls` are enforced in `prepare`, before any
  external call; an over-budget batch never starts.
- Discovery returning zero videos is a failure, not an empty success.
- A video is `delivered` only when every stage — including the terminal SENTINEL
  QA stage — reports success. The deliverables artifact upload is conditioned on
  that status, so a blocked run publishes evidence but never deliverables.
>>>>>>> origin/main

### Deploy to Google Cloud Run — `deploy-cloud-run.yml`

The only backend deployment path. It remains manual (`workflow_dispatch`) so a
protected-environment reviewer can approve the exact tested SHA. The workflow
requires all three PostgreSQL migration checks, authenticates only through
Workload Identity Federation, pins numeric secret versions, migrates before
either runtime, promotes the API only after candidate readiness succeeds, and
reuses the latest successful staging run's exact image digest in production.

## Adding More Workflows

1. Create a new `.yml` file in this directory (always include a top-level
   `name:`).
2. Follow the GitHub Actions syntax and pin third-party actions to a tag or SHA.
3. Define triggers, jobs, and steps; scope `permissions` to the minimum needed.
4. Test locally with `act` or on a branch before merging.
5. Add a row to the **Workflow Catalog** table above.

## Maintenance Log

A full audit of this directory was performed (see
`.github/workflows/AUDIT.md` for the per-file decision matrix). Summary:

- **Removed** `deploy.yml` — referenced a non-existent `deployments/` tree
  (actual infra lives in `infrastructure/`) and duplicated
  `deploy-cloud-run.yml`.
- **Removed** `mcp-optimization.yml` — targeted the non-existent
  `mcp-servers/mcp-profiling/` directory, so every run failed.
- **Removed** `verify-litert-mcp.yml` and `vision-reasoning.yml` — both only
  exercised the `mcp-servers/` tree, which was deleted in the dead-code cleanup;
  with the target modules gone every run failed, so the workflows were removed.
- **Renamed** `.yaml` → `stale.yml` — the file had no basename.
- **Fixed** `codeql-analysis.yml` — removed the fragile OWASP dependency-check
  job (`@main`, dead paths) and switched the Node cache from a dead
  `frontend/node_modules` path to the npm cache (`~/.npm`), which works with the
  repo's npm workspaces.
- **Fixed** `coverage.yml` — added a `name:` and the `workflow_dispatch`
  trigger the docs already described.
- **Fixed** `auto-assign.yml` — replaced `gh issue edit` with the REST
  assignees endpoint after run logs showed GitHub App installation tokens cannot
  use the CLI's GraphQL assignable mutation for this assignment.

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CodeQL Action](https://github.com/github/codeql-action)
- [Qlty Coverage Action](https://github.com/qltysh/qlty-action)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)


| Agent completion enforcement | `agent-completion-enforcement.yml` | `pull_request_target`; manual | Creates the independent, head-bound `Agent completion enforcement` Check from protected default-branch code. |
<<<<<<< HEAD
=======
| PR Governance | `pr-governance.yml` | `pull_request_target` (opened/edited/reopened/synchronize/ready_for_review) | Validates that every ready PR links exactly one real open canonical issue and contains non-empty delivery evidence sections; fails on competing PRs. |
| Repository Reconciliation | `repository-reconciliation.yml` | daily (13:17 UTC); manual | Non-destructive daily report of ready PRs missing a canonical issue, issues with competing implementation PRs, and stale unattached branches. |
>>>>>>> origin/main

## Agent-completion enforcement

`pr-checks.yml` retains the advisory `agent-completion/truth-gate/pr-<number>` status; it is never required. `agent-completion-enforcement.yml` runs protected default-branch code, does not execute PR code, and creates the separate **Agent completion enforcement** Check directly on the PR head SHA. It accepts only an exact-head, machine-readable report published by the configured dedicated GitHub App. Missing, stale, edited/deleted, ambiguous, or untrusted evidence fails closed.

Before enabling the rule, provision `.github/agent-lock/trusted-publishers.json` through protected review with the trusted App and actor allowlists. Empty lists intentionally block. Configure the repository ruleset to require **Agent completion enforcement**, one independent approval, and resolved conversations. Do not require `agent-completion/truth-gate`.