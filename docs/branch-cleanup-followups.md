# Branch Cleanup — Findings & Follow-ups

Companion to [`branch-cleanup-assessment.md`](./branch-cleanup-assessment.md). Records findings surfaced during the assessment and the planned action for each, so nothing is silently dropped.

## Findings

### F1 — "Committed Grok API key" — ❌ does NOT affect `main` (no action on main)
PR #220's body flags a hardcoded Grok key as an `os.environ.get(...)` default in `src/agents/mcp_tools/tri_model_consensus_tool.py`. **Verified against current `main`:** line 79 is `self.grok_api_key = os.environ.get("GROK_API_KEY")` — no default, clean. The finding is specific to the **#220 branch** (`claude/confident-roentgen-18e955`), not `main`.
- **Action:** none on `main`. Flag for reviewers of #220 to confirm the key is removed before merge. (Out of scope for the branch-cleanup PR.)

### F2 — "Non-hermetic test (live Gemini call)" — ❌ does NOT affect `main` (no action on main)
PR #215's body flags `tests/unit/test_code_generator.py` making a live Gemini call. **Verified against current `main`:** the test imports only `ProjectCodeGenerator` (the lightweight, offline generator), no `genai`/`gemini` import, no module-scope provider calls — hermetic.
- **Action:** none on `main`. If a live-calling variant lands via #215, mock the provider there.

### F3 — Stripe placeholder defaults — ⚠️ benign, low priority
`src/youtube_extension/backend/ai_code_generator.py:939-940` use `os.environ.get("STRIPE_SECRET_KEY", "sk_test_...")` / `"pk_test_..."` as defaults. These are literal placeholders (dots, not real keys) injected into *generated* project scaffolding, not live credentials.
- **Action:** optional hardening — emit an empty string / raise if unset rather than a placeholder, so generated apps fail loud instead of shipping a dud key. Not blocking.

### F4 — `main` history was rewritten — ✅ documented
A secret-purge force-push orphaned older branches and breaks naive git diff/merge-tree signals.
- **Action:** done — captured in `CLAUDE.md` (Repo Hygiene) and the `branch-cleanup` skill.

## Pending execution

> ✅ **SAFE batch executed (2026-06-02).** The 28 CLOSE-SAFE branches were deleted
> via the `Branch Cleanup` GitHub Actions workflow (server-side, where the token
> has `contents: write` — the web sandbox itself cannot delete refs). Verified:
> `deleted=28, still_present=0`; 28 `archive/*` tags pushed + SHAs in
> [`branch-cleanup-recovery-refs.txt`](./branch-cleanup-recovery-refs.txt) for
> reversibility. Remote went 67 → 40 branches.
>
> Note: `claude/modernize-stale-model-ids` (PR #215) also disappeared, but that
> was an independent **merge** (merged 2026-06-01 19:00, branch auto-deleted) —
> not part of this batch.

| Item | State | Plan |
|---|---|---|
| Delete **28 CLOSE-SAFE** branches | ✅ done (2026-06-02) | executed via Actions workflow; reversible |
| Delete **30 CLOSE-STALE** branches | ✅ done (2026-06-02) | executed via Actions workflow; reversible |
| Triage **3 REVIEW** branches | ✅ done (2026-06-02) | closed the 2 superseded (`copilot/improve-documentation`, `fix/unified-ai-sdk-real-providers-154`); **kept** `v0/ai-system-architecture-ac4e7c39` (gained open PR #226) |
| Merge PR #222 | open (draft) | review + un-draft |

Remote went **67 → 8 branches**. Survivors: `main`, this PR branch, and 6 open-PR
branches (#216/#217/#220/#221/#225/#226). **60 archive tags** preserve every deleted ref.

### ⚠️ Incident — PR #227 collateral (contained, no data loss)
`v0/groupthinking-86bedbf8` was STALE at the session-start snapshot, but **open PR #227
was opened against it at 09:19** (after the snapshot, before the STALE delete at 09:24),
so the hardcoded list deleted a now-active branch. **PR #227 is still open, head SHA
`99df2ac` intact** (preserved by the PR + the `archive/v0/groupthinking-86bedbf8` tag).

- **Restore (user action required):** the Actions token cannot recreate this ref because
  the commit contains `.github/workflows/*` files (GitHub blocks workflow-bearing pushes
  without the `workflows` scope). Restore via **PR #227 → "Restore branch"**, or locally:
  `git push origin archive/v0/groupthinking-86bedbf8:refs/heads/v0/groupthinking-86bedbf8`.
- **Root-cause fix (shipped):** `branch-cleanup-delete.sh` now does a **live open-PR check**
  per branch and refuses to delete any branch that heads an open PR — so a snapshot that
  goes stale can no longer cause this.

All deletions are reversible: `git push origin <sha>:refs/heads/<branch>` (SHAs in the recovery file), or `git push origin archive/<branch>:refs/heads/<branch>` (60 tags on remote).
