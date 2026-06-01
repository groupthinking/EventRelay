# EventRelay — Empirical Proof-of-Concept: 10 AI / Workflow-Automation Videos

**Date:** 2026-06-01
**Environment:** Claude Code on the web (ephemeral cloud container), Python 3.11.15
**Goal:** Run 10 real YouTube videos about AI / agent building and business
workflow automation through the EventRelay pipeline and prove, with direct
source evidence, exactly which stages work in this environment and which do
not. No mocked successes, no fabricated transcripts (per `CLAUDE.md`
REAL_MODE_ONLY).

Reproduce with:

```bash
python3 -m venv .poc-venv && . .poc-venv/bin/activate
pip install -e . youtube-transcript-api
python examples/poc_ai_workflow_runner.py    # writes examples/poc_results.json
```

---

## 1. The corpus (10 real, web-sourced URLs)

Collected via web search on 2026-06-01. Full list in
`examples/poc_video_urls.txt`.

| # | Video ID | Title |
|---|----------|-------|
| 1 | `mjkecNwp1X0` | ChatGPT Agent Builder Full Tutorial: Building AI Agents in 2025 |
| 2 | `rfonp8KiIso` | How to Build AI Agents Using Make.com (FREE COURSE 2025) |
| 3 | `ZiBLRw-_d7I` | AI Agents Full Course 2025 (Simplilearn) |
| 4 | `geR9PeCuHK4` | How to Build AI Agents with n8n in 2025! (Full Course) |
| 5 | `upblQZigz0U` | Agentic AI Full Course 2025 (Edureka) |
| 6 | `ftBWgcwvEk4` | 8 Hour AI Agents Course in 30 Minutes (DeepLearning.AI) |
| 7 | `ZbIVOy_GPyQ` | N8N Full Tutorial: Building AI Agents in 2025 |
| 8 | `OhI005_aJkA` | Full Course (Lessons 1-10) AI Agents for Beginners |
| 9 | `HMcBIA835ok` | How To Build AI Agents [Full Course 2025] |
| 10 | `2GZ2SNXWK-c` | N8N FULL COURSE 6 HOURS (Build & Sell AI Automations + Agents) |

---

## 2. Stage-by-stage results (what works / what doesn't)

| Stage | Result | Evidence |
|-------|--------|----------|
| 0. URL collection | ✅ **Works** | 10 real IDs, see table above |
| 1. Transcript capture | ❌ **Blocked (environment)** | `youtube_transcript_api` raised `IpBlocked` / `RequestBlocked` for **10/10**. HTTP trace: `GET youtube.com/watch 302` → `google.com/sorry/index 429` |
| 2. AI event extraction (Gemini) | ⚠️ **Blocked (no key) + bug found** | No `GEMINI_API_KEY`; provider returns a **mock** response. The AI call path was also **broken** (see §3) |
| 3. Event extraction endpoint | ✅ **Works (heuristic)** | `POST /api/v1/events/extract` → **HTTP 200 for 10/10** |
| 4. Agent dispatch endpoint | ✅ **Works** | `POST /api/v1/agents/dispatch` → **HTTP 200 for 10/10**, executions created |

Machine-readable evidence: `examples/poc_results.json`.
Totals: `{"videos": 10, "transcript_ok": 0, "extract_http_200": 10, "dispatch_http_200": 10}`.

### What is *blocked by the environment* (not a code defect)

- **Transcript capture is impossible from this cloud IP.** YouTube/Google
  anti-bot blocks the container IP (`IpBlocked`, escalating to
  `RequestBlocked` after repeated calls), third-party transcript mirrors
  return `403`, and even off-container `WebFetch` is redirected to Google's
  `/sorry` captcha. The pipeline's *first* stage therefore cannot run here
  without a residential/datacenter proxy or a supplied transcript.
- **No AI provider keys** (`GEMINI_API_KEY`, `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY` all empty), so genuine LLM extraction cannot be
  exercised. The pipeline still functions via its deterministic heuristic
  fallback.

### What *works* end-to-end (proven on real input)

