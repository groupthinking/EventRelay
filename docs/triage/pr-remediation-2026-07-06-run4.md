# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (#514, 2026-07-06), whose exit condition —
*"re-run when the owner clears a gate (lands #513, reviews #508/#510, or rebases/closes
the stale set)"* — has now been met: the owner landed #513.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy applied (unchanged):** merge only demonstrably-safe, auto-approved,
  **CI-only Dependabot _action_ pins**; hold anything carrying a documented breaking
  change, deploy/runtime blast radius, or a branch-protection block for owner sign-off.
  `deploy-cloud-run.yml` is `workflow_dispatch`-only, so a merge to `main` runs CI but
  does **not** trigger a production deploy.

## What changed since run 3

The owner cleared the primary run-3 gate and several carry-overs. `origin/main` now
contains (top of history `a747d80`):

- **#513** — npm minor/patch group bump + postcss security override — **MERGED**
  (this was run-3's headline "land #513" gate).
- **#514** — run-3 triage doc — **MERGED**.
- **#512** — run-2 triage doc — **MERGED**.
- **#511** — `ci(e2e)` prod-noise cleanup (was DEFERRED as a draft in run 3) — **MERGED**.
- **#509** — npm minor/patch group (21 pkgs) — **auto-closed by Dependabot**, superseded
  by the merged #513 (run-3 staged `close 509` as the follow-up; it closed itself).

Net effect: the open set dropped **14 → 10**. No further action was required from this
routine on any of the cleared PRs — closing #509 was the one staged command and Dependabot
performed it automatically when the equivalent change landed.

## Oldest-first disposition (current open set, 10 PRs)

All ten are **unchanged since run 3** — no new commits, reviews, or CI transitions — and
each remains at a human gate. States carried forward from run 3's live scan.

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | CI fail (Vercel preview); large (40 files, +5.8k/-1.8k) | `dirty` (merge conflict) | Left for owner — needs rebase + review | HALTED(merge_conflict) |
| #365 | owner | 06-21 | CI fail (Vercel preview); AI Gateway feature | — | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | CI fail (Vercel preview); Dockerfile rewrite | — | Left for owner review | HALTED(needs_review) |
| #433 | jules[bot] | 06-28 | CI fail (Vercel canceled); orphaned-history artifact | inflated diff from `main` rewrite | Recommend close + re-cut clean test branch | HALTED(orphaned_history) |
| #442 | owner | 06-29 | CI fail (Vercel preview); orphaned-history artifact, dup of #441 | inflated diff | Recommend decide #442 vs #441, close redundant | HALTED(orphaned_history) |
| #474 | owner | 07-03 | CI fail (Vercel preview); docstrings | — | Left for owner review | HALTED(needs_review) |
| #494 | owner | 07-03 | draft; implements #487's tests | — | High-value draft — recommend un-draft | DEFERRED(draft) |
| #495 | Copilot | 07-04 | draft; removes committed API keys, fixes imports | — | High-value draft — recommend un-draft + rotate leaked keys | DEFERRED(draft) |
| #508 | dependabot | 07-04 | green (required); `unstable` (Vercel non-required) | none | **Held — `vite` 6→8, two-major bundler bump; owner requested as reviewer** | HALTED(awaiting_review) |
| #510 | dependabot | 07-04 | green (required); `unstable` | none | **Held — `chrome-devtools-mcp` 0.10.2→1.5.0, pre-1.0→1.x major** | HALTED(awaiting_review) |

## Staged commands (owner sign-off required)

**New Dependabot bumps — review each breaking note, then:**
```
gh pr merge 508 --squash   # vite 6.4.3 → 8.1.3: TWO major versions. Smoke-test the web build
                           # (apps/web) before merging — bundler majors can break config/plugins.
gh pr merge 510 --squash   # chrome-devtools-mcp 0.10.2 → 1.5.0: pre-1.0 → 1.x major. Verify the
                           # MCP devtools integration still starts.
```

**Cleanup / drafts:**
```
gh pr close 433            # orphaned-history artifact; re-cut a clean unit-test branch if wanted
# decide #442 vs #441 (identical cleanup) and close the redundant one
# un-draft #494 and #495 when ready (rotate any leaked keys #495 removes)
```

**Stale/large — owner review:** #327 (rebase to clear conflict), #365, #414, #474.

## Systemic note — Vercel preview check

The non-required **Vercel** preview-deployment status continues to fail on the older PRs
(#327, #365, #414, #433, #474) and pass on the recent ones (#508, #510). It correlates
with branch staleness / deploy-config drift, is **not a required check**, and does not
block merge. Flagging only so it isn't mistaken for a per-PR code defect. (Run 3's #511 —
now merged — removed the separate self-committing E2E-noise source, so this Vercel-preview
status is the only remaining cosmetic-red signal on the stale set.)

## Is more work needed?

**No.** The routine's two auto-mergeable categories (owner-cleared production fixes; CI-only
Dependabot action pins) are both empty this run. The one automatable follow-up run 3 staged
— close the #513-superseded #509 — Dependabot executed on its own. Every remaining open PR
is at a human gate:

- Two Dependabot bumps with real app blast radius (#508 two-major bundler, #510 pre-1.0→1.x
  major) — deliberately **not** auto-merged unattended; owner review staged above.
- Two high-value drafts (#494 tests, #495 key-removal) awaiting un-draft.
- Two orphaned-history artifacts (#433, #442) awaiting a close/dedup decision.
- Four stale/large/conflicted PRs (#327, #365, #414, #474) awaiting owner review or rebase.

The loop's automatable work has converged. Re-run when the owner clears a gate (reviews
#508/#510, un-drafts #494/#495, or closes/rebases the stale set).
