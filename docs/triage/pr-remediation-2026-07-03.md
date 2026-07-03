# PR Remediation & Publish — run 2026-07-03

Oldest-first entry scan and terminal-state disposition for all **14 open PRs**, run
under the PR Remediation & Publish Runbook. This is a triage artifact, not a code change.

**Supersedes [#461](https://github.com/groupthinking/EventRelay/pull/461)** (the 2026-07-02
run), which is now stale — see "Corrections to the 2026-07-02 report" below. Recommend
closing #461 in favour of this file.

## Headline

- **The video-canvas dashboard work merged.** #459 (superset of #458, carrying all six
  Copilot review fixes) was **merged to `main` at 2026-07-03T01:28 UTC** by the maintainer;
  #458 was closed as superseded. `main` is now at `24120fc`. CI on the merged tree was fully
  green (build, test, lint, E2E 17/17 against the live deployment, CodeQL, Trivy). The publish
  gate was resolved correctly — by a human.
- **No PRs were merged by this run.** Every remaining open PR is owner-gated (draft, real
  merge conflict on a branch outside this session's push scope, a corrupted branch, or the
  protected-`main` publish gate). Nothing remained that could be driven to `MERGED`
  autonomously and safely.

## Corrections to the 2026-07-02 report (#461)

| #461 claim | Status on 2026-07-03 |
|---|---|
| "CodeRabbit credits exhausted — every PR carries a red *Prepaid credits exhausted* status" | **Not observed.** CodeRabbit is on the **Pro** plan and functional. On #459 it posted *"Review skipped — auto reviews are limited based on label configuration"*, and no red CodeRabbit check appears in the 27 checks on #458/#459. The review loop is label-gated, not credit-blocked. Trigger a single review with `@coderabbitai review` when needed. |
| #458 / #459 listed as `HALTED` / `DEFERRED(draft)` | **#459 MERGED, #458 closed** (2026-07-03T01:28 UTC). |

## Terminal states (this run)

- **0** `MERGED` (by this run) — the one merge this cycle, #459, was completed by the maintainer.
- **7** `DEFERRED(draft)` — #412, #415, #430, #434, #439, #442, #456
- **7** `HALTED`:
  - `merge_conflict` (needs a rebase pushed to the PR's own branch — outside this session's
    push scope): #327, #328, #414, #436, and #365 (**fork** `kk-agent/EventRelay` — rebase
    must come from the fork owner).
  - `corrupted_branch` — #433 (1547 files / −142k lines vs. base; orphaned by the `main`
    force-push). **Recommend close.**
  - `awaiting_merge_approval` — #461 (docs-only; this file supersedes it — **recommend close**).

## Matrix (oldest first)

| PR | Author | Type | State | Terminal | Staged next command |
|----|--------|------|-------|----------|---------------------|
| #327 | groupthinking | security dev-deps | conflict | HALTED(merge_conflict) | `git checkout chore/security/upgrade-dev-deps && git rebase origin/main` → resolve → `git push --force-with-lease` |
| #328 | groupthinking | security vitest/vite | conflict | HALTED(merge_conflict) | `git checkout chore/security/upgrade-vitest-vite && git rebase origin/main` → resolve → `git push --force-with-lease` |
| #365 | groupthinking (fork kk-agent) | Vercel AI Gateway | conflict | HALTED(merge_conflict) | fork owner: rebase `feat/vercel-ai-gateway-issue-269` onto `groupthinking/main` |
| #412 | groupthinking | react19 build fix | **draft** | DEFERRED(draft) | mark ready when validated |
| #414 | jules[bot] | Dockerfile rewrite | conflict | HALTED(merge_conflict) | `git checkout jules-9638972698930112439-d2c4ab7c && git rebase origin/main` → resolve → push |
| #415 | groupthinking | triage watermark | **draft** | DEFERRED(draft) | mark ready when validated |
| #430 | Copilot | react19 + pagination guard | **draft** | DEFERRED(draft) | mark ready when validated |
| #433 | jules[bot] | DB optimizer tests | conflict, 1547 files | HALTED(corrupted_branch) | `gh pr close 433 --comment "orphaned by main force-push; re-open a clean branch"` |
| #434 | groupthinking | anthropic-wif CI fix | **draft** | DEFERRED(draft) | mark ready when validated |
| #436 | Claude | Prisma schema extraction | conflict | HALTED(merge_conflict) | `git checkout claude/database-schema-extraction && git rebase origin/main` → resolve → push |
| #439 | Claude | untrack build artifacts | **draft** | DEFERRED(draft) | mark ready when validated |
| #442 | groupthinking | remove dead mcp workflows | **draft** | DEFERRED(draft) | supersedes #441; mark ready or cherry-pick |
| #456 | groupthinking | CORS wildcard hardening | **draft** | DEFERRED(draft) | supersedes #454; mark ready or cherry-pick |
| #461 | groupthinking | triage doc 2026-07-02 | blocked | HALTED(awaiting_merge_approval) | superseded by this file — `gh pr close 461` |

