# EventRelay Branch Audit — 2026-07-01

Audit of all 68 remote branches (`origin/*`, excluding `main`) plus a merge pass
on mergeable open PRs. Run with the `branch-cleanup` 6-gate harness
(`scripts/maintenance/branch-fail-test.sh`) enriched with live GitHub PR state.

## Verdict tally

| Verdict | Count | Meaning |
|---|---|---|
| **KEEP** | 19 → 17 | Open PR. 2 merged this pass (see below); 17 remain open. |
| **CLOSE-SAFE** | 38 | PR already closed/merged (ref preserved) or zero unique work. |
| **REVIEW** | 11 | No open PR but carries content / is a merged-PR remnant — human glance. |

Full evidence matrix: `docs/branch-cleanup-matrix.md` / `.csv`.

## Merges landed this pass

Only branches that were **non-draft, small real diffs, all CI green** were merged:

| PR | Branch | Change | Checks |
|---|---|---|---|
| #444 | `v0/ultrathinking-f213cca6` | gitignore + drop runtime audit logs (2 files) | 21/21 green → squash-merged |
| #432 | `copilot/find-tips-from-github-changelog` | parallel lint jobs, auto-label, docs (4 files) | 22/22 green → squash-merged |

Both were `mergeable_state: blocked` only on the required-review rule; CI was fully green.

## Open PRs NOT merged (and why)

**Drafts (author/bot "not ready" — GitHub refuses to merge drafts):**
- #448 `claude/todo-implementation-d49k3i` — majority-vote impl (1 file). Ready in substance; mark ready-for-review to merge.
- #445 `jules-12006327251276669115-4bbd6fbb` — concurrent batch queries (1 file).
- #446 `jules-7557281686534642670-eb4948a9` — exception-handler logging (1 file).
- #442 `claude/determined-maxwell-06popt` — CI cleanup companion to already-merged #441 (deletes 2 dead workflows).

**Orphaned pre-rewrite branches (1,505–2,991 unique files vs `main`):**
`agent-lock-architecture-overview` #324, `chore/security/upgrade-dev-deps` #327,
`chore/security/upgrade-vitest-vite` #328, `claude/database-schema-extraction` #436,
`claude/dazzling-edison-j79g5c` #434, `claude/dazzling-edison-ra3f0m` #412,
`claude/evaluate-unused-folders` #439, `claude/gifted-keller-9tw3p4` #415,
`copilot/add-ast-validation-layer` #316, `copilot/complete-repo` #430,
`jules-9638972698930112439-d2c4ab7c` #414, `dependabot/npm_and_yarn/zod-4.4.3` #422,
`test-index-analysis-grade-…` #433.

`main` was force-pushed (secret-purge), orphaning these branches. `git merge-tree`
reports them "clean" only because unrelated trees don't textually conflict — merging
would **clobber** `main`. They need a rebase onto current `main` (or fresh re-cut),
not an auto-merge. Left for human decision.

## Cleanup script

`scripts/maintenance/branch-cleanup-delete.sh` (regenerated from this run) archive-tags
then deletes. Nothing is deleted automatically — run explicitly:

```bash
DRY_RUN=1 scripts/maintenance/branch-cleanup-delete.sh safe   # preview 38 CLOSE-SAFE
scripts/maintenance/branch-cleanup-delete.sh safe             # execute
```

Recover any branch: `git push origin archive/<branch>:refs/heads/<branch>`.
