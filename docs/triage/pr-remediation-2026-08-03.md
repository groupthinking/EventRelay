# PR Remediation & Publish — 2026-08-03

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge). CodeRabbit handle: `@coderabbitai`.

## Definition-of-done outcome (read first)

**No PR reached `MERGED` this run, and that is the correct outcome.** The Publish Gate is
human-by-default: `auto_merge_policy: label:automerge`, and **no open PR carries the
`automerge` label**. `main` is a protected branch. Per the runbook's Section 8 and the
standing "no auto-merge to a protected branch without human sign-off" rule, every
merge-ready PR terminates at `HALTED(awaiting_merge_approval)` with the merge command
staged — it does not get merged autonomously.

The two genuinely green PRs (**#1285, #1288**) need exactly one human action: click merge.

## Scan

**70 open PRs.** Non-draft (ready): **5** — `#1280 #1281 #1285 #1288 #1289`.
Draft: **65** → all `DEFERRED(draft)` per the Scope Gate (work-in-progress, not ready
for the publish pipeline).

Live status matrix for the 5 ready PRs (real CI / review / mergeable), oldest-first:

| PR | Author | Title | CI (real) | Review | Action taken | Terminal state |
|----|--------|-------|-----------|--------|--------------|----------------|
| 1280 | palette bot | fix(a11y): ARIA label on search clear button | ❌ truth-gate `invalid_payload` (+ Vercel false-red) | none | diagnosed; systemic gate blocker, not PR-fixable | `HALTED(ci_failing_systemic)` |
| 1281 | sentinel bot | fix(security): route API errors through formatter | ❌ truth-gate `invalid_payload` (+ Vercel false-red) | none | diagnosed; systemic gate blocker, not PR-fixable | `HALTED(ci_failing_systemic)` |
| 1285 | groupthinking | fix(ci): surface collection errors behind `invalid_payload` | ✅ green | ✅ CodeRabbit **approved** | verified green + reviewed | `HALTED(awaiting_merge_approval)` |
| 1288 | groupthinking | perf: scan processed-video cache off the event loop | ✅ green | ✅ CodeRabbit review completed | verified green + reviewed | `HALTED(awaiting_merge_approval)` |
| 1289 | groupthinking | fix(codegen): real health timestamp + fail-closed scaffolding | ✅ green | truth-gate passed | verified real diff vs `origin/main`; merge-ready | `HALTED(awaiting_merge_approval)` |

Legend: **truth-gate** = `agent-completion/truth-gate/pr-<n>` GitHub Actions check;
**false-red** = a "Canceled from the Vercel Dashboard" commit status that is red while
every required check is green — safe to ignore (same pattern as prior runs).

## Finding 1 — the `invalid_payload` truth-gate is a systemic blocker (~47 PRs)

`#1280` and `#1281` fail `agent-completion/truth-gate` with `invalid_payload`. This is
**not** a defect in either PR's diff. Per the test docstring added by **#1285**
(`tests/unit/test_agent_completion_gate.py`), this reproduces
*"the production failure that blocked ~47 open PRs: branches matching the agent heuristic
(`claude/*`, `codex/*`, ...) are marked applicable, but with no linked AgentTask issue the
collector emits `agent_login`/`run_id` as null."* The gate then correctly fail-closes.

Because the root cause is the **applicability heuristic + missing AgentTask linkage**, no
per-PR code change clears it. The fix is architectural and needs a human decision:
- **Option A** — link each affected PR to an AgentTask issue so the collector can populate
  `agent_login`/`run_id`; or
- **Option B** — narrow the gate's applicability heuristic so bot/label PRs without an
  AgentTask are marked `not_applicable` instead of `applicable`+blocked.

**Important:** merging **#1285 will not turn #1280/#1281 green.** #1285 is a *diagnostics*
change only — it keeps `verdict`/`reasons` byte-identical and merely adds the underlying
`collection_errors` to `details`. It makes the failures self-explaining; it does not
unblock them. It is still worth merging (it is green, reviewed, and improves every future
`invalid_payload` report), but it is not the unblock.

## Finding 2 — #1289 is merge-ready (CORRECTED — it is NOT superseded)

> **Correction.** An earlier version of this doc called #1289 "superseded, recommend
> close." That was an error: it compared #1289's head to the local workspace tip
> (`a15e4bd`, which happened to be #1289's own head) instead of to `origin/main`.
> Verified against `origin/main` (`94b517c`):
> - `origin/main:src/youtube_extension/backend/code_generator.py:1172` **still emits the
>   constant `"2024-01-01T00:00:00Z"`** health timestamp — the exact defect #1289 fixes.
> - `a15e4bd` is **not an ancestor of `origin/main`** — the fix is genuinely absent from main.
> - `mergeable_state: clean`; all checks green (CodeRabbit skipped-by-label, Vercel
>   deployed, `agent-completion/truth-gate/pr-1289` = `not_applicable: all rules passed`).

`#1289` is therefore a legitimate, green, conflict-free PR that re-lands the #1257 codegen
fix which `main` still lacks. **Recommend: MERGE #1289** (not close). It is `HALTED` only on
the human Publish Gate — it carries no `automerge` label and `main` is protected, so this
routine does not merge it autonomously.

## Staged next commands (human gate — not executed)

```bash
# 1. Merge the three green, reviewed PRs (protected branch → human click required):
gh pr merge 1285 --squash --repo groupthinking/eventrelay   # CodeRabbit-approved, truth-gate passed
gh pr merge 1288 --squash --repo groupthinking/eventrelay   # green, review completed
gh pr merge 1289 --squash --repo groupthinking/eventrelay   # green + clean; re-lands #1257 codegen fix main still lacks

# 2. Unblock #1280/#1281 (architectural — pick one, then re-run the gate):
#    A) link each PR to an AgentTask issue, OR
#    B) adjust the truth-gate applicability heuristic (scripts/ci/agent_completion_gate.py)
```

## Drafts (65) — `DEFERRED(draft)`

All 65 remaining open PRs are drafts and are skipped by the Scope Gate. They span the
usual streams (dependabot bumps, `claude/determined-maxwell-*` fixes, `jules-*`,
`sentinel-*`, `palette-*`, `bolt-*` perf/a11y work, and prior `docs(triage)` runs). None
are ready for the publish pipeline until marked ready-for-review by their authors.

## Loop determination

**No more autonomous work remains.** Every open PR is in a terminal state: 65
`DEFERRED(draft)`, 3 `HALTED(awaiting_merge_approval)` (#1285, #1288, #1289 — green, one
human click each), 2 `HALTED(ci_failing_systemic)` (#1280, #1281 — architectural, human
decision). There is no action that advances any PR to `MERGED` without human sign-off, so
the remediation loop halts here rather than spinning.

_Update (webhook `pull_request.review_requested` on #1289): re-verified #1289 against
`origin/main` and corrected Finding 2 — it is merge-ready, not superseded. State unchanged
otherwise; still human-gated on merge._
