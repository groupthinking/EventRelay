# PR Remediation Run — 2026-07-07 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (#514, 2026-07-06), whose exit condition —
*"re-run when the owner clears a gate"* — has been met: the owner opened a large batch
of new PRs (#529–#559) and merged several others.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy applied (unchanged from runs 2–3):** merge only demonstrably-safe,
  auto-approved, CI-clean changes with no runtime/deploy blast radius; hold anything
  carrying a merge conflict, a breaking change, or a branch-protection block for owner
  sign-off. `deploy-cloud-run.yml` is `workflow_dispatch`-only, so a merge to `main`
  runs CI but does **not** trigger a production deploy.

## What changed since run 3

The owner cleared run 3's staged set and pushed a new wave of work. `origin/main` now
contains, among others:

- **#528** — pipeline-store `expire_before` + audit-store edge-case tests — **MERGED**
- **#548** — SQL identifier hardening in `database_cleanup_service` — **MERGED**
- **#554** — vendor capabilities audit doc — **MERGED** (owner, mid-scan; was `unstable`)

Main HEAD at scan time: `6f080b2 docs: add vendor capabilities audit (#554)`.

The open set has grown to **33 PRs**: 10 non-draft, 21 WIP drafts, plus #554 which
transitioned to MERGED during the scan. Critically, **every non-draft PR opened today
(#552–#559) reports `mergeable_state: dirty`** — they were cut in rapid succession off
`44565dd`/`4122c39` and now conflict (the `package-lock.json` churn is the usual magnet),
and several are **mutually redundant**.

## Oldest-first disposition — non-draft open set

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | large (40 files, +5.8k/-1.8k), security/frontend | `dirty` | Left for owner — needs rebase + review | HALTED(merge_conflict) |
| #365 | kk-agent (fork) | 06-21 | AI Gateway text+video feature (#269) | mergeable `unknown` | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | Dockerfile prod rewrite (#406) | mergeable `unknown` | Likely superseded by newer drafts #539/#540 — recommend owner pick one | HALTED(needs_review) |
| #552 | owner | 07-07 | "Merge branch main into chore/docs-audit-reports" | `dirty` | Merge-commit PR, no net content — recommend close | HALTED(merge_conflict) |
| #553 | owner | 07-07 | vite 8.0.16 + vitest bump (+3.5k/-10.7k) | `dirty` | Successor to run-3's held #508 (vite 6→8). Rebase + smoke-test web build | HALTED(merge_conflict) |
| #555 | owner | 07-07 | remove obsolete prisma `earlyAccess` flag | `dirty` | Small, safe once rebased | HALTED(merge_conflict) |
| #556 | owner | 07-07 | revert tailwindcss → v3 | `dirty` (orphaned 121) | **Superseded** — main on tailwind v4. Recommend close | HALTED(orphaned_history) |
| #557 | owner | 07-07 | add `@sentry/node-core` OTel peer deps | `dirty` (orphaned 122) | **Superseded** by main's newer Sentry/OTel set. Recommend close | HALTED(orphaned_history) |
| #558 | owner | 07-07 | align `@opentelemetry` 0.x pins to Sentry range | `dirty` (orphaned 122) | **Superseded** — merge would regress instrumentation 0.220→0.214. Commented + recommend close | HALTED(orphaned_history) |
| #559 | owner | 07-07 | pin tailwindcss → v3 (PostCSS build) | `dirty` (orphaned 121) | **Superseded** — main on tailwind v4. Recommend close | HALTED(orphaned_history) |

### The `dazzling-edison` cluster (#556–#559) — orphaned history, superseded by `main`: CLOSE all four

Triggered by `pull_request.opened` on **#558**, verified concretely. All four
`claude/dazzling-edison-*` branches are **121–122 commits behind current `main`**
(merge-bases `870daf8` / `874f022`, dated ~Jun 21). That — not a small dep conflict —
is why every one is `mergeable_state: dirty`: a merge would revert ~1,800 files, not
just adjust pins.

They target a **pre-upgrade** `apps/web/package.json`; `main` has since moved every dep
they touch *forward*, so merging any of them is a **regression**:

| dep | cluster PR wants | current `main` |
|-----|------------------|----------------|
| `@opentelemetry/instrumentation` | `^0.214.0` (#558, pins down) | `^0.220.0` |
| `@opentelemetry/exporter-trace-otlp-http` | `^0.214.0` (#558) | *removed from main* |
| `@opentelemetry/core` / `sdk-trace-base` | `^2.8.0` (#558) | `^2.9.0` |
| `@sentry/nextjs` | `^10.57.0` (#557/#558) | `^10.63.0` |
| `tailwindcss` | v3 revert/pin (#556/#559) | `^4.3.1` (v4) + `@tailwindcss/postcss ^4.3.2` |

The concern each addressed (OTel/Sentry pin alignment off `GHSA-8988-4f7v-96qf`; Tailwind
PostCSS build) is already resolved on `main` with **newer** versions. **Disposition:
close #556, #557, #558, #559** — no rebase, no dedup-and-keep-one. If any real gap
remains, re-cut a single fix from current `main` rather than reviving orphaned history.
A summary of this was posted on #558. Closing is left to the owner (their own PRs; not
auto-closed).

**#553** (vite 8 + vitest) is a *separate* concern on its own branch and is not part of
this orphaned cluster — it still needs an independent rebase + web-build smoke-test.

## WIP drafts — DEFERRED(draft)

21 drafts, all opened 2026-07-07, mostly **paired Copilot + Claude attempts at the same
issue** (owner is comparing two implementations per task). Un-draft the winner of each
pair; close the loser.

| Concern | Draft PRs |
|---------|-----------|
| Vercel AI Gateway / auto-deploy | #529 (Copilot), #530 (Claude) |
| unified_ai_sdk real providers | #532, #543 (Copilot), #544 (Claude) |
| MCP adapter real provider calls | #537 (Copilot), #538 (Claude) |
| Dockerfile ffmpeg + Node 22 | #539 (Copilot), #540 (Claude) — supersede #414 |
| GTM skill registry into MCP coordinator | #545 (Copilot), #546 (Claude) |
| SQL-injection hardening | #547 (Copilot), #550 (owner) — **note #548 already merged the same hardening; verify these aren't now redundant** |
| MCP continuity layer | #534 |
| Phase issue goal tracker workflow | #531 |
| CodeRabbit `@coderabbitai plan` guidance | #535 |
| Subagent prompt/start | #536 |
| Generic "fix issues" | #541 (Copilot), #542 (Claude) |
| Skills event-contract validator | #549 |
| pipeline-store edge tests | #551 — supersedes the now-merged #528 |

## Auto-mergeable this run

**None.** Every non-draft PR is `dirty` (conflict) or `unknown`/needs-review; drafts are
deferred by definition. The single clean-mergeable PR in the scan (#554, docs-only) was
merged by the owner during the run. There is nothing this routine can safely merge
unattended without choosing between the owner's own competing PRs.

## Staged commands (owner sign-off required)

**`dazzling-edison` cluster — orphaned + superseded by main, close all four:**
```
gh pr close 556 557 558 559   # 121-122 commits orphaned; main already has newer
                              # tailwind v4 / OTel 0.220 / sentry 10.63. Merging any regresses.
```

**Vite/vitest (#553) — separate concern, rebase + smoke-test (owner):**
```
git fetch origin chore/security/upgrade-vitest-vite && git rebase origin/main   # then verify apps/web build
```

**Superseded / obsolete:**
```
gh pr close 552          # merge-commit PR with no net content
# after choosing a Dockerfile: close #414 in favor of #539/#540 (or vice-versa)
# after verifying #548 covers it: close #547/#550 if now redundant
```

**Draft pairs — un-draft the winner, close the loser** (per the table above), e.g.:
```
# choose #539 vs #540 (Dockerfile), #529 vs #530 (Vercel), #537 vs #538 (MCP adapter), …
```

**Stale/large — owner review:** #327 (rebase to clear conflict), #365 (fork), #414.

## Is more work needed?

**Yes — but none of it is safely automatable unattended, so this routine is at a HALT
that requires the owner.** The clearest item: the entire `dazzling-edison` cluster
(#556–#559) is orphaned history that `main` has already superseded — **close all four**
(this run verified it and commented on the trigger PR #558; closing an owner's own PRs is
left to the owner). Beyond that, the blocker is *decisions between the owner's own PRs*
(which Dockerfile #414 vs #539/#540, which of each Copilot/Claude draft pair) plus the
#553 rebase — all outside this session's push scope. Merging into protected `main` past
those decisions is the publish-gate human step the runbook holds by default.

The loop's automatable work has converged again. **Re-run when the owner clears a gate** —
picks winners in the web-build cluster and the draft pairs, or rebases/closes the stale
set — at which point the survivors become CI-checkable and, if green, mergeable.
