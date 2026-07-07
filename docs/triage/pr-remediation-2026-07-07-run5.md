# PR Remediation Run — 2026-07-07 (run 5)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 4 (same day), whose exit condition — *"re-run when the owner
clears a gate"* — has been met: the owner merged run 4's output and part of its staged
set, and opened a fresh wave (#560–#563).

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy (unchanged from runs 2–4):** merge only demonstrably-safe,
  auto-approved, CI-clean changes with no runtime/deploy blast radius; hold anything
  carrying a merge conflict, a breaking change, orphaned history, or a branch-protection
  block for owner sign-off.

## What changed since run 4

The owner **acted on run 4's recommendations** and pushed the loop forward:

- **run 4's triage docs** (`33cb661`, `c837900`) — **MERGED** to `main`.
- **#552** (docs-audit merge-commit PR) — **MERGED** as `c191fb3` (run 4 had recommended
  close; owner chose to land it — no net-content harm).
- **#557**, **#558** (OTel/Sentry pin regressions in the `dazzling-edison` cluster) —
  **CLOSED** by the owner, exactly as run 4 recommended.
- **New wave opened** (all owner, all off orphaned `claude/dazzling-edison-*` or pre-rewrite
  branches): **#560, #561, #562** (non-draft) and **#563** (draft).

Main HEAD at scan time: `c837900 docs(triage): run 4 …`.

Open set is now **30 PRs**: 10 non-draft, 20 WIP drafts. `#557/#558/#552` are gone from
the open set; `#560–#563` are new.

## Oldest-first disposition — non-draft open set (10)

| PR | Author | Age | Concern | mergeable | Action taken | Terminal state |
|----|--------|-----|---------|-----------|--------------|----------------|
| #327 | owner | 06-19 | dev-deps upgrade (40 files, security/frontend) | `dirty`/orphaned | Left for owner — rebase + review | HALTED(merge_conflict) |
| #365 | kk-agent (fork) | 06-21 | Vercel AI Gateway text+video (#269) | `unknown` | Left for owner review | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | Dockerfile prod rewrite | `unknown` | Superseded by draft pair #539/#540 — owner picks one | HALTED(needs_review) |
| #553 | owner | 07-07 | vite 8.0.16 + vitest bump | `dirty` | Separate concern; rebase + web-build smoke-test | HALTED(merge_conflict) |
| #555 | owner | 07-07 | db schema-extraction change | `dirty`/orphaned | Small once rebased off current main | HALTED(merge_conflict) |
| #556 | owner | 07-07 | revert tailwindcss → v3 | `dirty`/orphaned | **Superseded by owner's own #560** (v4 postcss, correct direction). Recommend close | HALTED(superseded) |
| #559 | owner | 07-07 | pin tailwindcss → v3 | `dirty`/orphaned | **Superseded by #560.** Recommend close | HALTED(superseded) |
| #560 | owner | 07-07 | use `@tailwindcss/postcss` for Tailwind **v4** build | `dirty`/orphaned | Correct direction (main is on v4) but branch conflicts. Re-cut off current main | HALTED(merge_conflict) |
| #561 | owner | 07-07 | mcp: structural request summary + non-string `base_url` guard (#389 Copilot review) | `dirty`/orphaned | Legit small safety fix; CodeRabbit rate-limited, no fresh CI. Re-cut off current main | HALTED(merge_conflict) |
| #562 | owner | 07-07 | make OTEL instrumentation override effective + align Node engine | `dirty`/orphaned | Re-cut off current main | HALTED(merge_conflict) |

### The tailwind sub-cluster resolved itself
Run 4 flagged #556/#559 (v3 reverts) as superseded by `main` (already on v4). The owner has
since opened **#560**, which takes the *correct* v4 direction (`@tailwindcss/postcss`). So
#556 and #559 are now superseded by the owner's **own newer PR**, not just by `main` — the
close signal is unambiguous. #560 itself carries the right intent but sits on an orphaned
branch (`dazzling-edison-5wps75`) that conflicts with `main`; the fix should be re-cut as a
clean commit off current `main` rather than merged from the orphaned branch.

### Orphaned-history signature (per repo hygiene rules)
Every `dazzling-edison-*` and pre-rewrite branch in this set shares a recent merge-base
with `main` (~4 commits behind) but carries **~800 commits of pre-rewrite history** that the
secret-purge force-push removed from `main`. That is why GitHub reports each as
`mergeable_state: dirty` and why three-dot diffs / merge-tree are unreliable here. The
GitHub PR file view still shows the *intended* 2–5 file change, so the underlying fixes are
small and legitimate — but merging the branch as-is would drag orphaned history in. Correct
remedy for each is **re-cut the intended diff off current `main`**, not rebase 800 commits.

## WIP drafts — DEFERRED(draft) (20)

All opened 2026-07-07, mostly paired Copilot + Claude attempts at the same issue (owner
comparing two implementations). The count moved **21 → 20** since run 4: the owner **closed
the SQL-injection-hardening draft pair #547 (Copilot) and #550 (owner)** — both redundant
with the already-merged #548 (exactly the reconciliation run 4 flagged) — and opened one new
draft **#563** (docs: align `CLAUDE.md` anthropic SDK floor with `pyproject.toml`, `0.105.0`).
Net: 21 − 2 + 1 = 20. The rest of the inventory is unchanged from run 4. Un-draft the winner
of each remaining pair; close the loser. No action this run — deferred by definition.

## Auto-mergeable this run

**None.** Every non-draft PR is `dirty` (orphaned-history conflict) or `unknown`/needs-review;
drafts are deferred. There is nothing this routine can safely merge unattended, and it must
not front-run the owner's active Devin/CodeRabbit-assisted iteration by re-cutting their
in-flight PRs on a side branch.

## Staged commands (owner sign-off required)

**Tailwind sub-cluster — superseded by the owner's own #560, close the v3 reverts:**
```
gh pr close 556 559   # v3 reverts; main + #560 are on tailwind v4 (@tailwindcss/postcss)
```

**Re-cut the three real fixes off current `main`** (orphaned branches can't be merged as-is):
```
# #560 -> @tailwindcss/postcss v4 build fix
# #561 -> mcp protocol_bridge: non-string base_url guard + structural request summary
# #562 -> effective OTEL instrumentation override + Node engine alignment
git checkout -B fix/rewave-560-562 origin/main   # cherry-pick the intended diffs, drop orphaned history
```

**Still open from prior runs (owner):**
```
# #553  rebase vite8+vitest onto main, smoke-test apps/web build
# #555  rebase db schema-extraction onto main
# #327  rebase dev-deps upgrade onto main + review (large)
# #365  review fork PR (Vercel AI Gateway #269)
# #414  pick a Dockerfile: this vs draft pair #539/#540, close the losers
# draft pairs: un-draft the winner, close the loser (see run 4 table)
```

## Is more work needed?

**Automatable-by-this-routine: no — converged again at a HALT that requires the owner.**
The loop is healthy and the owner is actively driving it (they merged run 4's output, closed
#557/#558 as recommended, and re-cut the tailwind fix in the correct v4 direction as #560).
What remains is all owner-gated: decisions between the owner's own competing PRs, rebases of
conflicted branches, and re-cutting three orphaned-branch fixes (#560/#561/#562) off current
`main`. None of that is safely automatable without front-running the owner's in-flight work
or merging orphaned history into protected `main`.

**Re-run when the owner clears a gate** — closes #556/#559, re-cuts #560–#562 off `main`, or
picks winners in the draft pairs — at which point the survivors become CI-checkable and, if
green, mergeable.
