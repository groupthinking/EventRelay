# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (#514, 2026-07-06), whose exit condition — *"re-run when
the owner clears a gate"* — has been met: the owner executed run-3's recommendations.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy (unchanged from runs 2–3):** merge only demonstrably-safe,
  auto-approved, **CI-only Dependabot _action_ pins**; hold anything with a documented
  breaking change, deploy/runtime blast radius, or a branch-protection block for owner
  sign-off. `deploy-cloud-run.yml` is `workflow_dispatch`-only, so a merge to `main`
  runs CI but does **not** trigger a production deploy.

## What changed since run 3

The owner cleared run-3's staged commands:

- **#513** (npm minor/patch group + postcss security override) — **MERGED** (`a86c1fe`).
- **#512** (run-2 triage doc) — **MERGED** (2026-07-06T23:34Z, by owner).
- **#509** (npm minor/patch group, superseded by #513) — **CLOSED** (2026-07-06T23:34Z).

**Correction to the run 2 / run 3 records:** **#441** (the "cleanup pass 2" that removed
`mcp-servers/*` and ~365 other unreferenced files) was in fact **MERGED on 2026-06-29** —
weeks before run 3, *not* a change since it. Runs 2–3 (and this doc's first draft)
mischaracterized #441 as an open "twin" of #442 awaiting a redundancy decision. It is not:
its cleanup already landed. Consequently **#442 is not one of a redundant pair to choose
between** — its only residual value is deleting the two now-dead `mcp-servers/` workflow
files (`verify-litert-mcp.yml`, `vision-reasoning.yml`). #442's 384-file / −71.7k diff is
orphaned-history noise from the `main` force-push, not real content (per CLAUDE.md: trust
PR state + staleness, not raw diffs).

New drift observed this run:

- **#510** flipped `none` → **`dirty`** (merge conflict). Dependabot's chrome-devtools-mcp
  major bump now conflicts with `main`, most likely the #513 lockfile landing. Dependabot
  auto-rebases; no action needed from this routine. Still owner-gated regardless (pre-1.0
  → 1.x major that also modifies the install `prepare` script).

No open PR became newly safely-automatable. The two auto-mergeable categories (owner-cleared
production fixes; CI-only Dependabot action pins) are **empty** again this run.

## Oldest-first disposition (current open set — 11 PRs)

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | CI fail (Vercel preview); large (40 files, +5.8k/-1.8k) | `dirty` | Left for owner — needs rebase + review | HALTED(merge_conflict) |
| #365 | owner | 06-21 | CI fail (Vercel preview); AI Gateway feature | — | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | CI fail (Vercel preview); Dockerfile rewrite | — | Left for owner review | HALTED(needs_review) |
| #433 | jules[bot] | 06-28 | CI fail (Vercel canceled); orphaned-history artifact | inflated diff | Recommend close + re-cut clean test branch | HALTED(orphaned_history) |
| #442 | owner | 06-29 | CI fail (Vercel preview); orphaned-history, 384-file inflated diff | `unknown` | Verified on `origin/main`: **both** target workflows (`verify-litert-mcp.yml`, `vision-reasoning.yml`) are **already absent** → #442 has nothing left to deliver. **Recommend close.** | HALTED(recommend_close) |
| #474 | owner | 07-03 | CI fail (Vercel preview); docstrings | — | Left for owner review | HALTED(needs_review) |
| #494 | owner | 07-03 | draft; implements #487's tests | — | High-value draft — recommend un-draft | DEFERRED(draft) |
| #495 | Copilot | 07-04 | draft; removes committed API keys, fixes imports | — | High-value draft — recommend un-draft + rotate leaked keys | DEFERRED(draft) |
| #508 | dependabot | 07-04 | green (required); `unstable` (Vercel non-required) | none | **Held — `vite` 6→8, two-major bundler bump; owner is requested reviewer** | HALTED(awaiting_review) |
| #510 | dependabot | 07-04 | green (required); `unstable` | **`dirty`** | **Held — `chrome-devtools-mcp` pre-1.0→1.x major + install-script change; now conflicted (Dependabot will rebase)** | HALTED(awaiting_review) |
| #511 | owner | 07-04 | draft; ci(e2e) prod-noise cleanup | — | Draft | DEFERRED(draft) |

## Staged commands (owner sign-off required)

**Dependabot bumps — review each breaking note, then:**
```
gh pr merge 508 --squash   # vite 6.4.3 → 8.1.3: TWO major versions. Smoke-test the apps/web
                           # build before merging — bundler majors can break config/plugins.
# #510: chrome-devtools-mcp 0.10.2 → 1.5.0 is pre-1.0 → 1.x AND modifies the install
# `prepare` script; it is also now conflicted. Let Dependabot rebase, verify the MCP
# devtools integration still starts, then:
gh pr merge 510 --squash
```

**Cleanup / drafts:**
```
gh pr close 433            # orphaned-history bot artifact; re-cut a clean unit-test branch if wanted
gh pr close 442            # verified: both workflows it deletes (verify-litert-mcp.yml,
                           # vision-reasoning.yml) are ALREADY absent from origin/main, so the
                           # PR has nothing left to deliver; its 384-file diff is orphan noise
# un-draft #494, #495 (rotate any leaked keys #495 removes), #511 when ready
```

**Stale/large — owner review:** #327 (rebase to clear conflict), #365, #414, #474.

## Systemic note — Vercel preview check

The non-required **Vercel** preview-deployment status keeps failing on the older PRs
(#327, #365, #414, #433, #442, #474) and passing on the recent ones. It correlates with
branch staleness / deploy-config drift, is **not a required check**, and does not block
merge. Flagging only so it isn't mistaken for a per-PR code defect.

## Is more work needed?

**No — not for anything safely automatable unattended.** The owner has actively worked the
queue (run-3's four recommendations all executed). Everything still open is a draft awaiting
un-draft, an orphaned-history artifact, a stale/large/conflicted PR needing owner review or a
rebase, or a major-version Dependabot bump with app/install blast radius — none inside this
routine's conservative auto-merge policy.

The loop's automatable work has converged again. Re-run when the owner clears a gate (reviews
#508/#510, closes #442/#433, un-drafts #494/#495/#511, or rebases/closes the stale set).
