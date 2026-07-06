# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (#514, 2026-07-06), whose exit condition —
*"re-run when the owner clears a gate (lands #513, reviews #508/#510, or rebases/closes
the stale set)"* — was met, and then some: during this run the owner cleared **every open
Dependabot PR**.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy applied (unchanged):** merge only demonstrably-safe, auto-approved,
  **CI-only Dependabot _action_ pins**; hold anything carrying a documented breaking
  change, deploy/runtime blast radius, a branch-protection block, or a merge conflict for
  owner sign-off.

> **Live-state note (updated after CodeRabbit review of this doc):** the owner acted on the
> two staged Dependabot PRs *while this run was in flight* (between the 23:35Z scan and the
> 23:38Z commit). The table and commands below reflect the **live** state; the "current
> open set" no longer contains any Dependabot PR.

## What changed since run 3

The owner cleared the run-3 gate **and** the newly-staged Dependabot set:

- **#513** npm minor/patch group + postcss security override — **MERGED** (supersedes #509)
- **#509** superseded npm group bump — **CLOSED**
- **#511** ci(e2e) prod-noise cleanup — **MERGED**
- **#512** run-2 triage doc — **CLOSED/MERGED**
- **#508** `vite` 6.4.3 → 8.1.3 (two-major bundler bump) — **CLOSED unmerged** at 23:37Z
  (owner declined the major)
- **#510** `chrome-devtools-mcp` 0.10.2 → 1.5.0 — **MERGED** at 23:37Z (owner resolved the
  conflict + accepted the install-script/`prepare` change)

**No new PRs were opened.** Both auto-mergeable categories this routine watches
(owner-cleared production fixes; CI-only Dependabot action pins) are **empty** — the owner
handled the two npm-major PRs directly, exactly as the runbook's PUBLISH GATE intends
(human sign-off on the irreversible step).

## Oldest-first disposition (current open set)

Excludes this triage-doc PR (#521) itself.

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

**Resolved by owner during this run** (no longer open): #508 (closed unmerged), #510 (merged).

## Staged commands (owner sign-off required)

```bash
# Dependabot majors — RESOLVED this run, no action needed:
#   #508 vite 6→8  → closed unmerged (major declined)
#   #510 chrome-devtools-mcp 0.10.2→1.5.0 → merged

# Stale / orphaned-history — owner review or close:
gh pr close 433                 # orphaned-history artifact; re-cut a clean unit-test branch if wanted
# decide #442 vs #441 (identical cleanup) and close the redundant one
# rebase #327 to clear its conflict; review #365, #414, #474

# Drafts — un-draft when ready:
#   #494 (implements #487's tests), #495 (rotate any leaked keys it removes)
```

## Systemic note — Vercel preview check (unchanged from run 3)

The non-required **Vercel** preview-deployment status fails on the older PRs and passes on
the recent ones. It correlates with branch staleness / deploy-config drift, is **not a
required check**, and does not block merge. Flagging only so it isn't mistaken for a
per-PR code defect.

## Is more work needed?

**No — nothing safely automatable unattended.** After this run's activity, the entire open
Dependabot set is resolved (owner closed #508, merged #510) and both of the routine's
auto-mergeable categories are empty. Every remaining open PR is a draft (#494, #495), an
orphaned-history artifact (#433, #442), or a stale/large/conflicted PR requiring owner
review or a rebase outside this session's safe scope (#327, #365, #414, #474).

The loop's automatable work has converged. **Stopping the loop.** Re-run when the owner
clears the next gate (un-drafts #494/#495, rebases #327, or reviews/closes the stale set).
