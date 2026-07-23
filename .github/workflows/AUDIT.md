# Workflow Audit — Decision Matrix

Audit of every workflow file in `.github/workflows/`. Verdicts: **KEEP**
(no change), **FIX**, **DELETE**, **MERGE**. Each non-keep verdict lists the
concrete reason, verified against the actual repository tree.

## Decision Matrix

| File | Verdict | Reason |
|------|---------|--------|
| `stale.yml` | **FIX (rename)** | File had no basename (literally `.yaml`); renamed to `stale.yml`. Content (daily stale-bot) is sound. |
| `agent-completion-enforcement.yml` | **ADD** | Protected-default-branch verifier that creates the independent **Agent completion enforcement** Check on the PR head SHA. It accepts only an exact-head machine-readable report from the configured dedicated GitHub App; missing, stale, mutable, or untrusted evidence fails closed. |
| `anthropic-wif-test.yml` | KEEP | Main/manual GitHub OIDC-to-Anthropic federation smoke test with only `id-token: write` and `contents: read`. |
| `api-cost-postgres.yml` | **ADD** | PostgreSQL 16 fresh, upgrade-from-002, and round-trip migrations plus Alembic drift, runtime-role rotation, and exact-SHA container/integration gates. |
| `auto-assign.yml` | **FIX** | Replaced `gh issue edit` with the REST assignees endpoint. The CLI command used GraphQL `replaceActorsForAssignable`, which fails for this repository's GitHub App token when assigning the issue owner. |
| `auto-label.yml` | KEEP | Labels PRs by changed file type; guarded with try/catch. |
| `autonomous-video-processing.yml` | KEEP | Manual matrix batch processor; well-formed, scoped permissions. |
| `branch-cleanup.yml` | **FIX** | Removed the invalid `workflows` permission and unsupported automatic restore. The July script refresh also removed its live open-PR guard and recovery ledger while retaining active PR heads in the `safe` list, so both workflow and script now fail closed in preview-only mode pending a separately reviewed destructive implementation. |
| `bulk-issue-processor.yml` | KEEP | Manual bulk issue ops via `gh` + Python; dry-run default. |
| `canonical-pr-remediator.lock.yml` | **ADD** | Auto-generated gh-aw lock file compiled from `canonical-pr-remediator.md`; manually dispatched agent that stages corrective remediation commits onto a canonical PR branch without performing any direct branch writes. |
| `ci.yml` | **FIX** | Added `apps/web` type-check and ESLint before the build. Type-check remains informational; ESLint, build, repository guards, and tests block. |
| `codeql-analysis.yml` | **FIX** | Removed the OWASP `dependency-check` job — pinned to unstable `@main` and pointed at dead paths (`frontend/node_modules`, `src/mcp-bridge.py`); produced no usable SARIF. Switched the Node cache from the dead `frontend/node_modules` path to the npm download cache (`~/.npm`), which is correct for this npm-workspaces repo. CodeQL analysis itself retained. Dependency coverage already lives in `dependency-review.yml` + `security.yml`. |
| `coverage.yml` | **FIX** | Added a top-level `name:` and the `workflow_dispatch` trigger the README already documented as available. |
| `gh-aw-validation.yml` | **ADD** | Adds pinned gh-aw (`v0.82.14`) validation for EventRelay's custom markdown workflows. Enforces compile/validate plus actionlint, zizmor, and poutine checks, and verifies committed lock files. |
| `dependabot-auto-merge.yml` | KEEP | Comprehensive guards (same-repo, non-draft, SHA match, major excluded). |
| `dependency-review.yml` | KEEP | PR dependency review with documented allow-lists. |
| `deploy-cloud-run.yml` | **FIX** | Protected manual exact-main-SHA deployment: Workload Identity Federation, pinned secret versions, migration-first DDL/runtime identities, bounded delivery-disabled worker, API candidate readiness/promotion, and tested-digest rollback. |
| `deploy.yml` | **DELETE** | References a non-existent `deployments/` tree (manifests/terraform); actual infra is `infrastructure/`. The validate job hard-`exit 1`s on missing manifests. Generic multi-cloud (AWS+Azure+Slack) scaffold that duplicates `deploy-cloud-run.yml`. |
| `e2e-tests.yml` | **FIX** | Check out and verify the same SHA under test, resolve only deployments created by the verified Vercel bot for that SHA (Preview on PRs, Production on main pushes), and remove job-level `continue-on-error`. Step-level result capture and the explicit failure step preserve reporting; missing preview credentials fail fast and fork PR comments remain skipped where the token is read-only. |
| `emergency-stop.yml` | KEEP | Manual operational kill-switch with typed confirmation. |
| `eventrelay-ci-investigator.lock.yml` | **ADD** | Auto-generated gh-aw lock file compiled from `eventrelay-ci-investigator.md`; manually dispatched report-first agent that investigates CI failures and emits a single deduplicated blocker record without writing to branches. |
| `focused-coverage-controller.lock.yml` | **ADD** | Auto-generated gh-aw lock file compiled from `focused-coverage-controller.md`; manually dispatched read-only canary agent that monitors the focused Python coverage lane and surfaces gaps without modifying coverage configuration. |
| `issue-triage.yml` | KEEP | Keyword auto-labeling + triage comment on new issues. |
| `mcp-optimization.yml` | **DELETE** | Entire workflow targets `mcp-servers/mcp-profiling/` (requirements.txt, investigator_client.py, profiling_server.py) which does not exist — every run fails. |
| `phase-goal-tracker.yml` | KEEP | Tracks markdown checklists on phase issues, keeps a single status comment updated, and auto-closes the issue when all checklist goals are complete. |
| `pr-checks.yml` | KEEP | Validates PR title/description; fork-safe comment handling. |
| `real-processing.yml` | KEEP | Manual single-video processing; well-formed. |
| `secret-scan.yml` | KEEP | gitleaks on the working tree; action pinned to SHA, checksum-verified install. |
| `security.yml` | KEEP | npm audit, safety, bandit, trivy; uploads SARIF. |
| `verification.yml` | KEEP | Refactor-branch/manual Docker, Python, security, and integration fallback gates. |
| `verify-litert-mcp.yml` | **DELETE** | Path-filtered smoke test of `mcp-servers/litert-mcp/server.py`; the `mcp-servers/` tree was removed in the dead-code cleanup, so the target no longer exists and every run fails. |
| `vision-reasoning.yml` | **DELETE** | Path-filtered lint/type/test of `mcp-servers/shared-state/*`; those modules were removed in the dead-code cleanup, so the workflow has nothing to run. |

