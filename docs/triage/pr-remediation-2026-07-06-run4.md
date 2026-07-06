# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (#514, 2026-07-06), whose exit condition —
*"re-run when the owner clears a gate (lands #513, reviews #508/#510, or rebases/closes
the stale set)"* — was met: the owner landed #513 and cleared #509 / #511 / #512.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy applied (unchanged):** merge only demonstrably-safe, auto-approved,
  **CI-only Dependabot _action_ pins**; hold anything carrying a documented breaking
  change, deploy/runtime blast radius, a branch-protection block, or a merge conflict for
  owner sign-off.

## What changed since run 3

The owner cleared the run-3 gate:

- **#513** npm minor/patch group + postcss security override — **MERGED** (supersedes #509)
- **#509** superseded npm group bump — **CLOSED**
- **#511** ci(e2e) prod-noise cleanup — **MERGED**
- **#512** run-2 triage doc — **CLOSED/MERGED**

**No new PRs were opened.** The open set only shrank. The two Dependabot bumps that run 3
staged for owner review are still open and still owner-gated — and **#510 has _degraded_**:
it was `mergeable_state: none` in run 3 and is now `dirty` (merge conflict), and its
0.10.2 → 1.5.0 release notes flag an install-script (`prepare`) change — an extra
supply-chain reason to keep it under owner review rather than auto-merge.

## Oldest-first disposition (current open set)

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | CI fail (Vercel preview); large (40 files, +5.8k/-1.8k) | `dirty` | Left for owner — needs rebase + review | HALTED(merge_conflict) |
| #365 | owner | 06-21 | CI fail (Vercel preview); AI Gateway feature | — | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | CI fail (Vercel preview); Dockerfile rewrite | — | Left for owner review | HALTED(needs_review) |
| #433 | jules[bot] | 06-28 | CI fail; orphaned-history artifact | inflated diff | Recommend close + re-cut clean test branch | HALTED(orphaned_history) |
| #442 | owner | 06-29 | CI fail; orphaned-history artifact, dup of #441 | inflated diff | Recommend decide #442 vs #441, close redundant | HALTED(orphaned_history) |
| #474 | owner | 07-03 | CI fail (Vercel preview); docstrings | — | Left for owner review | HALTED(needs_review) |
| #494 | owner | 07-03 | draft; implements #487's tests | — | High-value draft — recommend un-draft | DEFERRED(draft) |
| #495 | Copilot | 07-04 | draft; removes committed API keys, fixes imports | — | High-value draft — recommend un-draft + rotate leaked keys | DEFERRED(draft) |
| #508 | dependabot | 07-04 | green (required); `unstable` (Vercel non-required); owner is requested reviewer | none | **Held — `vite` 6→8, two-major bundler bump; smoke-test web build** | HALTED(awaiting_review) |
| #510 | dependabot | 07-04 | `dirty` (newly conflicted); pre-1.0→1.x major; install-script change | conflict | **Held — needs `@dependabot rebase` + owner review of the `prepare` script change** | HALTED(merge_conflict) |

## Staged commands (owner sign-off required)

```
# Dependabot majors — review each breaking note, then:
gh pr merge 508 --squash        # vite 6.4.3 → 8.1.3: TWO major versions. Smoke-test apps/web build first.
gh pr comment 510 --body "@dependabot rebase"   # clear the new conflict, THEN review the install-script
                                                # (prepare) change before any merge; pre-1.0 → 1.x major.

# Stale / orphaned-history — owner review or close:
gh pr close 433                 # orphaned-history artifact; re-cut a clean unit-test branch if wanted
# decide #442 vs #441 (identical cleanup) and close the redundant one
# rebase #327 to clear its conflict; review #365, #414, #474

# Drafts — un-draft when ready:
# #494 (implements #487's tests), #495 (rotate any leaked keys it removes)
```

## Systemic note — Vercel preview check (unchanged from run 3)

The non-required **Vercel** preview-deployment status fails on the older PRs and passes on
the recent ones. It correlates with branch staleness / deploy-config drift, is **not a
required check**, and does not block merge. Flagging only so it isn't mistaken for a
per-PR code defect.

## Is more work needed?

**No — nothing safely automatable unattended.** This run's re-scan after the owner cleared
the run-3 gate confirms both auto-mergeable categories (owner-cleared production fixes;
CI-only Dependabot action pins) are **empty**. The only two non-draft Dependabot PRs are
npm bumps with app blast radius: #508 (two-major bundler) and #510 (pre-1.0→1.x major, now
conflicted, install-script change). Everything else is a draft, an orphaned-history
artifact, or a stale/large/conflicted PR requiring owner review or a rebase outside this
session's safe scope.

The loop's automatable work has converged. **Stopping the loop.** Re-run when the owner
clears the next gate (reviews #508, rebases/reviews #510, or rebases/closes the stale set).
