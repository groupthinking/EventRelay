# PR Remediation Run — 2026-07-06 (run 3)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 2 (#512, 2026-07-04), whose stated exit condition —
*"re-run when the owner clears a gate"* — has now been met.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy applied (unchanged from run 2):** merge only demonstrably-safe,
  auto-approved, **CI-only Dependabot _action_ pins**; hold anything carrying a
  documented breaking change, deploy/runtime blast radius, or a branch-protection block
  for owner sign-off. `deploy-cloud-run.yml` is `workflow_dispatch`-only, so a merge to
  `main` runs CI but does **not** trigger a production deploy.

## What changed since run 2

The owner cleared **the entire run-2 backlog**. `origin/main` now contains:

- **#478** — GCP secret wiring + X-API-Key auth (was HALTED awaiting admin-merge) — **MERGED**
- **#488** — Upstash Redis credential resolver (was HALTED awaiting admin-merge) — **MERGED**
- **#502** `upload-artifact` 4→7, **#504** `github-script` 7→9, **#505** `docker/build-push` 6→7,
  **#506** `opencv-python-headless` 4→5, **#507** `@opentelemetry/instrumentation` — all
  five held Dependabot bumps — **MERGED**

No open PR from run 2's table remains actionable by this routine; the only carry-overs
are the same stale/large/fork/orphaned PRs that have always required owner review.

## Oldest-first disposition (current open set)

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
| #509 | dependabot | 07-04 | green (required); `unstable` | none | **Held — npm minor/patch group (21 pkgs); superseded by owner draft #513** | HALTED(superseded_by_513) |
| #510 | dependabot | 07-04 | green (required); `unstable` | none | **Held — `chrome-devtools-mcp` 0.10.2→1.5.0, pre-1.0→1.x major** | HALTED(awaiting_review) |
| #511 | owner | 07-04 | draft; ci(e2e) prod-noise cleanup | — | Draft | DEFERRED(draft) |
| #512 | owner | 07-04 | draft; run-2 triage doc | — | Superseded by this doc — recommend close | DEFERRED(draft) |
| #513 | owner | 07-04 | draft; npm minor/patch group + postcss security override | — | Owner's consolidation; supersedes #509 | DEFERRED(draft) |

## Staged commands (owner sign-off required)

**New Dependabot bumps — review each breaking note, then:**
```
gh pr merge 508 --squash   # vite 6.4.3 → 8.1.3: TWO major versions. Smoke-test the web build
                           # (apps/web) before merging — bundler majors can break config/plugins.
gh pr merge 510 --squash   # chrome-devtools-mcp 0.10.2 → 1.5.0: pre-1.0 → 1.x major. Verify the
                           # MCP devtools integration still starts.
# #509 (npm minor/patch group) — do NOT merge; it is superseded by your own draft #513,
# which folds the same group bump together with a postcss security override.
# Land #513 instead, then close #509:
gh pr merge 513 --squash && gh pr close 509
```

**Cleanup / drafts:**
```
gh pr close 512            # run-2 triage doc, superseded by run-3 (this doc)
gh pr close 433            # orphaned-history artifact; re-cut a clean unit-test branch if wanted
# decide #442 vs #441 (identical cleanup) and close the redundant one
# un-draft #494 and #495 when ready (rotate any leaked keys #495 removes)
```

**Stale/large — owner review:** #327 (rebase to clear conflict), #365, #414, #474.

## Systemic note — Vercel preview check

The non-required **Vercel** preview-deployment status fails on the older PRs
(#327, #365, #414, #433, #474) and passes on the recent ones (#442, #508, #509, #510).
It correlates with branch staleness / deploy-config drift, is **not a required check**,
and does not block merge. Flagging only so it isn't mistaken for a per-PR code defect.

## Is more work needed?

**No — not for anything safely automatable unattended.** The routine's two auto-mergeable
categories from run 2 (owner-cleared production fixes; CI-only Dependabot action pins) are
empty this run: the three new Dependabot PRs are all npm bumps with app blast radius
(#508 two-major bundler, #510 pre-1.0→1.x major) or are superseded by an owner draft
(#509 → #513). Everything else open is a draft awaiting un-draft, an orphaned-history
artifact, or a stale/large/conflicted PR needing owner review or a rebase outside this
session's scope.

The loop's automatable work has converged again. Re-run when the owner clears a gate
(lands #513, reviews #508/#510, or rebases/closes the stale set).
