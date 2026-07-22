# Workflow Audit — Decision Matrix

Audit of every workflow file in `.github/workflows/`. Verdicts: **KEEP**
(no change), **FIX**, **DELETE**, **MERGE**. Each non-keep verdict lists the
concrete reason, verified against the actual repository tree.

## Decision Matrix

| File | Verdict | Reason |
|------|---------|--------|
| `.yaml` → `stale.yml` | **FIX (rename)** | File had no basename (literally `.yaml`); renamed to `stale.yml`. Content (daily stale-bot) is sound. |
| `auto-assign.yml` | **FIX** | Replaced `gh issue edit` with the REST assignees endpoint. The CLI command used GraphQL `replaceActorsForAssignable`, which fails for this repository's GitHub App token when assigning the issue owner. |
| `auto-label.yml` | KEEP | Labels PRs by changed file type; guarded with try/catch. |
| `autonomous-video-processing.yml` | KEEP | Manual matrix batch processor; well-formed, scoped permissions. |
| `branch-cleanup.yml` | **FIX** | Added `workflows: write` permission (missing permission caused push of restored branch to fail with "refusing to allow a GitHub App to create or update workflow ... without `workflows` permission"). Also restored push-sentinel trigger for `claude/branch-cleanup-*` branches and the restore-branch step, and removed the incorrect NOTE claiming restoration of workflow-containing branches is impossible with this token. |
| `bulk-issue-processor.yml` | KEEP | Manual bulk issue ops via `gh` + Python; dry-run default. |
| `ci.yml` | **FIX** | Added blocking `apps/web` type-check and ESLint steps before the build so CI fails fast on TypeScript or lint regressions. |
| `codeql-analysis.yml` | **FIX** | Removed the OWASP `dependency-check` job — pinned to unstable `@main` and pointed at dead paths (`frontend/node_modules`, `src/mcp-bridge.py`); produced no usable SARIF. Switched the Node cache from the dead `frontend/node_modules` path to the npm download cache (`~/.npm`), which is correct for this npm-workspaces repo. CodeQL analysis itself retained. Dependency coverage already lives in `dependency-review.yml` + `security.yml`. |
| `coverage.yml` | **FIX** | Added a top-level `name:` and the `workflow_dispatch` trigger the README already documented as available. |
| `gh-aw-validation.yml` | **ADD** | Adds pinned gh-aw (`v0.82.14`) validation for EventRelay's custom markdown workflows. Enforces compile/validate plus actionlint, zizmor, and poutine checks, and verifies committed lock files. |
| `dependabot-auto-merge.yml` | KEEP | Comprehensive guards (same-repo, non-draft, SHA match, major excluded). |
| `dependency-review.yml` | KEEP | PR dependency review with documented allow-lists. |
| `deploy-cloud-run.yml` | KEEP | The real deployment path (GCP Cloud Run); manual dispatch. |
| `deploy.yml` | **DELETE** | References a non-existent `deployments/` tree (manifests/terraform); actual infra is `infrastructure/`. The validate job hard-`exit 1`s on missing manifests. Generic multi-cloud (AWS+Azure+Slack) scaffold that duplicates `deploy-cloud-run.yml`. |
| `e2e-tests.yml` | **FIX** | Resolve the PR's Vercel preview deployment via the GitHub Deployments API before E2E runs, and skip the PR-comment step for forked `pull_request` runs where `GITHUB_TOKEN` is read-only (`Resource not accessible by integration`). Same-repo PRs still get comments. |
| `emergency-stop.yml` | KEEP | Manual operational kill-switch with typed confirmation. |
| `eventrelay-ci-investigator.md` / `.lock.yml` | **FIX** | Require a dedicated `CODEX_API_KEY` credential in pre-agent steps so Codex-specific runs fail fast with an explicit key-missing error instead of ambiguous fallback behavior. |
| `issue-triage.yml` | KEEP | Keyword auto-labeling + triage comment on new issues. |
| `mcp-optimization.yml` | **DELETE** | Entire workflow targets `mcp-servers/mcp-profiling/` (requirements.txt, investigator_client.py, profiling_server.py) which does not exist — every run fails. |
| `phase-goal-tracker.yml` | KEEP | Tracks markdown checklists on phase issues, keeps a single status comment updated, and auto-closes the issue when all checklist goals are complete. |
| `pr-checks.yml` | KEEP | Validates PR title/description; fork-safe comment handling. |
| `real-processing.yml` | KEEP | Manual single-video processing; well-formed. |
| `secret-scan.yml` | KEEP | gitleaks on the working tree; action pinned to SHA, checksum-verified install. |
| `security.yml` | KEEP | npm audit, safety, bandit, trivy; uploads SARIF. |
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

All 21 remaining workflow files were parsed with PyYAML after the changes — all
valid. Referenced paths were checked against the working tree:

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

| `agent-completion-enforcement.yml` | **ADD** | Protected-default-branch verifier that creates the independent **Agent completion enforcement** Check directly against the PR head SHA. It accepts only an exact-head machine-readable report from the configured dedicated GitHub App; missing/stale/mutable evidence, untrusted label provenance, and custom roles all fail closed. The existing `agent-completion/truth-gate` status stays advisory and must not be made required. |

The protected policy at `.github/agent-lock/trusted-publishers.json` starts with empty allowlists and therefore blocks until a repository administrator provisions the dedicated App and trusted actor identities through protected review. The repository ruleset must then require **Agent completion enforcement**, one independent approval, and resolved conversations.