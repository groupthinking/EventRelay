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
| `autonomous-video-processing.yml` | **FIX** | Was a discovery loop whose "processing" step incremented a counter and printed success, so every run reported videos as processed without doing any work. Inline heredoc extracted to `scripts/ci/autonomous_video_{plan,processing,summary}.py` (lintable + unit-tested); added `workflow_call`, secret preflight, guardrail caps, per-video correlation-ID manifests, 30-day evidence retention, and a QA-gated deliverables upload. See the "Multi-agent pipeline alignment" note below. |
| `branch-cleanup.yml` | **FIX** | Restored push-sentinel trigger for `claude/branch-cleanup-*` branches and the restore-branch step. **Correction (#1405):** an earlier revision added a `workflows: write` permission to answer "refusing to allow a GitHub App to create or update workflow ... without `workflows` permission". `workflows` is not a GitHub Actions permission scope, so that key granted nothing and made the file unparseable — 1,182 zero-duration failed runs, 100% of them, on every push to every branch including `main`. The key is removed. The NOTE it also deleted was correct: `GITHUB_TOKEN` cannot create or update files under `.github/workflows/`, and no `permissions:` key lifts that, so restoring a branch whose tree contains workflow files needs a PAT with the `workflow` scope or a local push. |
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
| `pr-checks.yml` | KEEP | Validates PR title/description. Truth-gate jobs removed; see `MERGE_POLICY.md`. |
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


The agent-lock trust policy and both agent-completion Checks were removed as unsatisfiable; `pr-governance.yml` is now the sole binding gate. See `MERGE_POLICY.md`.

## Repository governance workflows

| `pr-governance.yml` | **ADD** | Validates that every non-draft ready PR links exactly one real open issue (not a PR number) with non-empty delivery evidence sections (Outcome, Risk, Verification, Production evidence). Fails closed on competing implementation PRs. Triggers on `pull_request_target`. |
| `repository-reconciliation.yml` | **ADD** | Scheduled (13:17 UTC daily) non-destructive reconciliation report: identifies ready PRs missing a canonical issue, issues with competing implementation PRs (references validated via Issues API), and stale unattached branches. Excludes draft PRs and fork-branch name collisions. Upserts a single issue titled "[automation] Repository drift report". |
## Multi-agent pipeline alignment (Phase 1)

**Gate 0 decision — map, don't duplicate.** ATLAS / PRISM / FORGE / SENTINEL are
adopted as *role labels* over the pipeline stages that already exist in
`src/agents/pipeline_orchestrator.py`, not as a parallel agent system:

| Role | Existing stage |
|------|----------------|
| ATLAS | `video-ingest` |
| PRISM | `research-grounding` |
| FORGE | `code-gen` |
| SENTINEL | `quality-gate` |
| Lead Engineer | `PipelineOrchestrator` |

The mapping is a single constant (`STAGES` in
`scripts/ci/autonomous_video_processing.py`), so Phase 2 wires runners into the
existing DAG, VERA security wrapping and `PipelineAuditStore` rather than
standing up a second roster. The alternative — new modules under
`src/agents/specialized/` — was rejected: nothing in the current roster is being
retired, and duplicating it would give EventRelay two competing pipelines, which
contradicts the single-workflow principle in `CLAUDE.md` / `GEMINI.md`.

**What Phase 1 changed.** The previous workflow's processing step was
`processed += 1` under a comment reading "Real processing hook", so every run
reported success regardless of whether anything happened. Status is now derived
from actual stage records: `discovered` → `blocked`/`failed` → `delivered`, and
`delivered` requires every stage including the terminal QA stage to succeed.
While the Phase 2 runners are unregistered, `pipeline_mode: full` fails closed
with `blocked` — an honest signal — and the default `discovery` mode terminates
at `discovery-only` without ever claiming delivery.

**What Phase 1 deliberately did not do.**

- No `agents/{atlas,prism,forge,sentinel,lead_engineer}.py` — that is Phase 2 and
  extends the existing `AgentRequest` / `AgentResult` DTOs in
  `src/youtube_extension/services/agents/dto.py`.
- No `/master-prompt-learning/session_*.md` writer — that is Phase 3 and should
  be rendered from `PipelineAuditStore` records rather than a new store.
- No `contents: write` on the workflow. Committing session records from CI needs
  elevated permissions; evidence is artifact-only until that trade-off is
  explicitly accepted.
