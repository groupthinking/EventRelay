# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (#514, 2026-07-06), whose exit condition — *"re-run when
the owner clears a gate (lands #513, reviews #508/#510, or rebases/closes the stale
set)"* — has now been met.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy applied (unchanged from runs 2–3):** merge only demonstrably-safe,
  auto-approved, **CI-only Dependabot _action_ pins**; hold anything carrying a
  documented breaking change, deploy/runtime blast radius, or a branch-protection block
  for owner sign-off. `deploy-cloud-run.yml` is `workflow_dispatch`-only, so a merge to
  `main` runs CI but does **not** trigger a production deploy.

## What changed since run 3

The owner executed **run 3's entire staged plan**. `origin/main` now contains:

- **#513** — npm minor/patch group bump + postcss security override — **MERGED** (2026-07-06 23:34)
- **#509** — superseded npm group bump — **CLOSED** unmerged (one second after #513 merged), exactly as staged
- **#512** — run-2 triage doc — **MERGED**
- **#514** — run-3 triage doc — **MERGED**

No new automatable work has appeared. The residual open set is the same stale / draft /
orphaned / major-dependency-bump PRs that have always required owner review. #508 and
#510 were **not** touched by the owner in this clear-out (their head commits are still
dated 07-04); required checks stay green but both remain deliberately held for a smoke-test.

## Oldest-first disposition (current open set — 10 PRs)

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | CI fail (Vercel preview); large (40 files, +5.8k/-1.8k) | `dirty` (merge conflict) | Left for owner — needs rebase + review | HALTED(merge_conflict) |
| #365 | owner | 06-21 | CI fail (Vercel preview); AI Gateway feature | — | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | CI fail (Vercel preview); Dockerfile rewrite | — | Left for owner review | HALTED(needs_review) |
| #433 | jules[bot] | 06-28 | CI canceled; orphaned-history artifact | inflated diff from `main` rewrite | Recommend close + re-cut clean test branch | HALTED(orphaned_history) |
| #442 | owner | 06-29 | CI fail (Vercel preview); orphaned-history artifact, dup of #441 | inflated diff | Recommend decide #442 vs #441, close redundant | HALTED(orphaned_history) |
| #474 | owner | 07-03 | CI fail (Vercel preview); docstrings | — | Left for owner review | HALTED(needs_review) |
| #494 | owner | 07-03 | draft; implements #487's tests | — | High-value draft — recommend un-draft | DEFERRED(draft) |
| #495 | Copilot | 07-04 | draft; removes committed API keys, fixes imports | — | High-value draft — recommend un-draft + rotate leaked keys | DEFERRED(draft) |
| #508 | dependabot | 07-04 | required green; Vercel non-required success | none | **Held — `vite` 6→8, two-major dev-bundler bump; smoke-test `apps/web` build first** | HALTED(awaiting_review) |
| #510 | dependabot | 07-04 | required green; Vercel non-required success | none | **Held — `chrome-devtools-mcp` 0.10.2→1.5.0, pre-1.0→1.x major; verify MCP devtools starts** | HALTED(awaiting_review) |

## Staged commands (owner sign-off required)

**Major dependency bumps — smoke-test each, then:**
```
gh pr merge 508 --squash   # vite 6.4.3 → 8.1.3 (dev): TWO major versions. Smoke-test the
                           # web build (apps/web) before merging — bundler majors can break
                           # config/plugins.
gh pr merge 510 --squash   # chrome-devtools-mcp 0.10.2 → 1.5.0: pre-1.0 → 1.x major.
                           # Verify the MCP devtools integration still starts.
```

**Cleanup / drafts:**
```
gh pr close 433            # orphaned-history artifact; re-cut a clean unit-test branch if wanted
# decide #442 vs #441 (identical cleanup) and close the redundant one
# un-draft #494 and #495 when ready (rotate any leaked keys #495 removes)
```

**Stale/large — owner review:** #327 (rebase to clear conflict), #365, #414, #474.

## Systemic note — Vercel preview check

The non-required **Vercel** preview-deployment status still fails on the older PRs
(#327, #365, #414, #474) and passes on the recent ones (#508, #510). It correlates with
branch staleness / deploy-config drift, is **not a required check**, and does not block
merge. Flagging only so it isn't mistaken for a per-PR code defect.

## Is more work needed?

**No — nothing safely automatable unattended.** The routine's two auto-mergeable
categories (owner-cleared production fixes; CI-only Dependabot action pins) are empty
this run. The owner has already landed everything run 3 staged and left exactly the two
major dependency bumps (#508, #510) plus the stale/draft/orphaned residue for their own
review. Every open PR is in a recorded terminal state: `DEFERRED(draft)` ×2,
`HALTED(awaiting_review)` ×2, `HALTED(needs_review)` ×3, `HALTED(orphaned_history)` ×2,
`HALTED(merge_conflict)` ×1.

The loop's automatable work has converged. Re-run when the owner clears the next gate
(merges/smoke-tests #508 or #510, un-drafts #494/#495, or rebases/closes the stale set).
