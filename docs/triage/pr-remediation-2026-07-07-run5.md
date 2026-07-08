# PR Remediation Run — 2026-07-07 (run 5)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 4 (same day), whose exit condition — *"re-run when the owner
clears a gate"* — has been met: the owner acted on run 4's staged set and pushed a new
sub-wave (#560–#563).

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy (unchanged from runs 2–4):** merge only demonstrably-safe,
  CI-green, review-clean changes into `main` with no deploy blast radius; hold anything
  carrying a merge conflict, a breaking/regressive change, an unrun CI, or a
  branch-protection block for owner sign-off. `deploy-cloud-run.yml` is
  `workflow_dispatch`-only, so a merge to `main` runs CI but does **not** deploy.

## What changed since run 4

Main HEAD advanced to `c837900`. The owner cleared run 4's staged set:

- **#552** — docs/audit reports — **MERGED** (`c191fb3`; run 4 had flagged it as a
  no-net-content merge-commit PR, owner chose to land it)
- **#554** — vendor capabilities audit — **MERGED**
- **#547 / #550** — SQL-injection hardening — **CLOSED** (redundant with the already-merged
  #548, exactly as run 4 predicted)
- **#557 / #558** — `dazzling-edison` OTel/Sentry pin PRs — **CLOSED** (run 4's
  orphaned-history disposition, honored)

New PRs opened after run 4: **#560, #561, #562** (non-draft) and **#563** (draft).

## ⚠️ Systemic finding — CodeRabbit is out of credits

Every open PR's `CodeRabbit` status is **`failure` — "Prepaid credits exhausted — enable
usage-based reviews."** The runbook's core review-loop engine (step 4:
`@coderabbitai full review` → parse findings → fix → resolve) **cannot run** until the
owner refills CodeRabbit credits or enables usage-based billing. This is the single
biggest blocker to the runbook operating as designed; posting `@coderabbitai` commands
this cycle would be no-ops.

## ⚠️ Systemic finding — the `dazzling-edison` re-cut trap

Run 4 recommended: *"if any real gap remains, re-cut a single fix from current `main`
rather than reviving orphaned history."* The new #560 / #562 were cut **on the stale
`claude/dazzling-edison-*` branches again**, so despite fresh titles they diff against the
*pre-upgrade* `apps/web` tree and **would regress `main`**. Verified from their file diffs
against current `main`'s `apps/web/package.json`:

