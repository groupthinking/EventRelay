# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (#514, 2026-07-06), whose exit condition —
*"re-run when the owner clears a gate (lands #513, reviews #508/#510, or rebases/closes
the stale set)"* — has now been met: the owner **landed #513 and closed #509/#512**.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy applied (unchanged):** merge only demonstrably-safe, auto-approved,
  **CI-only Dependabot _action_ pins**; hold anything carrying a documented breaking
  change, deploy/runtime blast radius, or a branch-protection block for owner sign-off.
  `deploy-cloud-run.yml` is `workflow_dispatch`-only, so a merge to `main` runs CI but
  does **not** trigger a production deploy.

## What changed since run 3

The owner cleared the run-3 gate set:

- **#513** — npm minor/patch group bump + postcss security override (`GHSA-qx2v-qp2m-jg93`) — **MERGED**
- **#509** — the superseded npm group bump — **CLOSED** (as planned)
- **#512** — run-2 triage doc — **MERGED**

Side effect of #513 landing: it rewrote `apps/web/package-lock.json` / root
`package-lock.json`, which pushed **#510 into a merge conflict** (`mergeable_state: dirty`).

## Action taken this run

- **#510 — CONFLICT GATE cleared natively.** Posted `@dependabot rebase` so Dependabot
  regenerates the lockfile against current `main`. This un-rots the branch and keeps the
  bump reviewable; it does **not** merge it (still owner-gated — see below).

No PR qualified for auto-merge: the two live Dependabot PRs are both breaking-major npm
bumps with app blast radius and the owner is the requested reviewer on each.

## Oldest-first disposition (current open set)

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | large (40 files, +5.8k/-1.8k); non-req Vercel preview red | likely `dirty` (needs rebase) | Left for owner — rebase + review | HALTED(needs_review) |
| #365 | owner | 06-21 | AI Gateway feature; non-req Vercel preview red | — | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | Dockerfile rewrite; non-req Vercel preview red | — | Left for owner review | HALTED(needs_review) |
| #433 | jules[bot] | 06-28 | orphaned-history unit-test artifact; inflated diff | inflated diff from `main` rewrite | Recommend close + re-cut clean test branch | HALTED(orphaned_history) |
| #442 | owner | 06-29 | orphaned-history artifact, dup of #441 | inflated diff | Recommend decide #442 vs #441, close redundant | HALTED(orphaned_history) |
| #474 | owner | 07-03 | docstrings; non-req Vercel preview red | — | Left for owner review | HALTED(needs_review) |
| #494 | owner | 07-03 | draft; implements #487's tests | — | High-value draft — recommend un-draft | DEFERRED(draft) |
| #495 | Copilot | 07-04 | draft; removes committed API keys, fixes imports | — | High-value draft — un-draft + rotate leaked keys | DEFERRED(draft) |
| #508 | dependabot | 07-04 | **required checks green** (only non-req E2E cancelled → `unstable`) | none | **Held — `vite` 6→8, two-major bundler bump; owner is requested reviewer** | HALTED(awaiting_review) |
| #510 | dependabot | 07-04 | required checks green pre-conflict; pre-1.0→1.x major + install-script warning | was `dirty` → **rebase triggered** | Posted `@dependabot rebase`; still owner-gated | HALTED(awaiting_review) |
| #511 | owner | 07-04 | draft; ci(e2e) prod-noise cleanup | — | Draft | DEFERRED(draft) |

## Staged commands (owner sign-off required)

**Dependabot bumps — review each breaking note, then:**
```
gh pr merge 508 --squash   # vite 6.4.3 → 8.1.3: TWO major versions. Required CI is green;
                           # still smoke-test the apps/web build — bundler majors can break
                           # vite config / plugins that CI's build step may not exercise fully.
gh pr merge 510 --squash   # chrome-devtools-mcp 0.10.2 → 1.5.0: pre-1.0 → 1.x major. Release
                           # notes flag an install-time `prepare` script change — review package
                           # contents. Wait for the @dependabot rebase to land clean first.
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
(#327, #365, #414, #474) and passes on the recent Dependabot PRs. It correlates with
branch staleness / deploy-config drift, is **not a required check**, and does not block
merge. Flagging only so it isn't mistaken for a per-PR code defect.

## Is more work needed?

**No — not for anything safely automatable unattended.** This run:
- confirmed the owner cleared the entire run-3 gate set (#513 merged, #509/#512 closed);
- took the one concrete safe action available — cleared #510's post-#513 merge conflict
  via `@dependabot rebase`;
- found **zero** PRs in the two auto-mergeable categories (owner-cleared production fixes;
  CI-only Dependabot action pins). Both live Dependabot PRs (#508 two-major bundler, #510
  pre-1.0→1.x major with an install-script change) are breaking bumps the owner explicitly
  requested to review.

Everything else open is a draft awaiting un-draft (#494/#495/#511), an orphaned-history
artifact (#433/#442), or a stale/large PR needing owner review or a rebase outside this
session's scope.

The loop's automatable work has converged again. Re-run when the owner clears a gate
(reviews #508/#510, un-drafts #494/#495/#511, or rebases/closes the stale set). No further
unattended action remains.
