# Root Diff Artifact Ledger — 2026-08-25

Eleven raw PR export diffs (`701.diff` … `756.diff`) previously sat loose in the
repository root with nothing tracking whether they were pending patches or dead
weight. They were removed in commit `b24f3aa9` ("fix: keep API v1 router loading
when google-genai is absent", #989). This ledger records the file-by-file
verification that every artifact's post-state already exists in the current
tree, so nobody re-applies an already-landed patch. See GitHub issue #802 for
the originating triage plan.

## Phase 1: Verify applied status of all eleven artifacts ✅ COMPLETE

**Issue:** No document tracked the numeric root diffs by number, so their
"applied vs pending" status was ambiguous after removal.

**Solution:** Each diff's distinctive post-state (added lines) was checked
against the corresponding target file(s) on `main`. All eleven are applied.

| Diff | Target file(s) | Verified evidence | Status |
| --- | --- | --- | --- |
| `701.diff` | `apps/web/src/components/InteractiveTranscript.tsx` | `SegmentRow` wrapped in `React.memo` | ✅ applied, artifact removed |
| `710.diff` | `src/unified_ai_sdk/rate_limiter.py` | `class TokenBucket` rate limiter present | ✅ applied, artifact removed |
| `711.diff` | `src/youtube_extension/backend/static/index.html` | `sanitizeUrl` helper and DOM-API (`textContent`) result rendering | ✅ applied, artifact removed |
| `720.diff` | `.jules/bolt.md`, `src/agents/mcp_tools/tri_model_consensus_tool.py` | `httpx.AsyncClient` replaces synchronous `requests` in `_query_grok`; bolt.md learning entry restored by this change (it was lost when the artifact was deleted before the entry was merged) | ✅ applied, artifact removed |
| `722.diff` | `src/agents/multi_llm_video_processor.py` | `aiohttp.ClientSession` used for provider calls | ✅ applied, artifact removed |
| `723.diff` | `src/agents/process_video_with_mcp.py` | transcript fetches run via `loop.run_in_executor` + `asyncio.as_completed` | ✅ applied, artifact removed |
| `725.diff` | `src/agents/real_mode_guard.py` | split-string marker guard (`"# T" "ODO: Real implementation"`) present | ✅ applied, artifact removed |
| `745.diff` | `.github/workflows/ci.yml`, `config/agent_network.json`, `skills-lock.json`, `src/agents/mcp_ecosystem_coordinator.py`, `src/skills/*/main.py`, `tests/test_skills_integration.py` | CI `guards` job (conflict-marker/syntax gate) present; `trigger_events` renamed to `<domain>.<entity>.<action>` form (`youtube.video.published` etc.) with no old-style names remaining | ✅ applied, artifact removed |
| `746.diff` | `apps/web/src/components/dashboard/panels.tsx` | `search-video` labelled input present | ✅ applied, artifact removed |
| `749.diff` | `.jules/bolt.md`, `src/youtube_extension/backend/services/database_optimizer.py` | `asyncio.gather` batch execution present; bolt.md entry ("Optimize batch query execution") already present | ✅ applied, artifact removed |
| `756.diff` | `infrastructure/docker/docker-compose.full.yml`, `pyproject.toml`, `requirements.txt`, `src/youtube_extension/orchestrator/main.py`, `tests/unit/test_orchestrator_consumer.py` | orchestrator service (`python -m youtube_extension.orchestrator.main`) in compose; `redis>=5.0.0` dependency; orchestrator module and consumer test exist | ✅ applied, artifact removed |

## Phase 2: Restore the lost `720.diff` learning entry ✅ COMPLETE

**Issue:** `720.diff` carried a `.jules/bolt.md` learning entry ("2024-05-15 -
Prevent Event Loop Blocking in Third-Party Requests"). The code half of the
diff landed, but the bolt.md entry never did — deleting the artifact in
`b24f3aa9` was the only remaining record of it.

**Solution:** The entry was restored verbatim to `.jules/bolt.md` alongside
this ledger. No other bolt.md entries were affected.

## Disposition rules going forward

- Root-level `*.diff` files are export artifacts, not source. Do not commit
  them; apply the change on a branch and open a PR instead.
- The artifacts must not be recreated. If an old diff needs consulting, read it
  from history: `git show b24f3aa9^:<n>.diff`.
