# GitHub Actions Workflows

This directory contains the CI/CD, security, automation, and operational
workflows for EventRelay. Each file is a self-contained GitHub Actions
workflow; this README is the index.

## Workflow Catalog

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI | `ci.yml` | push / PR to `main` | Type-check + lint `apps/web`, build the web app, lint Python (informational), run unit tests |
| Coverage | `coverage.yml` | push / PR to `main`,`develop`; manual | Generate pytest coverage and upload lcov to Qlty |
| gh-aw Validation | `gh-aw-validation.yml` | push / PR to `main` on gh-aw files; manual | Pin `gh aw` to `v0.82.14`, compile custom EventRelay `.md` workflows, and run validate + actionlint + zizmor + poutine checks |
| Canonical PR Remediator | `canonical-pr-remediator.lock.yml` | manual | gh-aw agent (compiled lock) that stages corrective remediation commits onto a canonical PR branch without direct branch writes |
| EventRelay CI Investigator | `eventrelay-ci-investigator.lock.yml` | manual | gh-aw agent (compiled lock) that investigates CI failures and emits a single deduplicated blocker record; report-first, no branch writes |
| Focused Coverage Controller | `focused-coverage-controller.lock.yml` | manual | gh-aw agent (compiled lock) read-only canary that monitors the focused Python coverage lane and surfaces gaps without modifying coverage configuration |
| CodeQL Analysis | `codeql-analysis.yml` | push / PR to `main`; weekly (Mon 06:00 UTC) | Static security analysis for JavaScript/TypeScript and Python |
| Security Scan | `security.yml` | push / PR to `main`; weekly (Sun 00:00 UTC) | npm audit, Python safety, bandit, Trivy image scan |
| Dependency Review | `dependency-review.yml` | PR to `main`,`develop` | Review new dependencies for vulnerabilities and license policy |
| Secret Scan | `secret-scan.yml` | push to `main`; all PRs | gitleaks scan of the working tree |
| Dependabot Auto Merge | `dependabot-auto-merge.yml` | `pull_request_target`, `check_suite` | Approve and auto-merge patch/minor Dependabot PRs (majors excluded) |
| PR Checks | `pr-checks.yml` | PR opened/edited/synchronize | Validate PR title (conventional commits) and description |
| Agent completion enforcement | `agent-completion-enforcement.yml` | `pull_request_target`; manual | Create an independent head-bound Check from trusted exact-SHA evidence; fail closed when the trusted publisher is not provisioned |
| Auto Label | `auto-label.yml` | PR opened/reopened/synchronize | Label PRs by changed file type (docs, tests, python, etc.) |
| Auto-Assign Issues | `auto-assign.yml` | issue opened | Assign new issues to the repository owner |
| Issue Triage | `issue-triage.yml` | issue opened | Auto-label new issues by keyword and post a triage comment |
| Phase Goal Tracker | `phase-goal-tracker.yml` | issue opened/edited/reopened; manual | Track phase checklist progress, comment status, auto-close when complete |
| Bulk Issue Processor | `bulk-issue-processor.yml` | manual | Bulk label / summarize / close-stale across many issues |
| Close stale issues | `stale.yml` | daily (00:00 UTC) | Mark and close stale issues and PRs |
| Branch Cleanup Preview | `branch-cleanup.yml` | manual | Preview the current safe/review lists; destructive cleanup is disabled until a live open-PR guard and recovery ledger are restored and tested |
| E2E Tests | `e2e-tests.yml` | push / PR to `main` | Check out the triggering SHA and block on Vitest E2E tests against that SHA's verified Vercel Production or Preview deployment |
| Autonomous Video Processing | `autonomous-video-processing.yml` | manual | Batch-process YouTube videos by category (matrix) |
| Real Video Processing (Cloud) | `real-processing.yml` | manual | Process a single video: transcript and/or AI analysis |
| API-cost PostgreSQL | `api-cost-postgres.yml` | push / PR when substrate changes; manual | Exercise fresh, upgrade-from-002, and round-trip migrations plus runtime-role integration tests on PostgreSQL 16 |
| Deploy to Google Cloud Run | `deploy-cloud-run.yml` | manual | Run migrations, deploy the bounded delivery-disabled worker, then promote a tested API candidate |
| Anthropic WIF Test | `anthropic-wif-test.yml` | push to `main`; manual | Smoke-test GitHub OIDC federation to Anthropic without a long-lived API secret |
| Hybrid Refactor Verification | `verification.yml` | PR to `refactor/hybrid-infra-v2`; manual | Run Docker, Python, security, and integration fallback gates for the hybrid-infrastructure refactor |
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
- The test step is authoritative (`--cov-fail-under=90`, no `continue-on-error`,
  no `|| true`) so failures cannot report green.

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
- **Fail-closed** `branch-cleanup.yml` and its script in preview-only mode after
  the refreshed branch list removed the advertised live open-PR guard and
  recovery ledger while retaining active PR heads.
- **Fixed** `e2e-tests.yml` — exact-SHA deployment resolution is mandatory and
  test failure now fails the workflow while retaining result reporting. The
  checkout is verified against the same SHA and deployment creator identity is
  pinned to Vercel's global bot account.

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CodeQL Action](https://github.com/github/codeql-action)
- [Qlty Coverage Action](https://github.com/qltysh/qlty-action)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)


## Agent-completion enforcement

`pr-checks.yml` retains the advisory `agent-completion/truth-gate/pr-<number>` status; it is never required. `agent-completion-enforcement.yml` runs protected default-branch code, does not execute PR code, and creates the separate **Agent completion enforcement** Check directly on the PR head SHA. It accepts only an exact-head, machine-readable report published by the configured dedicated GitHub App. Missing, stale, edited/deleted, ambiguous, or untrusted evidence fails closed.

Before enabling the rule, provision `.github/agent-lock/trusted-publishers.json` through protected review with the trusted App and actor allowlists. Empty lists intentionally block. Configure the repository ruleset to require **Agent completion enforcement**, one independent approval, and resolved conversations. Do not require `agent-completion/truth-gate`.