## Owner-gated blockers (unchanged structurally, one resolved)

1. **~~CodeRabbit credits~~ — RESOLVED/stale.** CodeRabbit (Pro) is functional; reviews are
   label-gated, not credit-blocked.
2. **No `automerge` labels on protected `main`.** `auto_merge_policy: label:automerge`, so the
   publish gate halts every green PR on human sign-off. To let the runbook merge a green PR
   unattended, add the `automerge` label to it.
3. **`main` force-push orphaned older branches** (documented in `CLAUDE.md`). 5 of 7 non-draft
   PRs carry real conflicts and need rebases pushed to their own branches — outside this
   session's push scope (this session may only push to its designated branch).

## Answer to the loop's terminal question

*Is more work needed that this session can complete autonomously and safely?* **No.** The
active deliverable (video-canvas dashboard, #459) is merged and aligned with intent. Every
remaining PR requires the maintainer: a rebase authorized on its own branch, an `automerge`
label / merge sign-off on protected `main`, or a close decision (#433, #461). The loop
terminates here rather than re-polling owner-gated state.

---

## Addendum — later run 2026-07-03 (`main` @ `03f5aec`)

Re-ran the entry scan on a fresh session. **Delta since the run above:**

- **Prior close recommendations landed.** #430, #439, #461 are now **closed** — the queue no
  longer carries them. Good.
- **Four new PRs opened today** (#471, #472, #474, #476) postdate the scan above and are added
  below.
- **Terminal answer is unchanged: No.** 15 open PRs, **0 auto-mergeable**. 5 `DEFERRED(draft)`
  (#412, #415, #434, #442, #456), **10 `HALTED`** (all owner-gated). Nothing could be driven to
  `MERGED` autonomously and safely; no branch outside this session's push scope was rebased, and
  no PR was closed without a human decision.

### New PRs — disposition

| PR | Author | Type | `mergeable_state` | Terminal | Note / staged next command |
|----|--------|------|-------------------|----------|----------------------------|
| #471 | groupthinking | Firebase AI Logic docs | `unstable`, **inverted** | HALTED(inverted_base) | **head=`main`, base=`v0/ultrathinking-588aba59`** → 2877 files / 169 commits of reverse-merge noise. Not a forward PR. **Recommend close.** |
| #472 | groupthinking (Claude) | Mermaid arch diagram | `blocked` | HALTED(awaiting_merge_approval) | Clean single-file docs, no conflict — only the protected-`main` gate. Closest-to-ready of the queue; needs human merge sign-off (or `automerge` label). |
| #474 | groupthinking | docstrings / arch overview | `dirty` | HALTED(merge_conflict) | `git checkout agent-lock-architecture-overview && git rebase origin/main` → resolve → `git push --force-with-lease` |
| #476 | groupthinking | GCP secrets / X-API-Key | `unstable`, **inverted** | HALTED(inverted_base) | **head=`main`, base=`v0/ultrathinking-789d2ffd`** — same reverse-merge shape as #471. Its substantive `X-API-Key` work already appears on `main` via #470/#473. **Recommend close.** |

### CI signal clarification

The near-universal red on the queue is the **non-required `Vercel` preview deploy** context
(the repo-wide `react`/`react-dom` v19 mismatch whose fix sits unmerged in draft **#412**), not
per-PR test failures. The required `Vercel Deployments – garv_projects` context is green
everywhere ("No required projects to validate"). **#436** even shows the Vercel deploy fully
green — it is blocked *only* by its merge conflict + the human gate. Highest-leverage single
action for the whole queue: get #412 ready and merged so preview CI stops reddening every branch.

### Owner actions to unblock (nothing here is autonomously safe)

1. **Close the two inverted/junk PRs:** #471, #476 (and #433, still corrupted).
2. **Merge the one clean, ready PR** behind the protected gate: #472 (docs-only) — or label it
   `automerge`.
3. **Land the react19 build fix** (#412, draft) to un-red preview CI across the queue.
4. **Authorize rebases** on the conflicted branches (#327, #328, #414, #436, #474; #365 is on a
   fork) — each needs a `rebase origin/main` + force-push to *its own* branch, outside this
   session's push scope.
