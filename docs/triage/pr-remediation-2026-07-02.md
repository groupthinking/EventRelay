# PR Remediation & Publish — Triage Matrix (2026-07-02)

Entry scan + terminal-state disposition for all open PRs against `main`, run under the
PR Remediation & Publish Runbook. Oldest-first. This is the byproduct-of-acting report;
the terminal state is the outcome for each node.

## Systemic blockers found (these gate the whole backlog)

1. **CodeRabbit is out of credits.** Every PR shows a red status check:
   `CodeRabbit — "Prepaid credits exhausted — enable usage-based reviews"`.
   The runbook's remediation engine (steps 4–6) is CodeRabbit-driven, so it is
   currently inoperative. Posting `@coderabbitai` comments will no-op until credits
   are refilled or usage-based reviews are enabled.
2. **No PR is labeled `automerge`**, and `main` is protected. Under
   `auto_merge_policy: label:automerge`, the PUBLISH GATE halts every green PR on
   human sign-off — nothing auto-merges.
3. **`main` was force-pushed** (secret-purge, per `CLAUDE.md`), orphaning older
   branches. 6 of 7 non-draft PRs are `mergeable_state: dirty` (real conflicts vs.
   current `main`) as a direct consequence.

## Terminal-state table

| PR | Author | Age | Review | CI / checks | Conflicts | Action taken | Terminal state |
|----|--------|-----|--------|-------------|-----------|--------------|----------------|
| #327 | groupthinking | ~13d | 6 comments, no approval | conflict-blocked | **dirty** | scanned | `HALTED(merge_conflict)` |
| #328 | groupthinking | ~13d | 6 comments | conflict-blocked | **dirty** | scanned | `HALTED(merge_conflict)` |
| #365 | groupthinking (fork `kk-agent`) | ~11d | 2 comments | conflict-blocked | **dirty** | scanned | `HALTED(merge_conflict)` |
| #412 | claude (bot) | ~8d | — | — | — | scope gate | `DEFERRED(draft)` |
| #414 | google-labs-jules (bot) | ~7d | 8 comments | conflict-blocked | **dirty** | scanned | `HALTED(merge_conflict)` |
| #415 | claude (bot) | ~7d | — | — | — | scope gate | `DEFERRED(draft)` |
| #430 | copilot (bot) | ~4d | — | — | — | scope gate | `DEFERRED(draft)` |
| #433 | google-labs-jules (bot) | ~4d | 9 comments | conflict-blocked | **dirty, 1547 files / −142k** | scanned | `HALTED(corrupted_branch)` → recommend **CLOSE** |
| #434 | claude (bot) | ~4d | — | — | — | scope gate | `DEFERRED(draft)` |
| #436 | Claude (bot) | ~4d | 5 comments | Vercel green | **dirty** | scanned | `HALTED(merge_conflict)` |
| #439 | claude (bot) | ~3d | — | — | — | scope gate | `DEFERRED(draft)` |
| #442 | claude (bot) | ~3d | — | — | — | scope gate | `DEFERRED(draft)` |
| #456 | claude (bot) | ~0d | — | — | — | scope gate | `DEFERRED(draft)` |
| #458 | groupthinking | ~0d | Copilot (6) + Devin (7) issues | Vercel green; red = **CodeRabbit-credits only** | blocked (no conflict) | scanned | `HALTED(awaiting_review_and_merge_approval)` |
| #459 | claude (bot) | ~0d | — | — | — | scope gate | `DEFERRED(draft)` |

**Totals:** 0 `MERGED` · 8 `DEFERRED(draft)` · 7 `HALTED` (6 conflict — one of them corrupted — + 1 awaiting review/merge).

## Staged next commands (per HALTED PR)

Conflict PRs — rebase onto current `main` from a writable checkout, then re-request review:

```bash
# #327 / #328 / #365 / #414 / #436  (substitute branch)
git fetch origin main
git checkout <pr-head-branch>
git rebase origin/main      # expect heavy conflicts on orphaned branches; resolve, then:
git push --force-with-lease
```

- **#433** — do **not** rebase. The 1,547-file / −142k-line diff is orphaned-history
  corruption, not a real change set. Recommend **close** (archive-tag first per
  `branch-cleanup` skill) and, if the tests are still wanted, cherry-pick only the
  test file onto a fresh branch off `main`.
- **#458** — no conflict; blocked on review. Address the Copilot (6) + Devin (7)
  inline findings, then a human merges (or add `automerge` if policy allows). The red
  CI is solely the CodeRabbit-credits status, not a test failure.

## Why this run did not merge anything

- Merging to protected `main` is human-gated (no `automerge` labels) — the runbook's
  PUBLISH GATE is human by default.
- Conflict resolution requires pushing to each PR's own branch; this session is
  restricted to `claude/determined-maxwell-5593h9`.
- The CodeRabbit review loop cannot run (credits exhausted).

All three are human/owner actions. Re-running the loop will not change them until an
owner (a) refills CodeRabbit credits or enables usage-based reviews, (b) decides the
merge/close calls above, and (c) authorizes conflict-resolution pushes to the PR branches.
