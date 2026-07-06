# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (same day, 15:20 UTC), whose exit condition —
*"re-run when the owner clears a gate (lands #513, reviews #508/#510, or rebases/closes
the stale set)"* — has been partially met: the owner landed the #513 gate.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy (unchanged):** merge only demonstrably-safe, auto-approved,
  **CI-only Dependabot _action_ pins**; hold anything with a documented breaking change,
  deploy/runtime blast radius, or a branch-protection block for owner sign-off.

## What changed since run 3

The owner executed run 3's top staged recommendation verbatim:

- **#513** — npm minor/patch group bump + postcss security override — **MERGED** (23:34 UTC).
- **#509** — the npm minor/patch group bump it superseded (red on the `postcss@8.4.31`
  `dependency-review` gate) — **CLOSED** one second later (23:34:25), not merged. Correct:
  #513 folds in the same group bump plus the lockfile fix that clears the security gate.
- **#511** — owner **un-drafted** the E2E-noise CI-hygiene fix; it is now `open`/ready,
  `mergeable_state: blocked`, Vercel preview still deploying. Owner-active.

Open count: **14 → 12.** No PR from run 3's table that this routine could safely merge
unattended has become newly actionable.

## Oldest-first disposition (current open set — 12)

| PR | Author | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----------|-----------|--------------|----------------|
| #327 | owner | CI fail (Vercel preview); large (40 files) | `dirty` (conflict) | Left for owner — needs rebase + review | HALTED(merge_conflict) |
| #365 | owner | CI fail (Vercel preview); AI Gateway feature | — | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | CI fail (Vercel preview); Dockerfile rewrite | — | Left for owner review | HALTED(needs_review) |
| #433 | jules[bot] | CI fail; orphaned-history test artifact | inflated diff | Recommend close + re-cut clean test branch | HALTED(orphaned_history) |
| #442 | owner | CI fail; orphaned-history cleanup, dup of #441 | inflated diff | Recommend decide #442 vs #441, close redundant | HALTED(orphaned_history) |
| #474 | owner | CI fail (Vercel preview); docstrings | — | Left for owner review | HALTED(needs_review) |
| #494 | owner | draft; implements #487's tests | — | High-value draft — recommend un-draft | DEFERRED(draft) |
| #495 | Copilot | draft; removes committed API keys, fixes imports | — | High-value draft — un-draft + rotate leaked keys | DEFERRED(draft) |
| #508 | dependabot | green (required); `unstable` (Vercel non-req) | now behind main (post-#513) | **Held — `vite` 6→8, two-major bundler bump; owner requested as reviewer** | HALTED(awaiting_review) |
| #510 | dependabot | green (required); `unstable` | now behind main | **Held — `chrome-devtools-mcp` 0.10.2→1.5.0, pre-1.0→1.x major** | HALTED(awaiting_review) |
| #511 | owner | draft→**ready**; `blocked`, Vercel deploying | — | Owner just un-drafted; owner-active, awaiting required check + sign-off | HALTED(awaiting_review) |
| #512 | owner | draft; run-2 triage doc | — | Superseded by run-3/run-4 — recommend close | DEFERRED(draft) |

## Staged commands (owner sign-off required)

**Remaining Dependabot bumps — review each breaking note, then:**
```
gh pr merge 508 --squash   # vite 6.4.3 → 8.1.3: TWO major versions. Smoke-test the apps/web
                           # build (bundler majors can break config/plugins) before merging.
gh pr merge 510 --squash   # chrome-devtools-mcp 0.10.2 → 1.5.0: pre-1.0 → 1.x major.
                           # Verify the MCP devtools integration still starts.
```
Both are now behind `main` after #513 merged; GitHub can auto-update the branch on merge,
or `gh pr update-branch 508 && gh pr update-branch 510` first.

**Cleanup / drafts:**
```
gh pr close 512            # run-2 triage doc, superseded
gh pr close 433            # orphaned-history artifact; re-cut a clean unit-test branch if wanted
# decide #442 vs #441 (identical cleanup) and close the redundant one
# un-draft #494 and #495 when ready (rotate any leaked keys #495 removes)
# #511 is ready — merge once its required Vercel check goes green
```

**Stale/large — owner review:** #327 (rebase to clear conflict), #365, #414, #474.

## Is more work needed?

**No — nothing safely automatable unattended remains this run.** The routine's two
auto-mergeable categories (owner-cleared production fixes; CI-only Dependabot _action_
pins) are both empty: the owner already merged the one landable PR (#513) and closed its
superseded twin (#509) himself, and the two open Dependabot PRs (#508, #510) are both
major-version npm bumps with app blast radius that require an owner smoke-test — the
irreversible human sign-off step this routine does not bypass. Everything else is a draft
awaiting un-draft, an orphaned-history artifact, an owner-active PR (#511), or a
stale/large/conflicted PR needing owner review or a rebase outside this session's scope.

The loop's automatable work has converged. Re-run when the owner clears another gate
(reviews #508/#510, un-drafts #494/#495, or rebases/closes the stale set).
