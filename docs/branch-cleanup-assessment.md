# EventRelay — Branch Cleanup Assessment

**Date:** 2026-06-01 · **Scope:** all 67 remote branches (`main` + 66 others) on `groupthinking/EventRelay`
**Harness:** [`scripts/maintenance/branch-fail-test.sh`](../scripts/maintenance/branch-fail-test.sh) · **Full matrix:** [`branch-cleanup-matrix.md`](./branch-cleanup-matrix.md) / [`.csv`](./branch-cleanup-matrix.csv)

## TL;DR — how many can we close?

Of the **66** non-`main` branches:

| Verdict | Count | Meaning |
|---|---:|---|
| **KEEP** | **5** | Has an **open PR** — active work, do not touch. |
| **CLOSE-SAFE** | **28** | PR already closed/merged, **or** tip fully contained in `main`. Zero work lost. |
| **CLOSE-STALE** | **30** | No PR, stale (>30d) and far behind `main` (orphaned by the history rewrite) or superseded. |
| **REVIEW** | **3** | No PR but recent / carries unique work — one human glance, then close. |

**Bottom line: ~58 branches can be closed immediately, and up to 61 after a 5-minute review of the 3 flagged. Keep only the 5 with open PRs.**

The 5 to **keep** (open PRs): `claude/confident-roentgen-18e955` (#220), `claude/elegant-neumann-5d4867` (#217), `claude/exciting-ptolemy-l9vHs` (#216), `claude/modernize-stale-model-ids` (#215), `coderabbitai/utg/a86dca6` (#221).

The 3 to **review** before closing: `v0/ai-system-architecture-ac4e7c39` (5d old, no PR), `fix/unified-ai-sdk-real-providers-154` (superseded by the model-migration PRs #213/#215), `copilot/improve-documentation` (docs-only, won't merge clean).

## Why this needs a real test, not a glance

`main`'s history was **rewritten** — a secret-purge force-push (see the `scripts/security/purge-secrets-from-history.sh` referenced by PR #217). That orphaned the older branches: they share almost no common ancestor with today's `main`. The consequence is that **naive git signals lie**:

- A three-dot `git diff main...branch` reads **0 files** for a branch that actually diverges by ~10,000 files — because there's no real merge-base.
- `git merge-tree` reports a **clean merge** for those same orphans — because two unrelated trees don't textually *conflict*, they just clobber.

So the assessment can't trust ancestry or merge-cleanliness alone. The two signals that **survive a history rewrite** are **PR state** (authoritative: a human/bot already decided) and **staleness** (age + commits-behind). The harness leans on those and uses the git signals only as corroboration.

## The "fail test" — the gate battery each branch runs

Every branch is scored by [`branch-fail-test.sh`](../scripts/maintenance/branch-fail-test.sh) against six gates. Each gate is reproducible and emits a column in the matrix, so the verdict is auditable rather than asserted.

| Gate | What it runs | What a *fail* means |
|---|---|---|
| **G1 — PR state** | cross-reference branch ↔ GitHub PRs (`list_pull_requests`) | open ⇒ KEEP; closed ⇒ decision already made (GitHub preserves the ref); none ⇒ ambiguous |
| **G2 — Redundancy** | `git merge-base --is-ancestor`, `git cherry main branch` | tip is an ancestor of / fully cherry-absorbed into `main` ⇒ **nothing unique to lose** |
| **G3 — Clean-merge probe** | `git merge-tree --write-tree main branch` | textual conflicts ⇒ won't land without rework (corroborating signal only — see history-rewrite caveat) |
| **G4 — Unique diff** | `git diff --shortstat main branch` | files/LOC that would actually be lost on delete |
| **G5 — Staleness** | last-commit age + `git rev-list --count branch..main` | >30d **and** >50 behind ⇒ pre-rewrite orphan, not salvageable as-is |
| **G6 — CI fail-test** *(opt-in `--build`)* | per-branch worktree: `ruff` + `mypy` + `pytest -m "not slow"`; `turbo run build lint` | a branch that **fails its own CI**, has no open PR, and is stale is dead code, not lost work |

### Decision rule

```
open PR                                   -> KEEP
closed PR                                 -> CLOSE-SAFE   (ref preserved by GitHub)
tip ancestor of main OR zero unique diff  -> CLOSE-SAFE   (nothing to lose)
no PR & stale(>30d) & behind(>50)         -> CLOSE-STALE  (pre-rewrite orphan / superseded)
no PR & stale(>30d) & won't merge clean   -> CLOSE-STALE
otherwise                                 -> REVIEW       (recent/unique — human glance)
```

## Reproduce / back-test it

```bash
# Cheap gates (seconds) — regenerates docs/branch-cleanup-matrix.{md,csv}
scripts/maintenance/branch-fail-test.sh --pr-json /tmp/prmap.txt

# Full back-test including the per-branch CI fail-test (slow: checks out & builds each branch)
scripts/maintenance/branch-fail-test.sh --pr-json /tmp/prmap.txt --build
```

`--pr-json` is a `head.ref|state|number` line file derived from the GitHub PR list. The G6 build gate is opt-in because it checks out and installs every branch (hours, and many pre-rewrite branches won't install) — run it on the **REVIEW** subset before deleting if you want the strongest possible evidence.

## Suggested execution order

1. **Now (zero risk):** delete the **28 CLOSE-SAFE** branches — every one is either a closed PR (ref retained by GitHub) or fully contained in `main`.
2. **Next:** delete the **30 CLOSE-STALE** branches — pre-rewrite orphans and superseded duplicates. Optionally tag them first: `git tag archive/<branch> origin/<branch>` so the SHAs remain recoverable.
3. **Quick glance, then close:** the **3 REVIEW** branches.
4. **Never (for now):** the **5 KEEP** branches with open PRs.

> Deletion is reversible for ~90 days via GitHub's "restore branch" on the PR, and indefinitely if you create the `archive/*` tags above — so even the CLOSE-STALE batch carries no real data-loss risk.
