# PR Remediation & Publish — Run 11 (2026-07-09)

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge). CodeRabbit handle: `@coderabbitai`.

## Scan

**51 open PRs.** Prior runs (through run 10, on `main` as `e2916b9`) had declared
convergence with ~26 PRs, mostly drafts. Since then a **large batch of ~20 non-draft
PRs was auto-opened on 2026-07-09**, most on `claude/dazzling-edison-*` branches
(authored by `groupthinking` via Devin/Claude automation), plus assorted others.

`main` HEAD is now `c5350de` (merged `#638`, `#639`, `#641` since the batch was cut,
so the batch is also ~3 commits behind `main`).

## `main` is healthy — the build is already fixed

The 2026-07-09 batch is overwhelmingly aimed at "unblocking the `apps/web` production
build" (Tailwind v3↔v4, Sentry/OpenTelemetry deps). **That work is already on `main`:**

- `apps/web/package.json` on `main`: `tailwindcss@^4.3.1`, `@tailwindcss/postcss@^4.3.2`,
  full `@opentelemetry/*` set, `@sentry/nextjs@^10.63.0`.
- `apps/web/postcss.config.js` on `main` already uses the v4 plugin
  (`'@tailwindcss/postcss': {}`).
- Recent completed `main` CI runs are **green**.

Consequences for the batch:

- **Tailwind-v4 migration PRs** (e.g. `#618`, `#627`, `#630`, `#632`) come up
  `mergeable_state: dirty` — they **conflict** with `main` because the migration is
  already there.
- **"Revert to v3" PRs** (e.g. `#613`, `#616`, `#623`, `#629`) are tiny (2 lines) and
  would **regress** `main` back off v4.
- **OTel/Sentry-dep PRs** (`#614`, `#615`, `#617`, `#620`, `#621`, `#626`) duplicate deps
  already pinned on `main`.

→ **None of the build-churn PRs should be merged.** Merging a v4 one no-ops-or-conflicts;
merging a v3 one regresses `main`. Correct disposition: **close as superseded**.

## Genuine fixes hidden in the same batch — do NOT bulk-close

The `dazzling-edison` prefix is a batch label, not a topic. Four PRs in it are real,
unrelated fixes and must be judged individually:

| PR | What it is | State | Note |
|----|-----------|-------|------|
| `#631` | test: guard `knowledge_dir` default | **green**, `blocked` | Clean 3-line test; only gated by protected-`main` approval. Best merge candidate. |
| `#625` | ci: dependabot major-update merge guard | needs check | Real CI hardening. |
| `#622` | mcp: request summary + `base_url` type guard (`#389` review) | needs check | Real fix. |
| `#624` | `firstNonNull` null-vs-truthy check (CodeRabbit) | **red**, large | Title is a 1-liner but the PR carries 430/-137 across 5 files + a stale failing Vercel deploy. Needs rework before it's mergeable. |

## Blockers that make this run terminal (human-gated)

1. **Protected `main` requires approval.** Every green candidate (e.g. `#631`) reports
   `mergeable_state: blocked` — no approving review. This session will **not** self-approve
   to bypass the human gate.
2. **CodeRabbit is out of prepaid credits** — commit status reads
   *"Prepaid credits exhausted — enable usage-based reviews."* The runbook's automated
   CodeRabbit review loop (step 4) **cannot run** until billing is re-enabled.
3. **Bulk-close is unsafe to automate** — the build-churn PRs and the 4 genuine fixes are
   interleaved on the same branch prefix, so a blind sweep would discard real work.

## Housekeeping

Six superseded triage-doc PRs from this routine's own prior runs are still open and
should be closed: `#567`, `#576`, `#583`, `#584`, `#589`, `#590`.

## Disposition

| PR set | Action | Terminal state |
|--------|--------|----------------|
| Build-churn batch (`#613`–`#621`, `#623`, `#626`–`#630`, `#632`) | Diagnosed redundant/regressive vs `main`; recommend close | **DEFERRED (superseded — owner close)** |
| `#631` | Verified green; blocked on protected-`main` approval | **HALTED (awaiting_merge_approval)** |
| `#622`, `#625` | Real fixes; need review pass (CodeRabbit down) | **HALTED (awaiting_review)** |
| `#624` | Red + oversized vs its stated 1-line intent; needs rework | **HALTED (ci_failing / needs_rework)** |
| Prior triage docs `#567`,`#576`,`#583`,`#584`,`#589`,`#590` | Superseded; content on `main` | **DEFERRED (redundant — owner close)** |
| ~24 drafts / `[WIP]` | Scope gate | **DEFERRED** |

## Staged owner commands

```bash
# 1. Close the redundant/regressive web-build batch (does NOT touch the 4 real fixes):
for n in 613 614 615 616 617 618 619 620 621 623 626 627 628 629 630 632; do \
  gh pr close $n -c "Superseded: main already carries the Tailwind v4 PostCSS + OTel + @sentry/nextjs@^10.63.0 fix and is CI-green (run-11 triage)."; done

# 2. Close stale self-generated triage-doc PRs:
for n in 567 576 583 584 589 590; do gh pr close $n -c "Superseded triage doc; content already on main."; done

# 3. Merge the clean green fix once you approve it:
gh pr review 631 --approve && gh pr merge 631 --squash --delete-branch

# 4. Re-enable CodeRabbit usage-based reviews, then re-run the runbook against #622/#625/#624.
```

## Is more work needed?

**No autonomous engineering work remains this cycle — converged to a human gate.**
`main` is CI-green and already contains the fix the batch was chasing, so nothing open can
improve `main` without a human decision:

- merges are blocked by protected-`main` approval (this session won't self-approve),
- the correct disposition for the bulk (close) is owner-reserved and unsafe to automate
  because real fixes are interleaved,
- the automated review path (CodeRabbit) is out of credits.

Re-run when the owner approves `#631`, closes the superseded batch, or re-enables
CodeRabbit.
