# GATE-4 Security High Cluster Report

**When:** 2026-07-10T18:05–18:10Z UTC
**Branch:** `fix/gate4-security-hardening` (from `e70aa66a`)
**Baseline:** `eventrelay-audit-report.md` findings #1–4, #7

---

## Already on main before this gate

| Control | Status on `main` |
|---------|------------------|
| Pydantic YouTube host allowlist on `TranscriptActionRequest` / `ChatRequest` | Present |
| yt-dlp `cmd.append("--")` in `robust.py` | Present |
| Veo `/api/video/generate` Pro gate (402 free) | Present + **live 402** |

---

## Gaps found live (production, pre-deploy of this branch)

| Probe | HTTP | Issue |
|-------|------|--------|
| `POST /api/pipeline` url=`http://169.254.169.254/aaaaaaaaaaa` | **200** partial | **BFF did not reject** non-YouTube; fell into degraded paths |
| `POST /api/pipeline` url=`--config-locations=/aaaaaaaaaaa` | **200** partial | Same — Gemini path still ran |
| `POST /api/video/generate` unauth | **402** | Pro gate works live |
| Valid YouTube async | **200** job pending | Happy path still works |

**Conclusion:** Backend model validators alone are insufficient while the public Next.js BFF accepts arbitrary `url` and may not hit the Python validators on all code paths.

---

## Changes in this branch

| ID | Change | Files |
|----|--------|--------|
| G4-SSRF-01 | **BFF allowlist** `isAllowedYoutubeUrl` on pipeline + video routes; shared helper | `apps/web/src/lib/video-url-request.ts`, `pipeline/route.ts`, `video/route.ts` |
| G4-SSRF-01 tests | Vitest + pytest SSRF/dash rejection | `video-url-request.test.ts`, `test_api_models.py` |
| G4-YTDLP-01 | `--` before URL on Whisper/yt-dlp path | `enhanced_video_processor.py` (robust.py already fixed) |
| G4-VEO-01 | Already Pro-gated; **rate limit fail-closed** in production without Redis | `video/generate/route.ts` |
| G4-PROXY-01 | Production AI rate limit **fail-closed** without Redis (emergency: `UVAI_RATE_LIMIT_FAIL_OPEN=1`) | `proxy.ts` |
| G4-REG-01 | Unit tests green locally | vitest 26; pytest model tests 11 |

---

## Test evidence

```text
vitest: video-url-request + video-generate + pipeline-route → 26 passed
pytest TestTranscriptActionRequest + TestChatRequestVideoUrl → 11 passed (--no-cov)
```

Live production will only gain BFF 400 rejects **after this branch is merged and deployed**.

---

## Remaining residual risk

| Item | Notes |
|------|--------|
| Deploy lag | Production still runs old BFF until merge + Vercel deploy |
| Other yt-dlp YoutubeDL Python API sites | Use library API not argv; still rely on URL validators at entry |
| Auth fail-open for pages | NextAuth still broken (GATE-3); separate from this cluster |
| `UVAI_RATE_LIMIT_FAIL_OPEN=1` | Emergency only — do not set in prod |

---

## GATE-4 exit

| Criterion | Status |
|-----------|--------|
| High #1–3 SSRF/injection mitigations in code | **YES** (backend + BFF) |
| High #4 Veo ungated | **Mitigated** (Pro 402 live + fail-closed RL) |
| Fail-closed rate limit | **YES** (generate + proxy AI) |
| Tests | **YES** local |
| Merged to main + prod deploy | **NO** — needs PR + deploy |

**GATE-4 implementation complete on branch.** Ship via PR, then re-probe production for 400 on evil URLs.
