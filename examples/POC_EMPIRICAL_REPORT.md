# EventRelay — Empirical Proof-of-Concept: 10 AI / Workflow-Automation Videos

**Date:** 2026-06-01
**Environment:** Claude Code on the web (ephemeral cloud container), Python 3.11.15
**Goal:** Run 10 real YouTube videos about AI / agent building and business
workflow automation through the EventRelay pipeline and prove, with direct
source evidence, exactly which stages work in this environment and which do
not. No mocked successes, no fabricated transcripts (per `CLAUDE.md`
REAL_MODE_ONLY).

Reproduce:

```bash
python3 -m venv .poc-venv && . .poc-venv/bin/activate
pip install -e . youtube-transcript-api
# VERCEL_API_KEY is read from the environment for real AI extraction.
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

Totals from the committed run (`examples/poc_results.json`):
`{"videos": 10, "transcript_ok": 0, "extract_http_200": 10, "dispatch_http_200": 10}`

| Stage | Result | Evidence |
|-------|--------|----------|
| 0. URL collection | ✅ **Works** | 10 real IDs, see table above |
| 1. Transcript capture | ⚠️ **Intermittently blocked** | `IpBlocked`/`RequestBlocked` for 10/10 in the committed run; **a prior run captured video 6 (37,251 chars)**. HTTP trace: `youtube.com/watch 302` → `google.com/sorry 429` |
| 2. AI event extraction | ✅ **Works via Vercel AI Gateway** | **10/10** real Gemini‑2.0‑flash calls through `ai-gateway.vercel.sh` using `VERCEL_API_KEY`; ~$0.001 total |
| 3. Event extraction endpoint | ✅ **Works** | `POST /api/v1/events/extract` → **HTTP 200 for 10/10**, typed events (action/mention/topic/insight) |
| 4. Agent dispatch endpoint | ✅ **Works** | `POST /api/v1/agents/dispatch` → **HTTP 200 for 10/10**, executions created |

### What *works* end-to-end (proven on real input + real LLM)

- The FastAPI app boots, the v1 router loads, and the
  `events/extract` → `agents/dispatch` chain returns HTTP 200 for all 10
  videos.
- **AI extraction is real.** With no direct Gemini/OpenAI key on file, the
  endpoint now routes through the **Vercel AI Gateway** (model
  `google/gemini-2.0-flash`) and returns structured, typed events. Example
  log line:
  `Vercel AI Gateway model=google/gemini-2.0-flash tokens=2847 cost=0.0009144`
  → `Extracted 26 events via Vercel AI Gateway` (run against video 6's real
  37k-char transcript).
- Agent dispatch then queues 2 executions per AI-extracted event.

### What is *blocked by the environment*

- **Transcript capture is unreliable from this cloud IP.** YouTube/Google
  anti-bot blocks the container IP (`IpBlocked` → `RequestBlocked`),
  third-party transcript mirrors return `403`, and off-container `WebFetch`
  is redirected to Google's `/sorry` captcha. One video did get through in a
  prior run, confirming the block is rate/IP-based and intermittent, not a
  code defect. When capture fails the harness falls back to the real,
  web-sourced **title** as downstream input so the rest of the pipeline is
  still exercised on genuine (non-fabricated) text.
- **No direct AI provider keys** (`GEMINI_API_KEY`, `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY` all empty). The Vercel AI Gateway (`VERCEL_API_KEY`)
  bridges this gap, so AI extraction works anyway.

---

## 3. The Vercel AI Gateway provider (new)

`src/youtube_extension/services/ai/vercel_gateway_provider.py` is a
dependency-free (stdlib `urllib`) OpenAI-compatible client for
`https://ai-gateway.vercel.sh/v1`, which routes to 280+ models behind one
API and authenticates with the `VERCEL_API_KEY` already in the environment.
This realizes the multi-provider AI design described in `CLAUDE.md`
("Routes to Gemini, OpenAI, Anthropic, or Grok") even when no direct provider
key is configured.

`extract_events()` asks the model for a strict JSON array of
`{type, title, description, timestamp}` and normalizes the result into the
endpoint's `ExtractedEvent` shape. It is **REAL_MODE_ONLY**: every call is a
real billed invocation, and if `VERCEL_API_KEY` is absent it returns `[]` so
callers fall back to the deterministic heuristic.

Provider selection order in `/api/v1/events/extract`:
1. Direct Gemini (`HybridProcessorService`) — used if a real Gemini response
   is available (mock/empty responses are rejected per REAL_MODE_ONLY).
2. **Vercel AI Gateway** — used when no direct provider response is available
   but `VERCEL_API_KEY` is set. *(This is the path that runs in this
   environment.)*
3. Deterministic heuristic — only when no real AI path is available at all.

---

## 4. Bugs found through empirical execution (with fixes)

### Bug A (FIXED): AI event-extraction path was dead code

`router.py` called the AI processor with the **wrong signature and wrong
result parsing**:

```python
# before
ai_result = await processor.process(prompt=(... + transcript_text[:8000]))
raw_text  = ai_result if isinstance(ai_result, str) else str(ai_result.get("text", ai_result))
```

But `HybridProcessorService.process(self, input_data, prompt, ...)` *requires*
`input_data` and returns a `HybridResult` dataclass whose payload is
`.response` (not a dict). Every call raised:

```
HybridProcessorService.process() missing 1 required positional argument: 'input_data'
```

so the AI extractor could **never** run, silently degrading to the heuristic
on every request. **Fix:** pass `input_data`, read `.response`, and reject
mock/empty responses; then try the Vercel AI Gateway before the heuristic.
Locked by `tests/unit/test_events_extract_ai_path.py` (4 tests, passing).

### Bug B (DOCUMENTED): mock AI responses violate REAL_MODE_ONLY

With no key, `HybridProcessorService` logs `Using mock response for Gemini
processing` and returns fabricated text (`backend="mock"`). `CLAUDE.md`
forbids simulated responses. Bug A's fix prevents the *events endpoint* from
turning mock output into events; the service-level mock fallback should be
gated behind an explicit test-only flag (tracked, not changed here to avoid
breaking existing tests).

### Bug C (DOCUMENTED): `src.`-prefixed absolute imports break installed-package launch

15 backend modules (including `backend/api/v1/router.py`) use
`from src.youtube_extension...`, so importing the installed package loads
`main` but the v1 router subtree fails with `No module named 'src'` and every
`/api/v1/*` route 404s unless the repo root is on `sys.path`. Recommend
converting to relative / `youtube_extension.` imports for portability.

---

## 5. Bottom line

- **Provably working here:** URL ingestion → FastAPI app + v1 router → **real
  AI event extraction (Vercel AI Gateway / Gemini-2.0-flash)** → agent
  dispatch. HTTP 200 across all 10 videos; ~$0.001 total LLM spend per run.
- **Intermittent / environment-limited:** YouTube transcript capture
  (cloud-IP rate-block; succeeded for 1/10 in a prior run).
- **Fixed this branch:** the dead AI extraction path (Bug A) + a real
  Vercel AI Gateway provider, covered by regression tests.
- **For the richest results:** run from a non-blocked IP (or feed transcripts
  via the `transcript`/`transcript_text` request fields the endpoints already
  accept) so the LLM extracts from full transcripts rather than titles — as
  demonstrated by the 26-event extraction on video 6's captured transcript.
