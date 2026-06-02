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
| Delete **30 CLOSE-STALE** branches | ⏸ not authorized | Actions → Branch Cleanup → `batch: stale, dry_run: false` |
| Triage **3 REVIEW** branches | needs glance | `v0/ai-system-architecture-ac4e7c39` (5d, recent — likely keep/PR), `fix/unified-ai-sdk-real-providers-154` (superseded by model-migration PRs → close), `copilot/improve-documentation` (docs, won't merge clean → close) |
| Merge PR #222 | open (draft) | review + un-draft |

All deletions are reversible: `git push origin <sha>:refs/heads/<branch>` (SHAs in the recovery file), or `git push origin archive/<branch>:refs/heads/<branch>` (tags on remote).
