# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (same day, 15:20 UTC), whose exit condition —
*"re-run when the owner clears a gate (lands #513, reviews #508/#510, or rebases/closes
the stale set)"* — was met **while this run was executing**.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy (unchanged):** merge only demonstrably-safe, auto-approved,
  **CI-only Dependabot _action_ pins**; hold anything with a breaking change,
  deploy/runtime blast radius, or a branch-protection block for owner sign-off.

## What changed since run 3 — owner cleared the run-3 backlog live

Between 23:34–23:36 UTC the owner merged/closed the exact PRs run 3 staged, by hand:

- **#513** npm minor/patch group + postcss security override — **MERGED** (`a86c1fe`).
  This was the gate run 3 was blocked on. Its body directed "merge this and close #509."
- **#511** ci(e2e) prod-noise cleanup — un-drafted, then **MERGED** (`a747d80`).
- **#512** run-2 triage doc — **MERGED** (`9349aa3`).
- **#509** npm minor/patch group (superseded by #513) — **CLOSED** (not merged), as directed.
- **#508 / #510** — auto-rebased by Dependabot onto the new `main` (updated 23:35–23:36 UTC);
  still the two held major-version bumps.

No open PR from run 3's table remains actionable by this routine.

## Oldest-first disposition (current open set — 10 PRs)

| PR | Author | Age | Review/CI | Action taken | Terminal state |
|----|--------|-----|-----------|--------------|----------------|
| #327 | owner | 06-19 | CI fail (Vercel preview); large (40 files) + merge conflict | Left for owner — needs rebase + review | HALTED(merge_conflict) |
| #365 | owner | 06-21 | CI fail (Vercel preview); AI Gateway feature | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | CI fail (Vercel preview); Dockerfile rewrite | Left for owner review | HALTED(needs_review) |
| #433 | jules[bot] | 06-28 | CI fail; orphaned-history artifact | Recommend close + re-cut clean test branch | HALTED(orphaned_history) |
| #442 | owner | 06-29 | CI fail; orphaned-history artifact, dup of #441 | Recommend decide #442 vs #441, close redundant | HALTED(orphaned_history) |
| #474 | owner | 07-03 | CI fail (Vercel preview); docstrings | Left for owner review | HALTED(needs_review) |
| #494 | owner | 07-03 | draft; implements #487's tests | High-value draft — recommend un-draft | DEFERRED(draft) |
| #495 | Copilot | 07-04 | draft; removes committed API keys, fixes imports | Recommend un-draft + rotate leaked keys | DEFERRED(draft) |
| #508 | dependabot | 07-04 | green (required); rebased onto new main | **Held — `vite` 6→8, two-major dev-dep bump; smoke-test web build** | HALTED(awaiting_review) |
| #510 | dependabot | 07-04 | green (required); rebased onto new main | **Held — `chrome-devtools-mcp` 0.10.2→1.5.0, pre-1.0→1.x major** | HALTED(awaiting_review) |

## Staged commands (owner sign-off required)

```
gh pr merge 508 --squash   # vite 6.4.3 → 8.1.3: TWO major versions. Smoke-test apps/web build first.
gh pr merge 510 --squash   # chrome-devtools-mcp 0.10.2 → 1.5.0: pre-1.0 → 1.x. Verify MCP devtools starts.
gh pr close 433            # orphaned-history artifact; re-cut a clean unit-test branch if wanted.
# decide #442 vs #441 (identical cleanup) and close the redundant one.
# un-draft #494; un-draft #495 AND rotate the API keys it removes from history.
# stale/large — owner review: #327 (rebase to clear conflict), #365, #414, #474.
```

## Systemic note — Vercel preview check

The non-required **Vercel** preview status still fails on the older/stale PRs and passes
on recent ones. It correlates with branch staleness / deploy-config drift, is **not a
required check**, and does not block merge. Flagged so it isn't mistaken for a code defect.

## Is more work needed?

**No — nothing safely automatable unattended remains.** The routine's auto-mergeable
category (CI-only Dependabot *action* pins) is empty: the two open Dependabot PRs are npm
bumps with app blast radius (#508 two-major bundler, #510 pre-1.0→1.x major) needing owner
review. Everything else open is a draft awaiting un-draft, an orphaned-history artifact, or
a stale/large/conflicted PR needing owner review or a rebase outside this session's scope.

The owner cleared the entire run-3 backlog by hand during this window, so no notification
was sent (nothing broken; owner actively at the console). The loop's automatable work has
converged again. Re-run when the owner clears the next gate (un-drafts #494/#495, or
reviews/closes #508/#510 and the stale set).
