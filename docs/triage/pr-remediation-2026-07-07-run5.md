# PR Remediation Run — 2026-07-07 (run 5)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 4 (`docs/triage/pr-remediation-2026-07-06-run4.md`), whose
exit condition — *"re-run when the owner clears a gate (merges #442/#510, un-drafts
#494/#495, or rebases/closes the stale set)"* — has now been met.

- **Surface:** GitHub MCP (PR read + comment + close/merge), authed as repo owner.
- **Auto-merge policy applied (unchanged):** merge only demonstrably-safe, auto-approved,
  CI-only changes; hold anything carrying a documented breaking change, deploy/runtime
  blast radius, an unresolved merge conflict, or a branch-protection block for owner
  sign-off. Do **not** auto-merge to protected `main`, and do **not** override branch
  protection unattended. Redundant PRs are closed (reversible, non-merge cleanup).

## What changed since run 4

The owner cleared **every gate run 4 named**, and then some. `origin/main` now contains:

- **#495** — repair broken imports, remove committed API keys, align SDK types — **MERGED**.
- **#510** — `chrome-devtools-mcp` 0.10.2 → 1.5.0 (the supply-chain-flagged bump) — **MERGED**
  by the owner after the install-script review run 4 asked for.
- **#522** — `test_gemini_api.sh` hardcoded-Gemini-key scrub — **MERGED** (new since run 4).
- **#442** — dead mcp-servers workflow cleanup (run 4's cleanest merge candidate) — **CLOSED**
  by the owner at 2026-07-07T00:12Z.
- **#433** — orphaned-history unit-test artifact (run 4 recommended closing) — **CLOSED**
  by the owner at 2026-07-07T00:12Z.
- **#494** — **un-drafted** by the owner at 2026-07-07T00:13Z (was DEFERRED(draft) in run 4).

## The systemic finding this run — the backlog is now uniformly conflicted

Run 4 predicted: *"a fresh merge into `main` typically renders one or more of the remaining
… PRs redundant or conflicted."* That has now happened to the **entire** open set. With
#495/#510/#522 landed, GitHub has finished recomputing mergeability and **every open PR
except #524 reports `mergeable_state: dirty` (real merge conflicts against `main`)**:

| PR | `mergeable_state` | Why it now conflicts |
|----|-------------------|----------------------|
| #327 | `dirty` | 40-file dev-deps/Sentry/AI-extraction branch, base far behind post-#513 `main` |
| #365 | `dirty` | AI-Gateway feature (fork `kk-agent`), base far behind; touches `package.json`/`.env.example` |
| #414 | `dirty` | Dockerfile rewrite, base `ac55afe` far behind |
| #474 | `dirty` | 23-file docstring/refactor branch, base far behind |
| #494 | `dirty` | **edits the same `models.py` + `sdk/.../types.py` that #495 just rewrote** — direct overlap |

`#494` is the sharpest case: it adds `error_reason` to `VideoJobStatusResponse` and mirrors
it into the SDK types, which is exactly the pair of files **#495 ("align SDK types") just
landed**. Its conflict is therefore a genuine contract-file overlap, not incidental
drift — resolving it means reconciling #494's additive field against #495's rewrite and
then re-running #487's generated suite to confirm it still goes green.

## Action taken this run

- **No PR qualified for a safe unattended merge or auto-fix.** Every open PR is either
  conflicted against `main` (CONFLICT GATE) or blocked on a human review of protected
  `main` (PUBLISH GATE) — the two gates the runbook reserves for the owner.
