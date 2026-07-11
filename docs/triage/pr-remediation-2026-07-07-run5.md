# PR Remediation Run — 2026-07-07 (run 5)

Entry-scan + terminal-state disposition of **all open PRs** under the PR Remediation &
Publish Runbook. Follows run 4 (same day), whose exit condition — *"re-run when the owner
clears a gate"* — has partially been met: the owner **closed #552, #557, #558** since
run 4 and opened a further wave of fix PRs (**#560–#563**).

- **Surface:** GitHub MCP (PR read + comment). Merge to protected `main` is held for owner
  sign-off per the runbook's publish gate.
- **Auto-merge policy (unchanged from runs 2–4):** merge only demonstrably-safe,
  auto-approved, CI-clean changes with no runtime/deploy blast radius; hold anything
  carrying a merge conflict, a breaking change, or a branch-protection block for owner
  sign-off.

## What changed since run 4

- Main HEAD advanced to `c837900` (run-4 triage docs).
- **Closed by owner:** #552 (merge-commit, no net content), #557 + #558 (part of the
  orphaned `dazzling-edison` OTel/Sentry cluster). Run 4's close recommendation was acted
  on for two of the four.
- **Still open despite run-4 close recommendation:** #556, #559 (tailwind-v3 revert/pin,
  orphaned — `main` is on tailwind v4).
- **New PRs opened:** #560, #561, #562 (all `claude/dazzling-edison-*`, all `dirty`) and
  **#563** (docs-only, the one clean/green PR this run).

### 🔴 New systemic blocker — CodeRabbit prepaid credits exhausted

Since run 4's scan, every fresh CodeRabbit status now reports **"Prepaid credits
exhausted — enable usage-based reviews"** (first seen ~01:40–01:44 UTC today on
#556/#559/#560/#561/#562). **The CodeRabbit review loop that the runbook's step 4 depends
on cannot run until the owner tops up credits or enables usage-based billing in the
CodeRabbit dashboard.** This is an owner-gated action, not automatable from this session.
The red ✗ this puts on several otherwise-fine PRs is a *billing* status, not a code
failure.

## Oldest-first disposition — non-draft open set (11)

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | large (40 files), security/frontend | `dirty` | Needs rebase + review — owner | HALTED(merge_conflict) |
| #365 | kk-agent (fork) | 06-21 | AI Gateway text+video (#269) | Vercel deploy ✗ | Owner review (fork) | HALTED(needs_review) |
| #414 | jules[bot] | 06-25 | Dockerfile prod rewrite (#406) | Vercel deploy ✗ | Likely superseded by drafts #539/#540 — owner picks one | HALTED(needs_review) |
| #553 | owner | 07-07 | vite 8.0.16 + vitest bump | `dirty` | Rebase + web-build smoke-test — owner | HALTED(merge_conflict) |
| #555 | owner | 07-07 | remove obsolete prisma `earlyAccess` flag | `dirty` | Small, safe once rebased — owner | HALTED(merge_conflict) |
| #556 | owner | 07-07 | revert tailwindcss → v3 | `dirty` (orphaned) | **Superseded** — main on tailwind v4. **Close** (run-4 repeat) | HALTED(orphaned_history) |
| #559 | owner | 07-07 | pin tailwindcss → v3 | `dirty` (orphaned) | **Superseded** — main on tailwind v4. **Close** (run-4 repeat) | HALTED(orphaned_history) |
| #560 | owner | 07-07 | `@tailwindcss/postcss` v4 build | `dirty` | `dazzling-edison` branch — rebase-or-close, owner | HALTED(merge_conflict) |
| #561 | owner | 07-07 | mcp #389 review — request summary + base_url guard | `dirty` | `dazzling-edison` branch — rebase-or-close, owner | HALTED(merge_conflict) |
| #562 | owner | 07-07 | OTEL override effective + Node engine | `dirty` | `dazzling-edison` branch — rebase-or-close, owner | HALTED(merge_conflict) |
| #563 | owner | 07-07 | **docs: align CLAUDE.md SDK floor → 0.105.0** | **clean; `blocked`** | **All GitHub Actions CI green.** Blocked only on required review (branch protection). **Ready to merge on owner approval.** | HALTED(awaiting_merge_approval) |

### #563 verified correct — the one merge-ready PR

`pyproject.toml:134` requires `anthropic>=0.105.0`; `CLAUDE.md:139` still stated
`>=0.78.0`. #563 is a 1-line docs fix that aligns the stated floor to the real constraint.
Full CI is green (build, test, lint-python, lint-frontend, CodeQL, Trivy, bandit,
npm-audit, dependency-review, all security scans). `mergeable_state: blocked` is the
branch-protection review gate, not a failure. Its three PR comments are bot noise
(Vercel, CodeRabbit skip, dependency-review) — no actionable findings. **This is the
cleanest merge candidate in the open set.**

## WIP drafts — DEFERRED(draft) (19)

Unchanged in character from run 4: mostly paired Copilot + Claude attempts at the same
issue (owner comparing two implementations per task). Un-draft the winner of each pair;
close the loser. See run-4 doc for the pairing table (#529/#530, #532/#543/#544,
#537/#538, #539/#540, #545/#546, #541/#542, plus #531, #534, #535, #536, #547, #549,
#550, #551).

## Auto-mergeable this run

**None.** Every non-draft PR is `dirty` (conflict) or branch-protection `blocked`.
#563 is CI-clean but held at the publish gate for owner approval per the runbook. There is
nothing this routine can safely merge unattended without either (a) choosing between the
owner's own competing PRs, or (b) bypassing branch protection on `main`.

## Staged commands (owner sign-off required)

```
# 1. Merge the one clean PR (all CI green, docs-only, 1 line):
gh pr review 563 --approve && gh pr merge 563 --squash

# 2. Close the orphaned tailwind-v3 pair (main is on v4; merging regresses):
gh pr close 556 559

# 3. Rebase-or-close the remaining dazzling-edison fix branches:
#    #560 (tailwind v4 postcss), #561 (mcp #389), #562 (OTEL) — all dirty.
#    If the concern is already on main, close; else re-cut a single fix from current main.

# 4. Separate concerns needing rebase + smoke-test:
git fetch origin chore/security/upgrade-vitest-vite && git rebase origin/main   # #553, then verify apps/web build

# 5. CodeRabbit: top up prepaid credits or enable usage-based reviews in the
#    CodeRabbit dashboard — the runbook's review loop is blocked until then.
```

## Is more work needed?

**No more work is safely automatable unattended — the loop has converged at an
owner-gated HALT, same terminal shape as run 4, plus one new blocker.** The gates are all
outside this session's authority:

1. **CodeRabbit prepaid credits exhausted** — blocks the review-loop mechanism entirely;
   requires owner billing action.
2. **Branch protection on `main`** — #563 is green and ready but needs a human approving
   review; the runbook holds the publish gate by default.
3. **Decisions between the owner's own PRs** — which Dockerfile (#414 vs #539/#540), which
   of each Copilot/Claude draft pair, rebase-or-close the `dazzling-edison` set.

**Recommended single quickest win for the owner: approve + squash-merge #563** (verified
correct, fully green). Then close #556/#559 and address CodeRabbit billing.

**Exit condition:** re-run when the owner clears a gate — approves/merges #563, closes the
orphaned set, tops up CodeRabbit, or picks winners in the draft pairs — at which point the
survivors become CI-checkable and, if green, mergeable.
