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