- **No branch was auto-rebased.** The five conflicted branches are large/refactor
  (#327, #474), on a third-party fork I can't push to (#365 → `kk-agent`), bot-owned
  (#414 → jules), or a correctness-critical contract-file overlap (#494 over #495).
  Per the runbook's CONFLICT GATE, an autofix that can't cleanly resolve routes to
  `HALTED` with the rebase staged for a human — a blind unattended rebase over
  just-rewritten contract files risks silently breaking `main`, so it is explicitly
  **not** taken here.
- This run's own triage doc + the carried-forward run-4 doc are pushed on
  `claude/determined-maxwell-e0iuif` (this doc's branch) for the owner to merge.

## Oldest-first disposition (current open set — 6 PRs)

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | CodeRabbit ✅; stale Vercel fail | **dirty** | Needs rebase onto post-#522 `main` + owner review (40 files) | HALTED(merge_conflict + awaiting_review) |
| #365 | owner→`kk-agent` fork | 06-21 | AI-Gateway feature | **dirty** | Owner-gated; fork branch (no push access) — owner must rebase + review | HALTED(merge_conflict + needs_review) |
| #414 | jules[bot] | 06-25 | Dockerfile rewrite (resolves #406) | **dirty** | Owner-gated; bot branch — rebase + review | HALTED(merge_conflict + needs_review) |
| #474 | owner | 07-03 | Docstrings + refactor (23 files) | **dirty** | Owner-gated — rebase + review | HALTED(merge_conflict + needs_review) |
| #494 | owner | 07-03 | **un-drafted 07-07**; implements #487's tests | **dirty** | Conflicts with #495 on the same `models.py`/SDK-types files — needs careful rebase + re-run of #487 suite, then non-author review | HALTED(merge_conflict + awaiting_review) |
| #524 | owner | 07-06 | **All 26 checks green**; CodeRabbit review skipped-by-label; clean | none (`blocked`) | SIGPIPE/key-logging fix for `test_gemini_api.sh` (follow-up to merged #522). Ready to merge — **blocked only because the author (owner) cannot self-approve** a protected-branch PR | HALTED(awaiting_merge_approval) |

## Staged commands (owner sign-off required)

**Ready now — the single cleanest merge (needs one non-author approval):**
```
gh pr review 524 --approve   # from any account other than the author, then:
gh pr merge  524 --squash    # 1-file test-script fix, all 26 checks green, no app code
```
> #524 cannot be self-approved because GitHub blocks approving your own PR and `main`
> requires a non-author approving review. That review is the only thing between #524 and
> merge — this routine cannot supply it or bypass the branch-protection rule unattended.

**Just un-drafted — resolve the contract-file conflict, then advance:**
```
git fetch origin main && git checkout claude/determined-maxwell-e8uv5v && git rebase origin/main
# Resolve conflicts in src/youtube_extension/backend/api/v1/models.py and
# sdk/python/eventrelay_sdk/types.py against #495's landed rewrite (keep #495's alignment,
# re-add #494's additive `error_reason: Optional[str] = None` on both sides).
pytest tests/ -k "master_roadmap_fixes or api_v1_models" && npx vitest run VideoWorkflowStudio.test.tsx
git push --force-with-lease   # then request a non-author review
```

**Stale/large/fork — owner rebase + review (rebase onto post-#522 `main` first):**
```
# #327, #365 (fork), #414 (jules), #474  — all `dirty`; each needs a rebase then review.
```

## Systemic note — Vercel preview check (carried from run 3/4)

The non-required **Vercel** preview-deployment status still shows stale failures on the
older PRs (#327's dates to 2026-06-15). It is **not a required check** and does not block
merge — flagged only so a stale red X isn't mistaken for a per-PR code defect. #524's
Vercel deployment, by contrast, is fresh and green.

## Is more work needed?

**No — not for anything safely automatable unattended.** The loop's automatable work has
converged again: every open PR is now gated on an action this routine must not take
unattended — a non-author approval on protected `main` (#524) or a human-supervised
conflict resolution + review of a large/refactor/fork/contract-overlap branch
(#327/#365/#414/#474/#494). Blindly rebasing conflicted contract files or overriding
branch protection would trade safety for motion, which the runbook forbids.

The one net-new, low-risk, ready-to-land item is **#524** — green, clean, 1-file — held
solely by the self-approval rule. Re-run this loop when the owner clears a gate: approves
& merges #524, rebases #494 onto post-#495 `main`, or rebases/closes the stale set
(#327/#365/#414/#474). Each fresh merge into `main` will re-conflict whatever remains,
which is the next cleanup this routine can pick up.
