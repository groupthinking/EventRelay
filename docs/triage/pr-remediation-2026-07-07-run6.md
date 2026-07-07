# PR Remediation Run — 2026-07-07 (run 6)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 5 (same day), whose exit condition — *"re-run when the owner
clears a gate"* — has been met: the owner cleared the **entire** run-5 non-draft set and a
fresh wave has arrived.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy (unchanged from runs 2–5):** merge only demonstrably-safe,
  auto-approved, CI-clean changes with no runtime/deploy blast radius **and** carrying the
  `automerge` label; hold anything with a merge conflict, a breaking change, orphaned
  history, or a branch-protection block for owner sign-off.

## What changed since run 5

The owner **cleared every run-5 gate** and drove the loop forward:

- **Run 5's entire non-draft set is gone from the open set** — `#327, #365, #414, #553,
  #555, #556, #559, #560, #561, #562` are all closed or merged. The tailwind v3 reverts
  (#556/#559) and the orphaned-branch re-cuts (#560–#562) were resolved exactly as run 5
  recommended.
- **Run-5 triage doc landed on `main`** (`docs/triage/pr-remediation-2026-07-07-run5.md`
  is present at `origin/main`), via a parallel run merged ahead of #566.
- **#569** merged to `main` — `main` HEAD is now `4bd3f7e` (video route: abort-on-unmount,
  timeout headroom, a11y, base64-inline gateway video URL for CSP).
- **New wave opened:** non-draft `#529` (Copilot, Vercel AI Gateway) plus the run-5 doc/fix
  PRs `#566`/`#568`, and a large batch of paired Copilot+Claude WIP drafts (#530–#571).

Main HEAD at scan time: `4bd3f7e Merge pull request #569`.

Open set is now **22 PRs**: 3 non-draft, 19 WIP drafts.

## Oldest-first disposition — non-draft open set (3)

| PR | Author | Age | Concern | mergeable | CI | Action taken | Terminal state |
|----|--------|-----|---------|-----------|----|--------------|----------------|
| #529 | Copilot | 07-07 | Vercel AI Gateway + preview E2E + agent tooling (26 files, +1606/-1343) | `dirty` | green (last sha) | Left for owner — rebase onto `main` + review large diff | HALTED(merge_conflict) |
| #566 | owner | 07-07 | run-5 triage doc (`+117`, 1 file) | `dirty` | — | **Redundant** — the run-5 doc is already on `main` from a parallel run. Recommend **close** | HALTED(superseded) |
| #568 | owner | 07-07 | root `engines.node` `>=20.0.0`→`>=20.6.0` + lockfile sync (2 files, +2/-2) | `blocked` | **all green** (CodeRabbit skipped, Vercel deploy ✓) | Rebased onto current `main`; distills the one correct change from #562. **Awaiting owner merge approval** (branch protection) | HALTED(awaiting_merge_approval) |

### #568 is the one merge-ready change — and it is owner-gated, not routine-gated
`#568` is a metadata-only correctness fix: root `engines.node` declared `>=20.0.0`, but the
repo's own transitive deps (`@opentelemetry/core@2.8` needs `^18.19.0 || >=20.6.0`,
`@tailwindcss/oxide@4.3.1` needs `>=20`) require a higher floor, so a user on node 20.0–20.5
passes the declared engine check yet fails install/build. It is rebased onto current `main`,
all three status checks are green, and it touches no runtime code. It is `mergeable_state:
blocked` **only** because protected `main` requires a review approval — not because of any
conflict or failing check. Per the Publish Gate (§8) this routine must **not** auto-merge to
a protected branch without the `automerge` label; correct terminal state is
`HALTED(awaiting_merge_approval)` with the merge command staged below.

### #566 supersedes itself
The sole content of #566 (the run-5 triage doc) already exists at `origin/main`. Merging
#566 would be a no-op at best and drag its `dirty` orphaned-history base in at worst. The
close signal is unambiguous.

## WIP drafts — DEFERRED(draft) (19)

`#530, #531, #532, #534, #535, #536, #539, #540, #541, #542, #543, #544, #545, #546, #549,
#551, #567, #570, #571`. All opened 2026-07-07, mostly paired Copilot + Claude attempts at
the same issue (owner comparing two implementations: Dockerfile #539/#540, real-AI-response
#543/#544, GTM skills #545/#546, etc.). Deferred by definition — un-draft the winner of each
pair and close the loser; no action this run.

## Auto-mergeable this run

**None.** No open PR carries the `automerge` label. #568 is green but `blocked` by branch
protection (owner approval required); #529/#566 are `dirty`; drafts are deferred. There is
nothing this routine can safely merge unattended into protected `main`.

## Staged commands (owner sign-off required)

**Merge the one green, rebased, safe fix:**
```
gh pr merge 568 --squash   # engines.node floor >=20.6.0; all checks green, blocked only on approval
```

**Close the redundant run-5 doc PR (its content is already on `main`):**
```
gh pr close 566   # run-5 triage doc already present at origin/main from a parallel run
```

**Rebase the large Copilot PR before reviewing:**
```
# #529  rebase Vercel AI Gateway branch onto main (currently dirty), then review 26-file diff
```

**Draft pairs:** un-draft the winner of each Copilot/Claude pair, close the loser (see table).

## Is more work needed?

**Automatable-by-this-routine: no — converged again at an owner-gated HALT.** The loop is
healthy and the owner is actively driving it (they cleared the entire run-5 set, merged #569,
and landed the run-5 doc via a parallel run). What remains is all owner-gated: a merge
approval on the one green PR (#568), a redundant-PR close (#566), a rebase-then-review of the
large #529, and winner-selection across the draft pairs. None of that is safely automatable
without front-running the owner's in-flight work or merging into protected `main` without
sign-off.

**Re-run when the owner clears a gate** — approves/merges #568, closes #566, rebases #529, or
picks winners in the draft pairs — at which point the survivors become CI-checkable and, if
green and labeled `automerge`, mergeable.
