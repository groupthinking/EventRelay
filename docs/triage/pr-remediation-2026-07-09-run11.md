# PR Remediation & Publish — Run 11 (2026-07-09)

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge). CodeRabbit handle: `@coderabbitai`.
Merge method: `squash`. Auto-merge policy: **unset → `never`** (publish gate is human).

## Scan

**52 open PRs.** Composition:

- **6 stale prior-run triage-doc PRs** — `#567, #576, #583, #584, #589, #590`. Each is a
  `docs(triage): PR remediation run N` PR whose content has since landed on `main` (run 10
  is `e2916b9`) or been superseded by a later run. → **DEFERRED (redundant; close).**
- **16 web-build-churn PRs** — the Tailwind/OTel/Sentry cluster. All obsolete (see below).
- **7 drafts** — `#634, #635, #636, #637, #639, #642, #643` (`google-labs-jules[bot]`).
- **23 other non-draft PRs** — a mix of genuine green merge candidates and stale `[WIP]`
  duplicates.

Nothing was auto-merged: the runbook **PUBLISH GATE is human by default** and no
`automerge` policy is configured, so every merge candidate is **HALTED
(awaiting_merge_approval)** with the exact `squash`-merge command staged. No PRs were
closed unilaterally — closes are staged for the owner.

## Headline finding — the web-build cluster is dead weight

`main` already ships the fixed web build:

- **Tailwind v4** — `tailwindcss ^4.3.1` + `@tailwindcss/postcss ^4.3.2`, with
  `apps/web/postcss.config.js` correctly using the `@tailwindcss/postcss` plugin.
- **Sentry** — `@sentry/nextjs ^10.63.0` (current latest).
- **OpenTelemetry** — `@opentelemetry/core ^2.9.0`, `@opentelemetry/instrumentation ^0.220.0`,
  and aligned peers.

Every PR in the cluster branches off a June-era base whose `package.json` still reads the
old pins, so relative to today's `main` each one is either **contradictory** or a **no-op**:

| Sub-group | PRs | Why redundant |
|-----------|-----|---------------|
| Revert Tailwind → **v3** | `#613, #616, #623, #629` | Contradicts `main`, which is intentionally on v4 |
| Migrate Tailwind → **v4** | `#617, #618, #626, #627, #628, #630, #632` | Duplicates the v4 config `main` already has |
| Pin **OTel** to older versions | `#614, #615, #621` | Pins *older* than `main`'s (`^2.9.0` / `^0.220.0`); Vercel red |
| Bare "merge main into branch" | `#619` | No unique diff to land |
| Mislabeled React 19 bump | `#620` | Title says "restore lock integrity"; diff is React 18→19 on a stale base |

`#629, #630, #632` are additionally `dirty` (merge conflicts). **Recommendation: close all 16
as superseded.** If any live OTel breakage remains on `main`, cherry-pick only the
`@opentelemetry/*` lines from `#626`/`#632` rather than merging the PRs.

## Security flag — promote draft `#636`

`#636` (`🔒 Remove hardcoded Looker embed secrets`, `jules[bot]`, **draft**) removes
hardcoded fallback secrets in the Looker embed service and raises on missing config. Left
in place, those fallbacks could allow forging signed SSO embed URLs — a real multi-tenant
isolation risk. It is a draft, but security-relevant: **recommend a human promote it out of
draft and review/merge**, rather than leaving it in the deferred pile.

## Disposition matrix

### Merge candidates — green, substantive, non-redundant → HALTED(awaiting_merge_approval)