| dep | #560 / #562 propose | current `main` | net effect |
|-----|---------------------|----------------|------------|
| `@sentry/nextjs` | `^10.57.0` | `^10.63.0` | **regress** |
| `@opentelemetry/instrumentation` | `^0.219.0` (#562 override) | `^0.220.0` | **regress** |
| `@opentelemetry/core` / `sdk-trace-base` | `^2.8.0` | `^2.9.0` | **regress** |
| `@tailwindcss/postcss` | `^4.3.1` | `^4.3.2` | **regress** |
| `tailwindcss` | v4.3.1 (already on main) | `^4.3.1` | no-op |
| `@types/node` | `^20` | `^26` | **regress** |
| `zustand` | `^4.5.0` | `^5.0.14` | **regress** |

Both are `mergeable_state: dirty`. **Merging either reverts main's dep upgrades.** The
concerns they name (Tailwind v4 PostCSS build; OTel override) are already resolved on
`main` with newer versions. **Recommendation: close #560 and #562**; if a genuine gap
remains, cut one fix from a branch based on current `main` (not `dazzling-edison`).

## Oldest-first disposition — non-draft open set

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | large (40 files, security/frontend); CodeRabbit down | `dirty` | Carry forward — needs rebase + human review | HALTED(merge_conflict) |
| #365 | kk-agent (fork) | 06-21 | AI Gateway text+video (#269); needs review | `unknown` | Carry forward — owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | Dockerfile prod rewrite (#406) | `unknown` | Superseded by draft pair #539/#540 — owner picks one | HALTED(needs_review) |
| #553 | owner | 07-07 | vite 8 + vitest (40 files, +3.5k/−10.7k) | `dirty` | **Superseded — `main` already on vite `^8.1.3` + vitest `4.1.9`.** Close | HALTED(superseded) |
| #555 | owner | 07-07 | remove obsolete prisma `earlyAccess` flag | `dirty` | Small + safe once rebased onto `main` | HALTED(needs_rebase) |
| #556 | owner | 07-07 | revert tailwindcss → v3 | `dirty` | **Superseded — `main` on tailwind v4.** Close | HALTED(superseded) |
| #559 | owner | 07-07 | pin tailwindcss → v3 | `dirty` | **Superseded — `main` on tailwind v4.** Close | HALTED(superseded) |
| #560 | owner | 07-07 | "@tailwindcss/postcss for v4" — but orphaned `dazzling-edison` | `dirty` | **Regresses main (table above).** Close | HALTED(orphaned_history) |
| #561 | owner | 07-07 | **MCP protocol bridge: secret redaction + SSRF guard + capability routing (+213 test LOC)** | `unknown` | **Real net-new value; the one worth merging.** Trigger CI + owner sign-off | HALTED(awaiting_merge_approval) |
| #562 | owner | 07-07 | "OTEL override effective + Node engine" — but orphaned `dazzling-edison` | `unknown`→dirty | **Regresses main (table above).** Close | HALTED(orphaned_history) |

### #561 is the standout — recommend merge after CI

`fix(mcp): address Copilot review on #389`. Touches only
`src/youtube_extension/core/mcp/protocol_bridge.py` (+143/−10) and its unit test
(+213). It is **not** entangled in the deps regression (no `package.json` change). Substance:

- **Secret redaction:** protocol-request history now stores only a structural summary
  (`{keys, key_count}`) instead of the raw request dict — stops API keys / tokens / PII
  leaking into serialized-and-logged context history.
- **SSRF guard:** `OpenAIAdapter.initialize` rejects non-HTTPS / hostless / non-string
  `base_url` (blocks `http://169.254.169.254` metadata endpoint and `file://` URIs).
- **Intelligent routing:** capability-filtered, least-loaded-with-error-rate-tiebreak
  protocol selection, replacing the `TODO`/"first available" stub. Guards a bare-string
  `required_capabilities` against char-by-char iteration.
- **Tests:** 213 lines of new coverage for all of the above.

**CI caveat (honest):** the full GitHub Actions suite (test/build/lint/CodeQL) shown on
#561 is from a **stale 2026-06-22 commit**; the current head (`e8e5607`) has only run
`copilot-pull-request-reviewer` (success) + Vercel. So #561 is **not demonstrably green on
its current commit**, and CodeRabbit couldn't review it (credits). Do not merge blind —
trigger CI, confirm green, then merge. This is a publish-gate human step.

## WIP drafts + #563 — DEFERRED(draft)

#563 (`docs: align CLAUDE.md anthropic SDK floor`) is a draft. The ~20 remaining
`2026-07-07` drafts are unchanged from run 4's analysis — mostly paired Copilot + Claude
attempts at the same issue (un-draft the winner of each pair, close the loser). See run 4
for the pair table. None are actionable by this routine while draft.

## Auto-mergeable this run

**None unattended.** Every non-draft PR is `dirty` (regressive/superseded), `unknown` +
unreviewed, or awaiting CI. The one merge-worthy PR (#561) is not green on its current
head and is a substantive backend security change that warrants a real CI + review pass —
which CodeRabbit (down) cannot provide. Merging into protected `main` past these gates is
the publish-gate human step the runbook holds by default.

## Staged commands (owner sign-off required)

```bash
# 1. Refill the review engine (unblocks the whole runbook)
#    → enable usage-based CodeRabbit reviews / top up credits in the CodeRabbit dashboard

# 2. The one to MERGE — after confirming CI is green on head e8e5607
gh pr checks 561          # trigger/inspect CI on current head
gh pr merge 561 --squash  # once green + reviewed

# 3. Close the superseded / orphaned-regression set (all owner's own PRs)
gh pr close 553   # vite8+vitest — main already on vite ^8.1.3 + vitest 4.1.9
gh pr close 556   # tailwind v3 revert — main on v4
gh pr close 559   # tailwind v3 pin   — main on v4
gh pr close 560   # dazzling-edison orphan — regresses sentry/otel/tailwind/types-node
gh pr close 562   # dazzling-edison orphan — regresses sentry/otel/types-node/zustand

# 4. Rebase the small survivor
gh pr checkout 555 && git rebase origin/main && git push --force-with-lease   # then it becomes CI-checkable

# 5. Older set — owner review: #327 (rebase), #365 (fork), #414 (vs draft #539/#540)
```

## Is more work needed?

**Yes — but, as in runs 1–4, none of the terminal transitions are safely automatable
unattended.** Everything routes through the owner: merging into protected `main`
(publish gate) or closing the owner's own PRs (norm established over prior runs: this
routine *recommends*, the owner closes). The automatable analysis has converged again.

Two owner actions would unblock the most:
1. **Refill CodeRabbit credits** — the review engine is dead; the runbook's core loop is a
   no-op until this is fixed.
2. **Merge #561** (after CI) and **close the superseded/orphaned set** (#553, #556, #559,
   #560, #562). Stop re-cutting dep fixes on `claude/dazzling-edison-*` branches — they
   are orphaned history and every re-cut reintroduces a regression.

**Loop status: converged — no further autonomously-completable work this cycle.** Re-run
when the owner clears a gate (refills CodeRabbit, merges/closes the staged set, or picks
draft-pair winners), at which point the survivors become CI-checkable and mergeable.
