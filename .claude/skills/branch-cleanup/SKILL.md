---
name: branch-cleanup
description: >-
  Assess which git branches can be safely closed/deleted and back the call with
  evidence. Use when the user asks "which branches can I close/delete?", "clean
  up our branches", "we have 60+ branches — what's safe to prune?", or wants a
  data-backed branch audit. Runs a 6-gate fail-test per branch (PR state,
  redundancy, merge probe, unique diff, staleness, optional CI build) and emits
  a KEEP/CLOSE-SAFE/CLOSE-STALE/REVIEW decision matrix, then generates an
  archive-then-delete script. Honest across rewritten/force-pushed history.
---

# Branch Cleanup

Produce a defensible, reproducible verdict on every remote branch — which to
keep, which to close — backed by a per-branch evidence matrix rather than a
guess. Then hand the user a safe, reversible deletion script.

## When to use

Trigger on requests like: "how many of our branches can we close?", "clean up
stale branches", "branch audit", "what's safe to prune?", "we have 60+ branches".

## The core insight (read this first)

**Naive git signals lie after a history rewrite.** If `main` was ever
force-pushed (squash, rebase, or a secret-purge with tools like BFG /
`git filter-repo`), older branches get *orphaned* — they share little real
ancestry with today's `main`. The symptoms:

- `git diff main...branch` (three-dot) reads **0 files** for a branch that
  actually diverges by thousands of files (no real merge-base).
- `git merge-tree main branch` reports a **clean merge** for those orphans
  (unrelated trees don't textually *conflict* — they'd just clobber).

So **do not** base keep/close decisions on three-dot diffs or merge-tree alone.
The signals that survive a rewrite are **PR state** (authoritative — a human or
bot already decided) and **staleness** (age + commits-behind). Lean on those;
use git ancestry only as corroboration. Detect a likely rewrite when many
branches show large `behind` counts with old commit dates clustered before a
date where the file count jumps.

## Workflow

1. **Gather PR state** (authoritative gate). Use the GitHub MCP tools
   (`list_pull_requests` state=`all`, paginate) to map `head.ref → state →
   number`. Write one `branch|state|number` line per PR to a file, e.g.
   `/tmp/prmap.txt`. If the list response is huge, extract with
   `jq -r '.[] | "\(.head.ref)|\(.state)|\(.number)"'`.

2. **Run the harness** (cheap gates, seconds):
   ```bash
   scripts/branch-fail-test.sh --pr-json /tmp/prmap.txt
   ```
   Emits `docs/branch-cleanup-matrix.md` + `.csv`. Each branch is scored on:
   - **G1 PR-state** — open ⇒ KEEP · closed ⇒ CLOSE-SAFE (GitHub keeps the ref) · none ⇒ ambiguous
   - **G2 Redundancy** — `git cherry` / `--is-ancestor`: already in `main`? ⇒ nothing to lose
   - **G3 Merge-clean** — `git merge-tree` conflict count (corroboration only — see caveat)
   - **G4 Unique-diff** — files/LOC that would actually be lost
   - **G5 Staleness** — age + commits-behind (the truthful signal for orphans)
   - **G6 CI fail-test** *(opt-in `--build`)* — checks out each branch, runs lint/type/test/build; a branch that fails its own CI, has no open PR, and is stale is dead code, not lost work

3. **Read the tally** and sanity-check the `REVIEW` bucket by hand — those are
   the only ones needing judgment. Re-tune thresholds (`STALE_DAYS`,
   the `behind > 50` orphan rule) if the repo's cadence differs.

4. **Strongest evidence (optional):** run `--build` on the `REVIEW` subset
   before deleting, so the verdict carries real CI proof-of-work.

5. **Generate the deletion script** from the matrix CSV — archive-tag every
   branch *before* deleting so SHAs stay recoverable indefinitely:
   ```bash
   # one batch per verdict; each line: tag archive/<b>, push tag, push --delete
   for b in $(awk -F, 'NR>1 && $NF=="CLOSE-SAFE"{print $1}' docs/branch-cleanup-matrix.csv); do
     echo "git tag archive/$b origin/$b && git push origin refs/tags/archive/$b && git push origin --delete $b"
   done
   ```
   Always preview (dry-run) first. Recover any branch later with:
   `git push origin archive/<branch>:refs/heads/<branch>`.

## Verdict rule

```
open PR                                   -> KEEP
closed PR                                 -> CLOSE-SAFE   (ref preserved by GitHub)
tip ancestor of main OR zero unique diff  -> CLOSE-SAFE   (nothing to lose)
no PR & stale(>30d) & behind(>50)         -> CLOSE-STALE  (pre-rewrite orphan / superseded)
no PR & stale(>30d) & won't merge clean   -> CLOSE-STALE
otherwise                                 -> REVIEW       (recent/unique — human glance)
```

## Safety rules

- **Never delete branches automatically.** Produce the matrix + script; let the
  user run deletions (or explicitly authorize a batch).
- **Always archive-tag before delete** so nothing is truly lost.
- **Never touch branches with open PRs.**
- Deletion is reversible ~90d via GitHub "restore branch", and indefinitely via
  the `archive/*` tags.

## Bundled

- `scripts/branch-fail-test.sh` — the portable 6-gate harness (this is the asset).
