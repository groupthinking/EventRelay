# PR Remediation Run — 2026-07-06 (run 4)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 3 (#514, 2026-07-06), whose stated exit condition —
*"re-run when the owner clears a gate (lands #513, reviews #508/#510, or rebases/closes
the stale set)"* — has now been met.

- **Surface:** GitHub MCP (PR read + comment + close/merge), authed as repo owner.
- **Auto-merge policy applied (unchanged):** merge only demonstrably-safe, auto-approved,
  CI-only changes; hold anything carrying a documented breaking change, deploy/runtime
  blast radius, or a branch-protection block for owner sign-off. Do **not** auto-merge to
  protected `main`. Redundant PRs are closed (reversible, non-merge cleanup).

## What changed since run 3

The owner cleared **every gate run 3 named**. `origin/main` now contains:

- **#513** — npm minor/patch group bump (21 pkgs) + postcss security override — **MERGED**.
  This landed `vite@^8.1.3` and the postcss `8.5.16` resolution into `apps/web`.
- **#511** — `ci(e2e)` prod-noise cleanup (was a run-3 draft) — **MERGED**.
- **#512** — run-2 triage doc (run 3 recommended closing) — **MERGED** by owner.
- **#514** — run-3 triage doc — **MERGED**.
- **#509** — npm minor/patch group, superseded by #513 — **CLOSED** (as run 3 recommended).

## Action taken this run

- **#508 (`vite` 6.4.3 → 8.1.3) — CLOSED as superseded.** Run 3 held this for a
  "two-major bundler" review, but #513's group bump already resolved `apps/web` to
  `vite@^8.1.3` in `main`. Verified against `origin/main:apps/web/package.json`
  (`"vite": "^8.1.3"`), so this standalone bump is now a no-op with nothing left to
  merge. Closed with an explanatory comment; Dependabot will re-open if a newer vite ships.

No PR qualified for auto-merge this run. Everything else open is a draft (DEFERRED) or a
stale/large/owner-gated change (HALTED) — none carry an `automerge` label and `main` is
protected, so the publish gate stays with the owner.

## Oldest-first disposition (current open set — 9 PRs)

| PR | Author | Age | Review/CI | Action taken | Terminal state |
|----|--------|-----|-----------|--------------|----------------|
| #327 | owner | 06-19 | CodeRabbit ✅; Vercel status is a **stale** 06-15 preview fail; large (40 files) | Left for owner — needs rebase onto post-#513 `main` + review | HALTED(awaiting_review) |
| #365 | owner | 06-21 | AI Gateway feature; owner-gated | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | Dockerfile rewrite (resolves #406); owner-gated | Left for owner review | HALTED(needs_review) |
| #433 | jules[bot] | 06-28 | Unit tests; orphaned-history artifact (inflated diff from `main` rewrite) | Recommend close + re-cut a clean test branch | HALTED(orphaned_history) |
| #442 | owner | 06-29 | Vercel/CodeRabbit ✅ (all green); removes dead mcp-servers workflows | Cleanest merge candidate — staged for owner squash | HALTED(awaiting_merge_approval) |
| #474 | owner | 07-03 | Docstrings + refactor (23 files); owner-gated | Left for owner review | HALTED(needs_review) |
| #494 | owner | 07-03 | draft; implements #487's generated tests | Recommend un-draft when ready | DEFERRED(draft) |
| #495 | Copilot | 07-04 | draft; repairs imports, removes committed API keys, aligns SDK types | Recommend un-draft **+ rotate any leaked keys** | DEFERRED(draft) |
| #510 | dependabot | 07-04 | `chrome-devtools-mcp` 0.10.2 → 1.5.0 (pre-1.0 → 1.x major) | **Held — modifies an npm `prepare` install-script; supply-chain review required** | HALTED(awaiting_review) |

> `mergeable_state` was returned as `unknown` by the API for the carry-over set this run —
> GitHub is recomputing mergeability after #513/#511 moved `main`. Conflict states are
> therefore not freshly asserted here; #327 in particular will need a rebase onto the new
> `main` before it can merge (it was `dirty` in run 3).

## Staged commands (owner sign-off required)

**Cleanest merge first:**
```
gh pr merge 442 --squash   # removes dead mcp-servers workflows; all checks green
```

**Dependabot — review the breaking/security note, then decide:**
```
gh pr merge 510 --squash   # chrome-devtools-mcp 0.10.2 → 1.5.0. NOTE: Dependabot flags an
                           # install-time `prepare` script change. Review package contents
                           # (supply-chain) and verify the MCP devtools integration starts
                           # before merging. A rebase may be needed (post-#513 lockfile).
```

**Cleanup / drafts:**
```
gh pr close 433            # orphaned-history artifact; re-cut a clean unit-test branch if wanted
# decide #442 vs any remaining duplicate cleanup PR and close the redundant one
# un-draft #494 and #495 when ready (rotate any leaked keys #495 removes)
```

**Stale/large — owner review (rebase onto post-#513 `main` first):** #327, #365, #414, #474.

## Systemic note — Vercel preview check (carried from run 3)

The non-required **Vercel** preview-deployment status still shows failures on the older
PRs and correlates with branch staleness / deploy-config drift. It is **not a required
check** and does not block merge — flagged only so a stale red X isn't mistaken for a
per-PR code defect. On #327 the failing Vercel status dates to 2026-06-15.

## Is more work needed?

**No — not for anything safely automatable unattended.** The only auto-safe action this
run (closing the now-redundant `vite` bump #508) is done. Every remaining open PR is
either a draft awaiting the owner's un-draft, an orphaned-history artifact, or a
stale/large/owner-gated change whose merge is a human sign-off on protected `main` — which
this routine must not bypass. #442 is green and staged as the cleanest single merge; #510
carries a supply-chain (install-script) note the owner should review deliberately.

The loop's automatable work has converged. Re-run when the owner clears a gate (merges
#442/#510, un-drafts #494/#495, or rebases/closes the stale set) — a fresh merge into
`main` typically renders one or more of the remaining Dependabot/stale PRs redundant or
conflicted, which is the next cleanup this routine can take unattended.