| PR | Author | What it does | CI (real = Vercel) |
|----|--------|--------------|--------------------|
| #541 | Copilot | Fix 27 failing tests + `AgentResult` bug in HybridVisionAgent | ✅ |
| #549 | Copilot | Skills event-contract validator (+704, 41 tests) | ✅ |
| #570 | Copilot | Make Sentry wrapper optional in `next.config` | ✅ |
| #571 | Copilot | Guard E2E PR comments on forked runs | ✅ |
| #605 | groupthinking | Trivy commit-pin fix + broaden YouTube host allowlist | ✅ |
| #606 | groupthinking | Remove fabricated "simulated" MCP responses + dead routes | ✅ |
| #608 | groupthinking | Case-insensitive `_extract_video_id` | ✅ |
| #609 | groupthinking | `x-goog-api-key` header, non-billable health checks | ✅ |
| #612 | groupthinking | Prisma: drop `earlyAccess`; add NextAuth Prisma adapter | ✅ |
| #622 | groupthinking | MCP structural request summary + `base_url` type guard | ✅ |
| #624 | groupthinking | `firstNonNull` null-check (not truthy) — real bugfix | ⚠️ stale-red, verify |
| #625 | groupthinking | Dependabot merge-guard regex matches both major forms | ✅ |
| #631 | groupthinking | Guard `knowledge_dir` default in defaults test | ✅ |
| #633 | groupthinking | Remove commented-out code from `main.py` | ✅ |
| #539 | Copilot | Dockerfile ffmpeg + Node 22 multi-stage | ✅ (verify vs merged #600) |

### Needs human — real review required (not auto-mergeable)

| PR | Author | Why |
|----|--------|-----|
| #596 | groupthinking | `execute_single` + subagent dispatch; Vercel deploy failing |
| #610 | groupthinking | vite→8 / vitest upgrade, 40-file lock churn, Vercel **red** |
| #611 | groupthinking | "finalize audit fix" dev-deps (+5847), Vercel **red**, overlaps #610 |
| #642 | jules[bot] | Perf: eviction/parallel transcription/pool sizing (8 files) — genuine review |
| #636 | jules[bot] | Security (Looker secrets) — **promote from draft** |
| #545 | Copilot | GTM skill registry — verify vs `main`'s just-merged #641 (may be redundant) |
| #544 | Claude | `[WIP]` large unfinished `unified_request` refactor |

### Deferred / close as redundant

| PRs | Reason | Terminal |
|-----|--------|----------|
| #613,#614,#615,#616,#617,#618,#619,#620,#621,#623,#626,#627,#628,#629,#630,#632 | Web-build cluster superseded by `main` | **DEFERRED (close)** |
| #567,#576,#583,#584,#589,#590 | Prior-run triage-doc PRs; content merged/superseded | **DEFERRED (close)** |
| #530,#540,#546 | `[WIP]` duplicates of finished PRs (#365/#539/#545) | **DEFERRED (close)** |
| #634,#635,#637,#639,#643 | `jules[bot]` drafts | **DEFERRED (draft)** |

## Staged commands (owner to run — nothing executed this run)

```bash
# Close the redundant web-build cluster (16):
for n in 613 614 615 616 617 618 619 620 621 623 626 627 628 629 630 632; do
  gh pr close "$n" -c "Superseded by main (already on Tailwind v4 + current OTel/Sentry). See run-11 triage."
done

# Close stale prior-run triage-doc PRs (6):
for n in 567 576 583 584 589 590; do
  gh pr close "$n" -c "Content merged/superseded by later runs. See run-11 triage."
done

# Close WIP duplicates (3):
for n in 530 540 546; do gh pr close "$n" -c "Duplicate of the finished PR; WIP stub. See run-11 triage."; done

# Merge candidates — review then squash-merge (owner sign-off required):
for n in 541 549 570 571 605 606 608 609 612 622 625 631 633; do
  gh pr merge "$n" --squash   # after confirming CI + intent
done
# #624 (verify stale-red first), #539 (verify vs merged #600), #545 (verify vs #641) — review individually.
```

## Terminal states

| Bucket | Count | State |
|--------|-------|-------|
| Merge candidates | 15 | **HALTED(awaiting_merge_approval)** — commands staged |
| Needs human | 7 | **HALTED(needs_review)** — incl. security promote #636 |
| Redundant / stale (close) | 25 | **DEFERRED(redundant)** — close commands staged |
| Drafts | 5 | **DEFERRED(draft)** |

**Convergence:** the automatable work is complete — every open PR is dispositioned and
every next step is staged. All remaining transitions (merge to protected `main`, close,
draft promotion) require the human publish gate. No further unattended progress is possible
until the owner clears this set; re-running before then would only reproduce this matrix.
