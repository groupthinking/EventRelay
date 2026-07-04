# PR Remediation & Publish — run 2026-07-04

Oldest-first entry scan and terminal-state disposition for all **10 open PRs**, run under
the PR Remediation & Publish Runbook. This is a triage artifact, not a code change.

**Continues [`pr-remediation-2026-07-03.md`](./pr-remediation-2026-07-03.md).** Since that
run: #461 was closed, several fixes merged to `main` (now well past `#490`/`#491`/`#492`/
`#496`/`#456`), and five new PRs opened (#474, #478, #488, #494, #495). The structural
conclusion is unchanged — see "Answer to the loop's terminal question".

## Headline

- **No PRs were merged by this run.** Every open PR is owner-gated: draft, a real merge
  conflict on a branch outside this session's push scope, a corrupted/orphaned branch, or
  the protected-`main` publish gate with no `automerge` label. Nothing remained that could
  be driven to `MERGED` autonomously and safely.
- **#478 and #488 are the two closest to merge.** Both are `blocked` (not conflicted) with
  **every code check green** — `build`, `test`, `lint-frontend`, `lint-python`,
  `Security Scan (js/py)`, `bandit`, `trivy`, `npm-audit`, `python-safety`, `CodeQL`,
  `dependency-review`, `gitleaks`, coverage, Vercel Agent Review. The **only** non-green
  check on each is `E2E Pipeline Tests`, which targets the **live deployment** (failure on
  #478, cancelled on #488) — an environmental gate, not a defect in either diff (the same
  E2E-vs-live caveat #433's author noted). They need a **human**: an approving review plus
  either a green/again-run E2E or an admin merge override on protected `main`.

## Terminal states (this run)

- **0** `MERGED` (by this run).
- **2** `DEFERRED(draft)` — #494, #495.
- **8** `HALTED`:
  - `merge_conflict` (needs a rebase pushed to the PR's own branch — outside this session's
    push scope): **#327**, **#414**, **#474**, and **#365** (**fork** `kk-agent/EventRelay`
    — rebase must come from the fork owner). **#442** carries a 384-file / −71.7k-line
    orphaned-style tree (cleanup pass 2, superseding #441) and needs an owner merge-or-
    cherry-pick decision.
  - `corrupted_branch` — **#433** (1547 files / −142k lines vs. base; orphaned by the `main`
    force-push). **Recommend close** (archive-tag first).
  - `awaiting_merge_approval` — **#478**, **#488** (code-green; blocked only by the live-
    deployment E2E gate + required review on protected `main`).

## Matrix (oldest first)

| PR | Author | Type | mergeable_state | CI (code checks) | Terminal | Staged next command |
|----|--------|------|-----------------|------------------|----------|---------------------|
| #327 | groupthinking | security dev-deps (Sentry, AI extract) | dirty | — | HALTED(merge_conflict) | `git checkout chore/security/upgrade-dev-deps && git rebase origin/main` → resolve → `git push --force-with-lease` |
| #365 | groupthinking (fork kk-agent) | Vercel AI Gateway | unknown/conflict | — | HALTED(merge_conflict) | fork owner: rebase `feat/vercel-ai-gateway-issue-269` onto `groupthinking/main` |
| #414 | jules[bot] | Dockerfile rewrite (#406) | dirty | — | HALTED(merge_conflict) | `git checkout jules-9638972698930112439-d2c4ab7c && git rebase origin/main` → resolve → push |
| #433 | jules[bot] | DB optimizer unit tests | unknown, 1547 files | — | HALTED(corrupted_branch) | `git tag archive/pr-433 3c68732 && gh pr close 433 --comment "orphaned by main force-push; re-open a clean branch"` |
| #442 | groupthinking | remove dead mcp-servers workflows | unknown, 384 files | — | HALTED(merge_conflict) | owner: merge (supersedes #441) or cherry-pick the workflow-delete commit onto #441 |
| #474 | groupthinking | docstrings: agent-lock overview | dirty | — | HALTED(merge_conflict) | `git checkout agent-lock-architecture-overview && git rebase origin/main` → resolve → push |
| #478 | groupthinking | GCP secrets + X-API-Key auth (#476) | blocked | **all green**; E2E(live)=fail | HALTED(awaiting_merge_approval) | add `automerge` label, or approve review + admin-merge; optional: re-run E2E once |
| #488 | groupthinking | Upstash Redis credential resolver | blocked | **all green**; E2E(live)=cancelled | HALTED(awaiting_merge_approval) | add `automerge` label, or approve review + admin-merge; optional: re-run E2E once |
| #494 | groupthinking | roadmap features backing #487 tests | **draft** | — | DEFERRED(draft) | mark ready when validated (superset of #487) |
| #495 | Copilot | repair imports, drop committed keys, SDK sync (#413) | **draft** | — | DEFERRED(draft) | mark ready when validated |

## Owner-gated blockers (structurally unchanged from 2026-07-03)

1. **No `automerge` labels on protected `main`.** `auto_merge_policy` is label-gated, so the
   publish gate halts every green PR on human sign-off. To let the runbook merge a green PR
   unattended, add the `automerge` label — this is the single lever that would let #478/#488
   proceed autonomously.
2. **Live-deployment E2E is a required check.** `E2E Pipeline Tests` runs against the
   deployed environment, so it can be red/cancelled for reasons unrelated to a PR's diff
   (confirmed green code checks on #478/#488). It still blocks merge on protected `main`
   until it passes or an admin overrides.
3. **`main` force-push orphaned older branches** (documented in `CLAUDE.md`). The conflicted
   PRs need rebases pushed to their own branches — outside this session's push scope (this
   session may only push to its designated branch), and force-pushing other contributors'/
   bots'/forks' branches unattended risks clobbering their work.
4. **Close decisions need a human + archive-tag.** #433 (corrupted) should be archive-tagged
   then closed per `CLAUDE.md` ("Never delete branches without archive-tagging first") — not
   an unattended action.

## Answer to the loop's terminal question

*Is more work needed that this session can complete autonomously and safely?* **No.** Every
remaining open PR requires the maintainer: an `automerge` label / merge sign-off on
protected `main` (#478, #488 — code-green, one approval away), a rebase authorized on its own
branch (#327, #365, #414, #442, #474), a draft→ready promotion (#494, #495), or an archive-
and-close decision (#433). The toil up to each irreversible step is automated and staged
above; the irreversible steps are correctly halted for human sign-off. The loop terminates
here rather than re-polling owner-gated state that cannot change without the owner.