## On "MERGE"

No merges were applied. The small issue/PR-automation workflows (`auto-assign`,
`auto-label`, `issue-triage`) and the security workflows (`codeql-analysis`,
`security`, `dependency-review`, `secret-scan`) overlap thematically but trigger
on different events and use different tools; consolidating them would reduce
clarity and complicate `permissions` scoping without saving real cost. The one
genuine redundancy — the dependency-check job inside `codeql-analysis.yml`
versus the dedicated dependency workflows — was resolved by removing the broken
job rather than merging.

## Verification

All 24 live workflow files were parsed with PyYAML after the changes, and every
declared `GITHUB_TOKEN` permission key was checked against GitHub's supported
permission set. Referenced paths were checked against the working tree:

- Present: `.github/codeql/codeql-config.yml`, `.gitleaks.toml`, `.trivyignore`,
  `Dockerfile`, `scripts/maintenance/branch-cleanup-delete.sh`,
  `tests/e2e/`, `tests/failure-log.md`, `apps/web` (with `build:web` script).
- Absent (drove the deletes): `mcp-servers/mcp-profiling/`, `deployments/`,
  `frontend/`, `src/mcp-bridge.py`. The entire `mcp-servers/` tree was
  subsequently removed in the dead-code cleanup, which is why
  `verify-litert-mcp.yml` and `vision-reasoning.yml` were also deleted.
- Recent run logs checked: `auto-assign.yml` failed on issue #392 because
  `gh issue edit` used a GraphQL mutation unsupported by GitHub App
  installation tokens; the workflow now calls the REST assignees endpoint.


## Agent completion enforcement

The protected policy at `.github/agent-lock/trusted-publishers.json` starts with empty allowlists and therefore blocks until a repository administrator provisions the dedicated App and trusted actor identities through protected review. The repository ruleset must then require **Agent completion enforcement**, one independent approval, and resolved conversations.
