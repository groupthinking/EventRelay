# PR Remediation Run — 2026-08-01

**Runbook:** PR Remediation & Publish Runbook (action-forcing, RASOR).
**Surface:** GitHub MCP, authenticated as `groupthinking` (repo owner, write+merge capable).
**Generated:** 2026-08-01T21:00Z (scheduled/unattended run — no human watching live).
**Revised:** 2026-08-02 after owner review of PR #1177 — see *Corrections from review* below.

---

## Corrections from review (applied 2026-08-02)

Owner review on #1177 caught two factual errors in the first draft; both are fixed inline below and summarized here:

1. **#1118 is NOT green.** Current state is `mergeable=CONFLICTING`, `mergeStateStatus=DIRTY`, `draft=true`. It needs a rebase before anything, and it's under security review — the proxy-credential-leak it fixes may already be closed on `main`, in which case it should be **closed as obsolete, not rebased**. It is *not* fast-trackable.
2. **"Green/red" is not a usable signal for most of this backlog.** At the time these PRs last ran CI, *every* PR in the repo was red for two content-independent reasons: (a) `Agent completion enforcement` → `missing_trusted_publication` (empty allowlists in `.github/agent-lock/trusted-publishers.json` under `fail_closed`), and (b) `gitleaks (working tree)` false-positive on `uv.lock:5129`. Uniform red carries no information, so "no distinguishable blocker" must not be read as "safe" — that misread is what run #1128 made for #999–#1008, where #999/#1003 actually fail `build` and #1000 fails `test`/`Coverage`/`truth-gate`. Both systemic gates are now fixed on `main` (#1151, #1142), **but existing PRs won't reflect that until rebased** (checks don't re-run retroactively). **Rule: green/red on any PR not updated since 2026-08-02 is not a usable input. Rank on `build`/`test`/`Coverage`/`validate-gh-aw`, and require ≥1 *green required* check before classifying anything as fast-trackable.**

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
- Spot-checked the *combined commit status* of **#1118** (proxy-credential leak fix):
  the 4 posted statuses (Vercel ×2, CodeRabbit, truth-gate) were success. **This was
  misread as "green" in the first draft — it is not.** Combined status ≠ required
  checks ≠ mergeability. Per owner review, #1118 is `mergeable=CONFLICTING` /
  `mergeStateStatus=DIRTY`: it needs a rebase, is under security review, and may be
  closeable as obsolete. It is **not** merge-ready.
- Per-PR *required*-check state (`build`/`test`/`Coverage`/`validate-gh-aw`) for the
  rest was **not** polled and, per the *Corrections* note, would be stale anyway for
  any PR not rebased since the 2026-08-02 gate fixes. It does not change any terminal
  state here, since all 30 stop at the scope gate regardless of CI.

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
| #1118 | fix(security): stop proxy credential leakage | 07-31 | ✅ | scope gate | DEFERRED(draft) — **CONFLICTING/DIRTY, needs rebase; verify vuln still open on `main` or close as obsolete** |
| #1119 | test(web): billing chat gating asserts real behaviour | 07-31 | ✅ | scope gate | DEFERRED(draft) |

**Terminal-state tally:** 30 × `DEFERRED(draft)`. 0 `MERGED`. 0 `HALTED`
(nothing reached a human-gate mid-flow — they all defer at the scope gate).

---

## Grouping for human action

**A. Candidates to *evaluate* for merge — NOT a fast-track list (corrected):**
These are the substantive security/bug PRs by topic, but *none* is classified as
fast-trackable here, because their current CI is not a usable signal (see *Corrections*).
Before any of these is proposed for merge it must be **rebased onto current `main`**
(to pick up the #1151/#1142 gate fixes) and then show **≥1 green required check**
(`build`/`test`/`Coverage`/`validate-gh-aw`):
- #1118 proxy credential leak — **blocked first on CONFLICTING/DIRTY + obsolescence check** (may be closed, not merged).
- #734 / #810 — security (DNS rebinding, log injection) — rebase, then verify required checks.
- #869 — high-priority bug (webhook outbox retries) — rebase, then verify required checks.
- #1075 — pipeline-critical bug (transcript preservation) — rebase, then verify required checks.

Do **not** infer "safe" from the absence of a distinguishable red check: until rebased,
these were uniformly red for the two content-independent gate reasons in *Corrections*,
which is exactly the misread that broke run #1128.

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

The backlog is a **generation-rate problem, not a review-capacity one.** Per owner
review, **46 of 50 open PRs are drafts; only 4 are actually proposed for merge.**
Automation opens drafts faster than anything converts them, and each triage run adds
one more PR to the pile it reports on (#1044, #1059, #1128, and this one are all
triage-run artifacts). A report that must be reviewed and merged to be *read* is
self-defeating when the thing being reported on is an unreviewable backlog.

Concrete asks for a human (none executed autonomously):

1. **Change where this routine writes.** Emit the triage report to a GitHub **issue or
   a workflow-run summary**, not a PR. This stops the loop from adding to its own pile.
2. **Pause / slow the routine until the backlog is drained** (owner's preferred
   option). `automerge`-based auto-merge only becomes safe *after* the two systemic
   gates (#1151, #1142) are confirmed clearing on **rebased** PRs — otherwise it
   automates the exact "uniform-red = safe" misread that broke run #1128.
3. **Drain the backlog:** close the `duplicate`-labeled set (#961, #995, #996, #1040,
   #1043, #1045, #1050, #1064) and the superseded triage snapshots (#1044, #1059 are
   red-check-era artifacts; #1076, #1077 too). *Left to the owner — this run does not
   close others' or prior PRs.*
4. **Evaluate the security/bug PRs individually** (group A) only after rebasing each
   and confirming ≥1 green required check. #1118 specifically may be **closed as
   obsolete** rather than merged — verify the vuln is still open on `main` first.

*Nothing here was merged, closed, or un-drafted automatically — those are human
decisions, surfaced for sign-off. This revision incorporates owner review of #1177
(2026-08-02); it does not act on the review's "can be closed" suggestion for #1044/#1059,
which remains the owner's call.*