- The FastAPI app boots, the v1 router loads, and the
  `events/extract` → `agents/dispatch` chain returns HTTP 200 for all 10
  videos, producing typed events (`action` / `topic`) and queuing agent
  executions (2 per event). Example (video 4, n8n course):
  events `["How to Build AI Agents with n8n in 2025!", "(Full Course)"]`,
  4 executions dispatched.

---

## 3. Bugs found through empirical execution (with fixes)

Running the real code — rather than reading it — surfaced three genuine
defects. Two are fixed in this branch; one is documented.

### Bug A (FIXED): AI event-extraction path was dead code

`src/youtube_extension/backend/api/v1/router.py` called the AI processor with
the **wrong signature and wrong result parsing**:

```python
# before
ai_result = await processor.process(prompt=(... + transcript_text[:8000]))
raw_text  = ai_result if isinstance(ai_result, str) else str(ai_result.get("text", ai_result))
```

But `HybridProcessorService.process(self, input_data, prompt, ...)` *requires*
`input_data`, and returns a `HybridResult` dataclass whose payload is
`.response` (not a dict with `.get("text")`). Every call therefore raised:

```
AI event extraction failed, using heuristic extraction:
HybridProcessorService.process() missing 1 required positional argument: 'input_data'
```

**Impact:** the AI extractor could *never* run — even with a valid Gemini key —
and silently degraded to the heuristic on every request.

**Fix** (`router.py`): pass `input_data`, read `.response`, and — per
REAL_MODE_ONLY — reject mock/empty responses so the fallback is deterministic:

```python
ai_result = await processor.process(input_data=transcript_text[:8000], prompt=(...))
cloud_result = getattr(ai_result, "cloud_result", None)
backend = getattr(cloud_result, "backend", None)
raw_text = (ai_result.response or "") if getattr(ai_result, "success", False) else ""
if not raw_text.strip() or backend == "mock":
    raise RuntimeError("AI extraction unavailable (no real Gemini response)")
```

**Verified:** after the fix the logged fallback reason changed from the
`TypeError` to `AI extraction unavailable (no real Gemini response)` — i.e.
the path is now reachable and would parse a real Gemini response, while still
falling back cleanly when no key is present. Locked by
`tests/unit/test_events_extract_ai_path.py` (3 tests, all passing).

### Bug B (DOCUMENTED): mock AI responses violate REAL_MODE_ONLY

With no key, `HybridProcessorService` logs `Using mock response for Gemini
processing` and returns fabricated text (`backend="mock"`). `CLAUDE.md`
forbids simulated responses in production paths. Bug A's fix now prevents the
*events endpoint* from turning mock output into "extracted events", but the
service-level mock fallback should be gated behind an explicit
test-only flag for production builds (tracked, not changed here to avoid
breaking existing tests that rely on it).

### Bug C (DOCUMENTED): `src.`-prefixed absolute imports break installed-package launch

15 backend modules (including `backend/api/v1/router.py`) use
`from src.youtube_extension...`. The package installs as `youtube_extension`
(src-layout), so importing `youtube_extension.main` as an installed package
loads `main` but the **v1 router subtree fails** with `No module named 'src'`
and every `/api/v1/*` route 404s — unless the repo root is on `sys.path` (as
the documented `uvicorn src.youtube_extension.main:app` launch happens to
ensure). Recommendation: convert these to relative/`youtube_extension.`
imports for launch portability.

---

## 4. Bottom line

- **Provably working here:** URL ingestion, FastAPI app + v1 router, heuristic
  event extraction, and agent dispatch — HTTP 200 across all 10 videos.
- **Blocked by environment (not code):** YouTube transcript capture (cloud-IP
  ban) and real LLM extraction (no API keys).
- **Fixed this branch:** the AI event-extraction path (Bug A), now covered by
  regression tests.
- **To run the *full* AI pipeline:** supply `GEMINI_API_KEY` (or another
  provider key) **and** either run from an IP YouTube does not block or feed
  transcripts via the `transcript` / `transcript_text` request fields, which
  the endpoints already accept.
