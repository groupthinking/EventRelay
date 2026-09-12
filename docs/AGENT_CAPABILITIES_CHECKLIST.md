# Agent Capabilities Checklist

A concrete audit of the capabilities requested in
[groupthinking/EventRelay#1679](https://github.com/groupthinking/EventRelay/issues/1679):
agents, tools, MCP, git operations (pull/push/commit/merge), issues, code,
dependencies, database, GitHub Actions, and role assignment — mapped to what
is actually implemented in this repository today (not aspirational). See
[`REPO_MAP.md`](./REPO_MAP.md) for the directory layout referenced below.

Legend: ✅ implemented and wired up · ⚠️ present but partial/manual-only ·
❌ not implemented.

## Agents

- ✅ **Per-domain Copilot agent instructions** — `.github/agents/*.agent.md`
  (`git-ops`, `mcp`, `python-backend`, `frontend`, `testing`,
  `video-processing`, `documentation`).
- ✅ **Host-level instructions** — root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
  `SKILL.md` (each read by a different agent host: Copilot/Codex, Claude,
  Gemini CLI, generic skill loaders).
- ✅ **Application agents** — `src/agents/` (e.g.
  `mcp_ecosystem_coordinator.py`, `mcp_agent_network.py`,
  `process_video_with_mcp.py`) drive the video → event → agent pipeline.
- ⚠️ **gh-aw agentic workflows** — `canonical-pr-remediator.md`,
  `focused-coverage-controller.md`, and `repo-assist.md` (added by this
  change) run via the `github/gh-aw` compiler. All three are staged as
  read-only / report-only per `MERGE_POLICY.md`'s canonical-PR discipline;
  none currently write to branches.

## Tools / Skills

- ✅ **Agent Skills** — `.agents/skills/*/SKILL.md` (mirrored under
  `.claude/skills/`), installed from published skill packs and tracked in
  `skills-lock.json` with source + content-hash provenance, including
  `test-driven-development`, `systematic-debugging`, and
  `verification-before-completion` (source: `obra/superpowers`, the
  "Superpowers" pack listed on skills.sh) and `vercel-react-best-practices`
  (source: `vercel-labs/agent-skills`). This satisfies the issue's request
  to add 2+ skills.sh-sourced skills that add value for this repo: TDD and
  systematic debugging directly support the ≥90% pytest/coverage bar in
  `pyproject.toml`, and the Vercel React skill applies to `apps/web`
  (Next.js on Vercel).

- ✅ **Custom scripts as tools** — e.g. `tools/mcp/git_workflow_server.mjs`,
  `scripts/ci/*.py`, `scripts/maintenance/branch-fail-test.sh`.

## MCP (Model Context Protocol)

- ✅ **Host-level MCP servers configured** — `.github/mcp-servers.json` wires
  up `github`, `git-workflow`, `supabase`, `context7`, `playwright`,
  `sequential-thinking`, `sentry`, `notebooklm`, and `stitch` for the
  Copilot cloud agent host. Documented in `.github/mcp-config.md` and
  `.github/agents/mcp.agent.md`.
- ✅ **Local MCP server implementation** — `tools/mcp/git_workflow_server.mjs`
  uses `@modelcontextprotocol/sdk` (`^1.30.0`, see `package.json`) to expose
  `git_status`, `git_diff`, `git_add`, `git_commit`, `git_push`, `git_pull`
  as MCP tools over stdio.
- ✅ **Capability negotiation verified functional** — running
  `node tests/testing/test_git_workflow_client.mjs` performs a real MCP
  `initialize` handshake (via `Client.connect()`), lists the server's
  advertised tools, and invokes `git_status` end-to-end. This is the
  baseline the issue asked to confirm before adding anything further; it
  passes today (see the "MCP baseline verification" section below).
- ⚠️ **MCP Skills extension trust posture tracked (watch-only)** — SEP-2640
  compatibility is explicitly tracked as **WATCH → TEST** with trigger-gated,
  draft-only conformance scope in
  [`docs/mcp-skills-sep-2640-watch.md`](./mcp-skills-sep-2640-watch.md)
  (issue [#1640](https://github.com/groupthinking/EventRelay/issues/1640)).
- ✅ **Video-processing MCP layer** — `src/youtube_extension/mcp/`,
  `src/mcp/mcp_ecosystem_coordinator.py`, `src/mcp/mcp_video_processor.py`.
- ✅ **Standalone MCP servers** — `mcp-servers/langextract/`,
  `mcp-servers/vercel/`.

## Git operations (pull / push / PR / commit / merge)

- ✅ **Pull / push / commit** — via the `git-workflow` MCP server
  (`tools/mcp/git_workflow_server.mjs`), scoped to `GIT_WORKSPACE_ROOT`.
- ✅ **Pull request automation** — `pr-checks.yml` (title/description
  validation), `auto-label.yml`.
- ✅ **Merge automation** — `dependabot-auto-merge.yml` (patch/minor only,
  major excluded, same-repo + SHA-match guards).
- ⚠️ **Merge policy for agent-authored PRs** — `MERGE_POLICY.md` documents a
  canonical-PR-per-issue discipline; agentic workflows (`canonical-pr-*`)
  are explicitly forbidden from merging, approving, or creating competing
  PRs — human maintainers merge.

## Issues

- ✅ **Auto-assign** — `auto-assign.yml` assigns new issues via the REST
  assignees endpoint (`/repos/{repo}/issues/{n}/assignees`).
- ✅ **Auto-triage** — `issue-triage.yml` (keyword labeling + triage
  comment).
- ✅ **Phase tracking** — `phase-goal-tracker.yml` (checklist progress,
  auto-close on completion).
- ✅ **Bulk operations** — `bulk-issue-processor.yml` (manual, dry-run
  default).
- ✅ **Stale handling** — `stale.yml`.

## Code

- ✅ **Static analysis** — CodeQL (`codeql-analysis.yml`,
  JavaScript/TypeScript + Python), `ruff`/`black`/`mypy` (Python),
  ESLint (`turbo run lint`, `apps/web`).
- ✅ **AST-based code analysis tool** — `code_analyzer` in
  `src/mcp/mcp_ecosystem_coordinator.py` (also referenced in
  `.github/agents/mcp.agent.md`).
- ✅ **Code review** — GitHub Copilot code review, invoked on pull requests;
  described alongside AI-assisted issue triage in
  `.github/copilot-instructions.md`.

## Dependencies

- ✅ **Dependency review on PRs** — `dependency-review.yml`.
- ✅ **Scheduled scanning** — `security.yml` (npm audit, Python `safety`,
  `bandit`, Trivy image scan).
- ✅ **Automated updates** — `.github/dependabot.yml` +
  `dependabot-auto-merge.yml`.
- ✅ **Lockfiles committed** — `package-lock.json`, `uv.lock`,
  `skills-lock.json`, `.github/aw/actions-lock.json`.

## Database

- ✅ **ORM + migrations** — SQLAlchemy models, Alembic (`alembic.ini`,
  migrations under `infrastructure/database`).
- ✅ **Dev/prod split** — SQLite (`sqlite:///./.runtime/app.db`) for
  development, PostgreSQL for production (`DATABASE_URL`).
- ✅ **PostgreSQL integration tests** — `api-cost-postgres.yml` (fresh,
  upgrade-from-002, and round-trip migration checks against Postgres 16).
- ✅ **Shared database package** — `packages/database`.

## Actions (GitHub Actions)

- ✅ **Full catalog documented** — see
  [`.github/workflows/README.md`](../.github/workflows/README.md) for all
  workflows, triggers, and purposes (CI, coverage, CodeQL, security,
  dependency review, secret scanning, deploy, E2E, gh-aw validation, etc.).
- ✅ **gh-aw validation** — `gh-aw-validation.yml` pins `gh aw` to
  `v0.88.7`, compiles the repository's markdown-based agentic workflows,
  and runs `actionlint` + `zizmor` + `poutine` against the compiled output
  before requiring the `.lock.yml` files to match what's committed.

## Role assignment

- ✅ **Issue assignment** — `auto-assign.yml` assigns the repository owner
  to new issues.
- ✅ **Agent role separation** — `.github/agent/rules/*` and
  `.claude/agents/pr-shepherd.md` define distinct responsibilities (e.g.
  Codex as read-only canary/controller vs. Jules as the implementation
  agent per `focused-coverage-controller.md` / `canonical-pr-remediator.md`);
  `MERGE_POLICY.md` reserves merge/approve/deploy decisions for humans.
- ✅ **Least-privilege workflow permissions** — every gh-aw workflow in this
  repo declares an explicit, minimal `permissions:` block (e.g.
  `contents: read`, `issues: read`) rather than defaulting to write access.

## MCP baseline verification

Per the issue's request to confirm the baseline is functional before adding
anything else: the `git-workflow` MCP server was exercised end-to-end in
this change using the existing test client:

```bash
npm install   # installs @modelcontextprotocol/sdk (devDependency)
node tests/testing/test_git_workflow_client.mjs
```

This performs capability negotiation (MCP `initialize`), lists the tools the
server advertises, and calls `git_status`. It succeeded, confirming the MCP
baseline described in `.github/mcp-servers.json` / `.github/mcp-config.md` is
functional for this repository today.
