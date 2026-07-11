# PR Remediation & Publish — Run 12 (2026-07-11)

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge). CodeRabbit handle: `@coderabbitai`.
Run mode: **unattended scheduled routine** (no human watching during the run).

## Headline: the backlog is stuck and growing, not converging

| Run | Date | Open PRs |
|-----|------|----------|
| Run 10 | 07-07 | 26 |
| **Run 12** | **07-11** | **53** |

The open-PR count has **doubled in four days.** The remediation loop is producing
fix/triage PRs **faster than they merge** — because, per the verified gate below,
**nothing is merging at all.** Continuing to loop only enlarges the pile. The correct
terminal outcome of this run is therefore **not** "merge everything" — it is to record
the blocker and hand the backlog to the owner for a batch decision.

## The one gate that blocks the entire backlog (verified)

`main` is a **protected branch that requires an approving human review**, and **no open
PR carries one.** This was confirmed on the freshest, cleanest PR in the set:

- **#658** (`fix(web): fail open for cheap AI status GETs`, created 07-11 02:27):
  authored CI green/running (`lint-*`, `build`, `bandit`, `gitleaks`, `validate` all
  ✅; `test`/`trivy`/coverage still running), Vercel deploy ✅ — yet
  `mergeable_state: "blocked"`. Its only reviews are **bot** reviews (CodeRabbit
  *dismissed*, Devin *commented*, Copilot *commented*). **Zero human `APPROVED`
  reviews.** `blocked` = branch protection unsatisfied.

- No open PR carries an `automerge` label (`auto_merge_policy: label:automerge` →
  **no PR qualifies for auto-merge**).

**Consequence:** the PUBLISH GATE is HUMAN for every PR. An unattended agent cannot
clear it without either a human approval or bypassing branch protection on `main` — the
latter is explicitly out of bounds (irreversible, protected branch, and many of these
PRs mutually conflict — see clusters). **No PR was merged this run, by design.**

## Older PRs are also behind `main` (verified sample)

`origin/main` HEAD = `a3d0d2a`. Sampled older PRs report `mergeable_state: "unknown"`
with **stale bases** (branch is behind current `main`):

- **#596** (07-07, `execute_single`): base `a20db9a`, `unknown`.
- **#606** (07-08, remove fabricated MCP bridge): base `b0e33e8`, `unknown`.
- **#632** (07-09, Tailwind v4 postcss): base `e2916b9`, `unknown`.

Combined with the repo-hygiene note (history was force-pushed; older branches are
orphaned), these need a **rebase onto current `main`** before their mergeability can
even be computed — another reason merge cannot be automated here.

## Redundant / mutually-conflicting clusters (recommend batch close)

The build-fix PRs from 07-09 are **contradictory** — they cannot all be right, and
several are exact reversals of each other. A human must pick **one winner per cluster**
and close the rest.

- **Tailwind v3 ↔ v4 flip-flop (8 PRs):** `#613` revert→v3, `#616` pin→v3, `#618`
  migrate→v4, `#623` realign→v3, `#627` complete→v4, `#629` revert→v3, `#630`
  migrate→v4, `#632` use `@tailwindcss/postcss`→v4. → keep the one that matches the
  desired Tailwind major on `main` (newest is `#632`); **close the other 7.**
- **OTel / Sentry pin churn (5 PRs):** `#614`, `#615`, `#617`, `#621`, `#626`
  (+ `#570` Sentry-optional). Overlapping dependency-pin edits to the same files. →
  consolidate to one; **close the rest.**
- **Merge-noise (2 PRs):** `#619`, `#628` — both bare `Merge origin/main into …`
  branches with no distinct change. → **close.**
- **Exact duplicates (2 pairs):** `#659` is a draft duplicate of `#658` (same title);
  `#650` (Copilot) duplicates `#649` (Jules) — Gemini 4xx retry fix. → keep one of each,
  **close the twin.**

## Drafts → DEFERRED per SCOPE GATE (12 PRs)

`#634`, `#635`, `#636`, `#637`, `#645` (run-11 triage doc), `#648`, `#649`, `#650`,
`#651`, `#653`, `#657`, `#659`. Drafts and `hold`-equivalents are skipped by the
runbook's SCOPE GATE.

> ⚠️ `#636` (`remove hardcoded Looker embed secrets`) is a **security** draft. If the
> secrets are live it should be prioritised for un-drafting + review, not left in the
> draft pile.

## Disposition

| Bucket | PRs | Terminal state |
|--------|-----|----------------|
| Freshest actionable, CI green, blocked on review | #658 | **HALTED(awaiting_merge_approval)** — needs 1 human `APPROVE` on `main` |
| Non-draft, behind `main` / unknown mergeability | #596, #606, #632, and other 07-07→07-09 non-drafts | **HALTED(awaiting_rebase+approval)** |
| Tailwind cluster (7 of 8) | #613,#616,#618,#623,#627,#629,#630 | **HALTED(redundant→recommend close)** |
| OTel/Sentry cluster (4 of 5) | #614,#615,#617,#621 | **HALTED(redundant→recommend close)** |
| Merge-noise | #619, #628 | **HALTED(no-op→recommend close)** |
| Duplicates | #659 (=#658), #650 (=#649) | **DEFERRED(duplicate)** |
| Drafts | 12 listed above | **DEFERRED(draft)** |

## What the owner needs to do to unblock (staged, exact next steps)

1. **Pick winners** for the Tailwind and OTel/Sentry clusters; close the losers
   (archive-tag branches first per repo hygiene). This alone removes ~11 PRs.
2. **Approve or close** the genuine fixes that are green-and-blocked, starting with
   **#658** (`gh pr review 658 --approve` then merge, or dismiss).
3. **Decide the automation policy:** either (a) apply an `automerge` label to
   agent-authored PRs whose CI is green so future runs can complete the PUBLISH GATE,
   or (b) accept that these runs are review-triage only and **stop the loop from opening
   further fix PRs** until the backlog drains — the loop is currently net-negative.

## Runbook terminal note

Per the Definition of Done, this run drives every open PR to a terminal state
(`HALTED` with the blocker recorded, or `DEFERRED`). **`MERGED` is not reachable by an
unattended agent** given branch protection + zero human approvals + mutually-conflicting
diffs. No merges performed. The autonomous loop has reached its own terminal state:
**no further work can be completed without a human decision.**
