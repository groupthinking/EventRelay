# PR Remediation Run — 2026-08-01

**Runbook:** PR Remediation & Publish Runbook (action-forcing, RASOR).
**Surface:** GitHub MCP, authenticated as `groupthinking` (repo owner, write+merge capable).
**Generated:** 2026-08-01T21:00Z (scheduled/unattended run — no human watching live).

---

## Headline

**30 open PRs. Every one is a draft.** Under the runbook's SCOPE GATE (step 2 — a
draft or `hold`/`do-not-merge` PR is `DEFERRED`), all 30 defer before any
remediation, CodeRabbit, red-team, CI, or publish step runs. **No PR is eligible for
autonomous merge in this run.**

The bottleneck is **entirely human**, and it is structural, not per-PR:

1. Draft status is an explicit "not ready to merge" signal from the author. Merging
   any of these requires first marking it *Ready for review* — an author decision an
   unattended scheduled run must not make on 30 PRs at once.
2. The base branch is `main` (protected). The runbook's PUBLISH GATE is
   *human-by-default*; `auto_merge_policy` is `label:automerge` and **no open PR
   carries an `automerge` label**. So even if a PR were un-drafted and green, it would
   land at `HALTED(awaiting_merge_approval)`, not merge.

**Self-perpetuating loop worth flagging:** this routine has fired repeatedly since
2026-07-03 (`docs/triage/pr-remediation-*.md` — run2…run10, 07-17, and 4 open triage
PRs: #1044, #1059, #1076, #1077). Each run adds a triage doc + draft PR that then
stays drafted because merging is human-gated. The backlog grows every run. The doc
you are reading is itself another instance of that pattern — see *Recommendation*.

---

## What was verified this run

- Listed all open PRs (oldest-first). All 30 are `draft: true`.
- Spot-checked CI on the newest substantive security PR **#1118** (proxy-credential
  leak fix): **all 4 checks success** (Vercel ×2, CodeRabbit, truth-gate). It is
  green and blocked *only* by draft status + human merge approval.
- Per-PR CI for the remaining 29 was **not** polled: it does not change any terminal
  state, since all 30 stop at the scope gate regardless of CI.

---

## Terminal states (Output Contract, oldest-first)

| PR | Title | Age (created) | Draft | Action taken | Terminal state |
|----|-------|---------------|-------|--------------|----------------|
| #734 | fix(security): pin cloud callbacks vs DNS rebinding | 07-12 | ✅ | scope gate | DEFERRED(draft) |
| #810 | fix(security): sanitize API log injection (CWE-117) | 07-17 | ✅ | scope gate | DEFERRED(draft) |
| #869 | fix: harden API-cost webhook outbox retries | 07-18 | ✅ | scope gate | DEFERRED(draft) |
| #903 | fix(auth): restore Google OAuth in Vercel prod | 07-20 | ✅ | scope gate | DEFERRED(draft) |
| #906 | fix(ci): remediate PR #877 rollout gaps | 07-21 | ✅ | scope gate | DEFERRED(draft) |
| #961 | [DRAFT EVIDENCE] duplicate dashboard a11y proposal | 07-23 | ✅ | labeled `duplicate` | DEFERRED(draft/duplicate) |
| #987 | [DRAFT EVIDENCE] unbound CI + module-shadowing | 07-25 | ✅ | scope gate | DEFERRED(draft) |
| #995 | perf(mcp): reuse pooled aiohttp session | 07-25 | ✅ | labeled `duplicate` | DEFERRED(draft/duplicate) |
| #996 | fix(mcp): actually reuse pooled aiohttp session | 07-25 | ✅ | labeled `duplicate` | DEFERRED(draft/duplicate) |
| #1000 | build(deps): bump actions/checkout 4.2.2→7.0.1 | 07-25 | ✅ | dependabot | DEFERRED(draft) |
| #1003 | build(deps): bump actions/github-script 8→9 | 07-25 | ✅ | dependabot | DEFERRED(draft) |
| #1020 | perf: optimize call stack ops + string allocs | 07-26 | ✅ | scope gate | DEFERRED(draft) |
| #1040 | fix(mcp): green up MCPOrchestrator E2E tests | 07-27 | ✅ | labeled `duplicate` | DEFERRED(draft/duplicate) |
| #1043 | perf(web): optimize viewBox computation | 07-27 | ✅ | labeled `duplicate` | DEFERRED(draft/duplicate) |
| #1044 | docs(triage): PR remediation run 2026-07-27 | 07-27 | ✅ | this routine's own doc | DEFERRED(draft/triage-doc) |
| #1045 | 🎨 Palette: keyboard focus-visible styling | 07-27 | ✅ | labeled `duplicate` | DEFERRED(draft/duplicate) |
| #1047 | ci: suppress failure issues on no-op runs | 07-27 | ✅ | scope gate | DEFERRED(draft) |
| #1049 | fix(a11y): dashboard focus contrast + coverage | 07-27 | ✅ | scope gate | DEFERRED(draft) |
| #1050 | Configure agentic no-op comment suppression | 07-27 | ✅ | labeled `duplicate` | DEFERRED(draft/duplicate) |
| #1052 | fix: allow awmg-mcpg gateway in firewalls | 07-27 | ✅ | scope gate | DEFERRED(draft) |
| #1059 | docs(triage): PR remediation run 2026-07-28 | 07-28 | ✅ | this routine's own doc | DEFERRED(draft/triage-doc) |
| #1064 | docs(runbook): Google OAuth 403 remediation | 07-28 | ✅ | labeled `duplicate` | DEFERRED(draft/duplicate) |
| #1075 | fix(pipeline): preserve transcript on timeout | 07-29 | ✅ | scope gate | DEFERRED(draft) |
| #1076 | docs(triage): PR remediation run 2026-07-29 | 07-29 | ✅ | this routine's own doc | DEFERRED(draft/triage-doc) |
| #1077 | docs(triage): run 2026-07-29 + CWE-209 canonical | 07-29 | ✅ | this routine's own doc | DEFERRED(draft/triage-doc) |
| #1080 | perf(ci): replace Math.max spread anti-pattern | 07-29 | ✅ | scope gate | DEFERRED(draft) |
| #1114 | fix(deps): realign apps/web lockfile | 07-30 | ✅ | scope gate | DEFERRED(draft) |
| #1117 | fix(deps): raise brace-expansion override floors | 07-30 | ✅ | scope gate | DEFERRED(draft) |
| #1118 | fix(security): stop proxy credential leakage | 07-31 | ✅ | CI verified green | DEFERRED(draft) — merge-ready if un-drafted |
| #1119 | test(web): billing chat gating asserts real behaviour | 07-31 | ✅ | scope gate | DEFERRED(draft) |

