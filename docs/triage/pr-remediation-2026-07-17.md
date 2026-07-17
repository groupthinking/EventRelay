# PR Remediation & Publish — 2026-07-17

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge). CodeRabbit handle: `@coderabbitai`
(`.coderabbit.yaml` present, `request_changes_workflow: true`).

## Scan

**35 open PRs** (up from 26 at run 10). Non-draft: 32. Draft: 3 (`#799`, `#800`, `#803`).

Live status matrix (`mergeable_state` / real CI / review), sorted by number:

| PR | author | mergeable | CI (real) | review | note |
|----|--------|-----------|-----------|--------|------|
| 612 | groupthinking | blocked | ✅ | none | prisma earlyAccess flag removal; needs review |
| 617 | groupthinking (Devin) | blocked | ❌ real | none | OTEL override; web-build cluster |
| 620 | groupthinking (Devin) | blocked | ✅ | none | package-lock integrity; web-build cluster |
| 621 | groupthinking (Devin) | blocked | ✅ | none | pin OTel deps; web-build cluster |
| 622 | groupthinking (Devin) | dirty | ❌ real | none | Copilot #389 follow-up; conflict + red |
| 624 | groupthinking (Devin) | blocked | ⏳ pending | none | firstNonNull null-check |
| 626 | groupthinking (Devin) | blocked | ✅ | none | Sentry OTel + Tailwind v4; web-build cluster |
| 628 | groupthinking (Devin) | blocked | ⏳ pending | none | bare merge-commit PR |
| 629 | groupthinking (Devin) | unstable | ❌ real | none | **revert Tailwind→v3** (competes with 630) |
| 630 | groupthinking (Devin) | dirty | ❌ real | none | **migrate Tailwind→v4** (competes with 629) |
| 646 | jules[bot] | dirty | ❌ real | none | Phase-3 load/e2e test suite |
| 649 | jules[bot] | dirty | ❌ real | **approved** | Gemini 4xx retry fix; conflict + red |
| 651 | jules[bot] | dirty | ✅ | **approved** | MD5→SHA-256; conflict only |
| 703 | jules[bot] | unstable | ❌ real | **approved** | SSL config fix (**dup** of 705/721) |
| 705 | jules[bot] | dirty | ✅ | **approved** | SSL verify fix (**dup** of 703/721) |
| 717 | jules[bot] | dirty | ✅ | **approved** | BigQuery export tests; conflict only |
| 720 | jules[bot] | blocked | ⏳ pending | none | async httpx Grok |
| 721 | jules[bot] | dirty | ⚠️ false-red | none | SSL cert verify (**dup** of 703/705) |
| 726 | jules[bot] | dirty | ⚠️ false-red | **approved** | weight-persistence tests |
| 728 | jules[bot] | dirty | ⚠️ false-red | none | API cost webhook |
| 732 | jules[bot] | dirty | ⚠️ false-red | none | Redis consumer for orchestrator |
| 734 | groupthinking | blocked | ❌ real (CodeQL) | none | 7 CodeQL findings; builds on #733 |
| 737 | groupthinking | dirty | ✅ | none | **conflict-marker fix — OBSOLETE** |
| 738 | groupthinking | dirty | ✅ | none | pipeline stream handler refactor |
| 744 | groupthinking | dirty | ✅ | none | skill-trigger dotted-convention |
| 745 | groupthinking | dirty | ✅ | none | CI conflict-marker guard job |
| 749 | jules[bot] | blocked | ✅ | none | asyncio.gather batch query (rel. #799) |
| 758 | groupthinking | unstable | ✅ | none | **GREEN — only needs review** |
| 787 | groupthinking | dirty | ✅ | none | **conflict-marker fix — OBSOLETE** |
| 789 | groupthinking | dirty | ✅ | none | **conflict-marker fix — OBSOLETE** |
| 790 | groupthinking | blocked | ✅ | none | **conflict-marker fix — OBSOLETE** |
| 799 | groupthinking | blocked | ✅ | none | **draft** — execute_batch_queries concurrency |
| 800 | jules[bot] | blocked | ⚠️ false-red | none | **draft** — binary-search transcript (**dup** of 803) |
| 801 | jules[bot] | blocked | ⚠️ false-red | none | info-disclosure in API errors |
| 803 | jules[bot] | blocked | ⚠️ false-red | none | **draft** — binary-search transcript (**dup** of 800) |

Legend: **real** = GitHub Actions job actually failing; **false-red** = only a
"Canceled from the Vercel Dashboard" commit status is red while all required GH
Actions checks (test/lint/build/security) are green — safe to ignore / re-run.

## Precondition verified: `main` is healthy

The recurring "`main` ships committed conflict markers" premise (PRs #737/#787/#789/#790)
is **no longer true**. Current `origin/main` HEAD `f14c95a` was unbroken by the run of
merges `#793/#794/#795/#797/#798` and `f14c95a`. Verified locally on `main`:

- `git grep -E '^(<<<<<<<|>>>>>>>) '` over `src/` → **no conflict markers**.
- `python3 -m compileall -q src/skills/` → **OK** (the skills package these PRs claimed
  raised `SyntaxError` now imports cleanly).

⇒ The four conflict-marker "fix(main)" PRs are **superseded/obsolete**.

## Dispositions

### DEFERRED — drafts (SCOPE GATE)
`#799`, `#800`, `#803` → draft. Skipped. (`#800`/`#803` are also duplicates of each other.)

### DEFERRED (redundant / obsolete) — recommend owner close
- **`#737`, `#787`, `#789`, `#790`** — conflict-marker "fix(main)" PRs against an
  already-fixed `main`. Nothing to fix; would re-touch resolved files.
- **SSL cluster** `#703` / `#705` / `#721` — three PRs fixing the *same* insecure-SSL
  config in the video processors. `#705` is approved + real-CI green (only conflicted).
  Keep **`#705`**, close `#703` and `#721` as duplicates.
- **Transcript binary-search** `#800` / `#803` — identical change (O(N)→O(log N)
  `activeSegmentId`). Collapse to one; both currently draft.

### HALTED(awaiting_merge_approval) — green/approved, blocked only by the human gate
Protected `main` requires review; **no PR carries an `automerge` label**, so
`auto_merge_policy: label:automerge` yields **no auto-merge**. Merges are the owner's.
Closest to mergeable:
- **`#758`** — GREEN (real CI success, `unstable` = a non-required check only). Needs one review.
- **`#651`** — approved, real-CI green, only conflicted → rebase then merge.
- **`#705`** — approved, real-CI green, only conflicted → rebase then merge (SSL fix; supersedes 703/721).
- **`#717`** — approved, real-CI green, only conflicted → rebase then merge (BigQuery tests).
- **`#726`** — approved, GH-Actions green (Vercel false-red), only conflicted → rebase then merge.

### HALTED(ci_failing) — real red CI, needs a code fix before it can advance
`#617`, `#622`, `#629`/`#630` (mutually-exclusive Tailwind approaches — owner must pick
one), `#646`, `#649`, `#734` (required CodeQL). Not merge-ready; require engineering, and
several are entangled clusters (web-build `#617/#620/#621/#626/#629/#630`; owner should
choose a single web-build remediation branch rather than land fragments).

## Is more work needed?

**No autonomous *merge/land* work is available this iteration.** Every non-draft PR is
gated by one of: (a) a required human review on protected `main`, (b) an unresolved merge
conflict, or (c) a genuine red CI job needing a code decision — and none carry `automerge`.
Bypassing (a) is explicitly out of scope; (b) mass-rebasing 17 orphaned-history bot
branches unattended is riskier than the backlog it clears; (c) requires owner direction
(especially the mutually-exclusive Tailwind v3-vs-v4 choice). The backlog is **stuck at
the human gate**, not at automation capacity.

### Staged next commands (owner's call)

```bash
# Obsolete — main already fixed the conflict markers these target
gh pr close 737 787 789 790 --comment "Superseded — main is clean (f14c95a); no conflict markers remain (verified: src/skills compiles, no markers in src/)."

# Duplicate SSL fixes — keep #705 (approved, CI-green)
gh pr close 703 721 --comment "Duplicate of #705 (approved, CI-green). Consolidating the SSL-verification fix there."

# Merge-ready after a rebase onto current main (approved + real-CI-green, conflict-only)
for pr in 651 705 717 726; do
  git fetch origin "pull/$pr/head:pr-$pr" && git checkout "pr-$pr" && git rebase origin/main
  # resolve, then: git push --force-with-lease && gh pr merge $pr --squash
done

# #758 is green — needs one review, then:
gh pr merge 758 --squash

# Needs an engineering decision before it can advance:
#   Tailwind: choose ONE of #629 (revert→v3) or #630 (migrate→v4); close the other.
#   #734: address the 7 CodeQL findings. #617/#622/#646/#649: fix real red CI.
```

Re-run when the owner clears a review gate, picks the Tailwind direction, or promotes a
draft out of WIP.
