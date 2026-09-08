# GitHub Copilot App & Agentic Workflow Fit — Evaluation

Decision artifact for GRV-114. Compares the GitHub Copilot desktop app and
GitHub Agentic Workflows (`gh-aw`) against what EventRelay already runs today,
and ends with an explicit adopt / trial / defer call per area. Every claim
about the current setup below is verified against this repository's tree at
the time of writing — nothing is inferred from the ticket's pasted docs.

## What EventRelay already has (verified in-repo)

- **gh-aw agentic workflows are already adopted.** Two active `.md` +
  compiled `.lock.yml` pairs (`canonical-pr-remediator`,
  `focused-coverage-controller`) plus a manually-dispatched read-only
  `repo-assist`, with lock-file sync enforced by
  `.github/workflows/gh-aw-validation.yml` and a governance test
  (`tests/unit/test_gh_aw_workflow_governance.py`) that pins the sanctioned
  set.
- **A scheduled agentic workflow was already tried and removed.** The
  `eventrelay-ci-investigator` produced noise-only output across three runs
  (GRV-105/107/113) and was deleted in commit `07b8a2ec`; the governance
  test now asserts it stays gone. That is first-hand evidence about
  unattended scheduled agents in this repo, and it argues for
  report-first/manual-dispatch designs.
- **Copilot customization is already in place.** Repo custom instructions
  (`.github/copilot-instructions.md`), per-domain agents
  (`.github/agents/*.agent.md`), MCP servers (`.github/mcp-servers.json`),
  and agent skills (`.agents/skills/`, mirrored in `.claude/skills/`,
  provenance-tracked in `skills-lock.json`). The Copilot app reads all of
  these surfaces, so it would work here with zero additional configuration.
- **Completion gating is repo-side, not client-side.** The truth-gate /
  `REAL_MODE_ONLY` policies are enforced in CI and docs, so they apply
  equally to any agent client (Copilot app, CLI, Claude Code, Codex).

## Comparison against the current workflow

### Session modes (Interactive / Plan / Autopilot)

The app's session modes map onto what the team already does with Copilot
CLI / Claude Code sessions plus repo-side gates. The added value is UI-level
mode switching and per-session model/effort selection; it does not add any
control the repo's truth-gate does not already enforce server-side.
**Verdict: nice-to-have, not a gap.**

### Parallel work (worktrees, cloud sandboxes)

Parallel isolated sessions on dedicated branches is the app's strongest
feature. EventRelay's agent work is currently serialized per session/PR.
For a solo-maintainer repo with many small agent tasks, parallel worktree
sessions could raise throughput — but the bottleneck observed in this repo's
history is review/verification capacity (canonical-PR discipline in
`MERGE_POLICY.md`), not generation capacity. More parallel generation
without more review capacity produces more stale branches, which this repo
has already paid to clean up (see `docs/branch-cleanup-*.md`).
**Verdict: trial only with a strict one-PR-at-a-time landing rule.**

### PR / review lifecycle handling

The app consolidates issue triage, PR creation, CI status, and review into
one surface. EventRelay already gets this from Linear + GitHub + agentic
remediation (`canonical-pr-remediator`), and Copilot code review can be
requested without the app. Switching surfaces has real cost (Linear is the
system of record here) and the app does not integrate with Linear.
**Verdict: no adoption driver; keep Linear-centered flow.**

### Scheduled automation (app Automations / gh-aw schedules)

This is the one area with direct negative evidence: the scheduled CI
investigator produced no safe outputs three times and was removed. App-side
"Automations" run on a user's machine/account rather than in auditable
Actions runs, which is strictly worse for this repo's provenance
requirements than gh-aw (which at least leaves compiled locks, logs, and
governance-testable artifacts).
**Verdict: defer app Automations; keep scheduled agents in gh-aw only, and
only as report-first workflows with manual dispatch until one demonstrates
signal.**

## Recommendation

**Defer** adoption of the GitHub Copilot app as a team workflow; **keep**
the existing gh-aw + repo-side-gating setup as the sanctioned agentic path.
Individual use of the app is harmless (it consumes the same
`.github/copilot-instructions.md`, agents, MCP config, and skills already in
the repo) but it should not become load-bearing: it adds a parallel surface
outside Linear, and its differentiating features either duplicate existing
capability (session modes, PR handling) or are contraindicated by this
repo's own evidence (unattended scheduled automation).

### The one experiment worth running

If parallel throughput becomes a real bottleneck: run a two-week trial where
one maintainer uses the app's parallel worktree sessions for small,
well-scoped issues, with the constraint that only one agent PR may be open
per area at a time. Measure merged-PR count and stale-branch count against
the prior two weeks. Adopt only if merged throughput rises without
stale-branch growth.

### Action items

1. ~~Remove the inert nested duplicate workflow
   `.github/workflows/.github/workflows/anthropic-wif-test.yml`~~ — done in
   the change that added this document.
2. No new Copilot app configuration is required; existing customization
   surfaces already cover it.
3. Revisit this verdict if (a) the app gains Linear integration, or (b) a
   gh-aw report-first workflow demonstrates sustained signal, making
   scheduled automation worth expanding.