**Terminal-state tally:** 30 × `DEFERRED(draft)`. 0 `MERGED`. 0 `HALTED`
(nothing reached a human-gate mid-flow — they all defer at the scope gate).

---

## Grouping for human action

**A. Ready or near-ready — un-draft + review to merge (highest value):**
- #1118 fix(security): proxy credential leakage — **CI green now**, security fix.
- #734 / #810 — security fixes (DNS rebinding, log injection).
- #869 — high-priority bug (webhook outbox retries).
- #1075 — pipeline-critical bug (transcript preservation).

**B. Dependency bumps — low-risk, batchable once un-drafted:**
- #1000 actions/checkout, #1003 actions/github-script, #1114 lockfile, #1117 brace-expansion.

**C. Labeled `duplicate` — close candidates (8):**
- #961, #995, #996, #1040, #1043, #1045, #1050, #1064.
  (#995 vs #996 are the same aiohttp-pooling fix; keep one.)

**D. This routine's own accumulating triage/doc PRs — consolidate or close (4):**
- #1044, #1059, #1076, #1077.

---

## Recommendation (why this run does not merge anything)

Per the runbook: *"'Take action' means automate the toil up to the irreversible step —
not bypass human sign-off on it."* Merging 30 drafts to protected `main` in an
unattended run — after first overriding each author's explicit draft designation — is
exactly the irreversible, human-owned step the PUBLISH GATE reserves. So all 30 are
correctly `DEFERRED`, and this run stops short of merging.

Concrete asks for a human (staged commands, none executed):

1. **Drain the duplicate + stale-triage backlog (12 PRs)** so the signal-to-noise of
   the open list recovers: close C (#961, #995, #996, #1040, #1043, #1045, #1050,
   #1064) and D (#1044, #1059, #1076, #1077).
2. **Fast-track group A** (5 security/bug PRs): mark Ready → review → merge. #1118 is
   already green.
3. **Decide the loop's future.** This routine keeps emitting draft PRs that never
   merge. Either (a) add an `automerge` label + `auto_merge_policy: label:automerge`
   convention so green low-risk PRs can land, or (b) reduce this routine's cadence /
   pause it until the backlog is drained — otherwise every firing grows the pile.

*Nothing here was merged, closed, or un-drafted automatically — those are human
decisions, surfaced for sign-off.*
