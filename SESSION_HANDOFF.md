# EventRelay — Session Handoff & System Documentation

> ⚠️ **OUTDATED (deployment section).** This doc was generated 2026-03-02 and the
> hosting topology below is no longer accurate. The backend is **no longer on
> Railway** — `eventrelay-production.up.railway.app` is dead (404). Current
> production topology (verified 2026-06-16):
>
> - **Frontend (canonical):** https://uvai.io (Vercel) — `event-relay-web.vercel.app` is a dead alias.
> - **Backend:** https://api.uvai.io → Google Cloud Run service `uvai-backend` (us-central1), fronted by Cloudflare. Health: `https://api.uvai.io/api/v1/health`.
> - Deploy config: `.github/workflows/deploy-cloud-run.yml` (manual dispatch). `railway.toml` is legacy.
>
> Treat any "Railway" / `event-relay-web.vercel.app` references in the rest of
> this document as historical only.

> **Generated**: 2026-03-02 | **Repo**: [groupthinking/EventRelay](https://github.com/groupthinking/EventRelay)  
> **Frontend**: https://uvai.io | **Backend**: https://api.uvai.io (Google Cloud Run)

---

## 1. What Is EventRelay?

EventRelay is an **Agentic Video Execution Platform** — a complete end-to-end pipeline that takes a YouTube URL as input and produces **deployed, running software** as output.

The vision (from the owner's notes): *"You're building the first AI software factory that goes from human intention → deployed reality automatically."*

### The Pipeline (4 Stages)
```
┌─────────────────────────────────────────────────────────────────┐
│  YouTube URL                                                     │
│       ↓                                                          │
│  1. INGEST   — Gemini analyzes video with Google Search grounding │
│       ↓                                                          │
│  2. TRANSLATE — Structured output → VideoPack JSON artifact      │
│       ↓                                                          │
│  3. TRANSPORT — CloudEvents published at each stage              │
│       ↓                                                          │
│  4. EXECUTE  — Agents generate code → create repo → deploy live  │
│       ↓                                                          │
│  Live URL + GitHub Repo                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture

### Production Infrastructure

| Component | Platform | URL | Tech Stack |
|-----------|----------|-----|------------|
| Frontend  | Vercel   | `uvai.io` | Next.js 14, React, Zustand, TypeScript |
| Backend   | Google Cloud Run | `api.uvai.io` (`uvai-backend`, us-central1) | FastAPI, Python 3.12, uvicorn |
| Database  | SQLite (ephemeral) | `/tmp/uvai_data/app.db` | On Cloud Run container |
| Repos     | GitHub   | `github.com/groupthinking/` | Auto-created by pipeline |

### Request Flow
```
Browser → Vercel (Next.js)
  ├── POST /api/pipeline        → Cloud Run backend /api/v1/video-to-software
  ├── POST /api/video           → Cloud Run backend /api/v1/transcript-action (analysis only)
  ├── POST /api/transcribe      → Gemini Google Search (direct)
  └── POST /api/extract-events  → Gemini structured output (direct)

Cloud Run Backend (api.uvai.io):
  /api/v1/video-to-software chains:
    Phase 1: EnhancedVideoProcessor.process_video(url)  → Gemini + YouTube analysis
    Phase 2: ProjectCodeGenerator.generate_project()     → HTML/JS/CSS in /tmp
    Phase 3: DeploymentManager.deploy_project()          → GitHub repo + Vercel deploy
```

### Environment Variables

**Vercel (Frontend)**:
| Key | Purpose |
|-----|---------|
| `BACKEND_URL` | Points to Cloud Run backend (`https://api.uvai.io`) |
| `GEMINI_API_KEY` | Gemini API (standard) |
| `Vertex_AI_API_KEY` | Vertex AI Express Mode key (starts with `AQ.Ab8...`) |
| `OPENAI_API_KEY` | OpenAI fallback for transcription |

**Cloud Run (Backend)**:
| Key | Purpose |
|-----|---------|
| `GEMINI_API_KEY` | Video analysis via Gemini |
| `Vertex_AI_API_KEY` | Vertex AI Express Mode |
| `GITHUB_TOKEN` | Create repos under `groupthinking` org |
| `VERCEL_TOKEN` | Deploy generated projects to Vercel |
| `DATABASE_URL` | `sqlite:///tmp/uvai_data/app.db` |

---

## 3. API Reference

### Frontend Endpoints (Vercel)

#### `GET /api/pipeline`
Returns pipeline metadata and available capabilities.
```json
{
  "name": "EventRelay End-to-End Pipeline",
  "version": "1.0.0",
  "pipeline_stages": ["1. Ingest...", "2. Translate...", "3. Transport...", "4. Execute..."],
  "backend_available": true,
  "gemini_available": true
}
```

#### `POST /api/pipeline` — Full End-to-End Pipeline
**Input:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "project_type": "web",              // optional, default: "web"
  "deployment_target": "vercel",       // optional, default: "vercel"
  "features": ["responsive_design"]   // optional
}
```
**Output:**
```json
{
  "id": "pipeline_mm7h503r",
  "status": "success",                // "success" | "partial" | "error"
  "pipeline": "backend",              // "backend" | "gemini-only"
  "processing_time": "31.9s",
  "result": {
    "live_url": "",                    // Live deployed URL (when deploy succeeds)
    "github_repo": "https://github.com/groupthinking/uvai-generated-project-5734",
    "build_status": "failed",          // "success" | "failed"
    "video_analysis": { "status": "success", "extracted_info": {...} },
    "code_generation": { "framework": "vanilla", "files_created": [...] },
    "deployment": { "status": "partial_success", "platforms": ["github","vercel"] }
  }
}
```

**Strategies (fallback order):**
1. Backend pipeline (Railway `/api/v1/video-to-software`) — full pipeline
2. Gemini analysis only — when no backend available

#### `POST /api/video` — Video Analysis Only
**Input:** `{ "url": "https://youtube.com/watch?v=..." }`  
**Output:** Analysis with insights, events, actions, topics.

**Strategies (fallback order):**
1. Backend `/api/v1/transcript-action`
2. Gemini agentic analysis (Google Search grounding + structured output)
3. Transcript → Extract chain (transcribe + extract-events)

### Backend Endpoints (Cloud Run / api.uvai.io)

#### `GET /api/v1/health`
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "components": {
    "video_processor": "available",
    "websocket": "available",
    "gemini_key_present": true
  }
}
```

#### `POST /api/v1/video-to-software`
**Input:** `{ "video_url": "...", "project_type": "web", "deployment_target": "vercel" }`  
**Note:** Uses `video_url` (not `url`) — different from frontend.

#### `GET /docs` — Swagger UI
Full interactive API docs at `https://api.uvai.io/docs`

#### `GET /openapi.json` — OpenAPI Spec
37+ endpoints documented. Machine-readable spec for LLM integration.

---

## 4. Key Source Files

### Frontend (Next.js — `apps/web/src/`)

| File | Purpose |
|------|---------|
| `app/api/pipeline/route.ts` | Full end-to-end pipeline endpoint |
| `app/api/video/route.ts` | Video analysis endpoint (3-strategy fallback) |
| `app/api/transcribe/route.ts` | Gemini Google Search transcription |
| `app/api/extract-events/route.ts` | Structured event extraction |
| `app/dashboard/page.tsx` | Dashboard UI with Analyze + Deploy buttons |
| `store/dashboard-store.ts` | Zustand store: `processVideo()`, `deployPipeline()` |
| `lib/gemini-video-analyzer.ts` | Gemini agentic analysis engine |
| `lib/gemini-client.ts` | GoogleGenAI client factory (Vertex AI Express Mode support) |
| `lib/cloudevents.ts` | CloudEvents v1.0 publisher |
| `lib/youtube-metadata.ts` | YouTube page scraper (no API key needed) |

### Backend (Python — `src/youtube_extension/`)

| File | Purpose |
|------|---------|
| `main.py` | Slim FastAPI entry — includes v1 router |
| `backend/main.py` | Full 565-line FastAPI app (alternative entry) |
| `backend/api/v1/router.py` | V1 API router with `/video-to-software` (line 628) |
| `backend/services/video_processing_service.py` | Core: chains analysis → codegen → deploy |
| `backend/enhanced_video_processor.py` | Gemini + YouTube video analysis |
| `backend/code_generator.py` | Creates React/VanillaJS/FastAPI projects |
| `backend/deployment_manager.py` | GitHub repo creation + Vercel/Netlify deploy |
| `backend/video_processor_factory.py` | Factory: enhanced → real → deepmcp |

### Infrastructure

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage Python 3.12, non-root user, healthcheck |
| `Dockerfile.cloudrun` | Cloud Run-optimised build (used by `deploy-cloud-run.yml`) |
| `pyproject.toml` | Python dependencies |
| `apps/web/package.json` | Frontend dependencies |

---

## 5. Gemini / Vertex AI Configuration

### Model Selection (CRITICAL)
| Model | responseSchema + googleSearch | Use For |
|-------|-------------------------------|---------|
| `gemini-3-pro-preview` | ✅ Supported together | Frontend structured analysis |
| `gemini-2.5-flash` | ❌ 400 error | Do NOT use for combined |
| `gemini-2.0-flash` | ❌ 400 error | Backend video analysis only |

### Vertex AI Express Mode
```typescript
// SDK init — apiKey is MUTUALLY EXCLUSIVE with project/location
const client = new GoogleGenAI({ vertexai: true, apiKey: vertexApiKey });
```
- Endpoint: `https://aiplatform.googleapis.com/v1beta1/publishers/google/models/{model}:generateContent`
- Auth header: `x-goog-api-key` (NOT Bearer token)
- Express Mode key starts with `AQ.Ab8...`
- Does NOT work on standard Gemini API endpoint (generativelanguage.googleapis.com)

### Key Cascade in `gemini-client.ts`
1. `Vertex_AI_API_KEY` → Vertex AI Express Mode (`vertexai: true`)
2. `GEMINI_API_KEY` → Gemini API mode
3. `GOOGLE_API_KEY` → Gemini API mode

---

## 6. How to Run Locally

### Frontend
```bash
cd apps/web
npm install
npm run dev
# → http://localhost:3000
```

### Backend
```bash
cd /path/to/EventRelay

# Create venv (MUST use Python 3.12, NOT 3.14)
python3.12 -m venv .venv
source .venv/bin/activate

# Install
pip install -e .
pip install aiohttp  # Required for EnhancedVideoProcessor

# Source secrets
source ~/.config/secrets/shell-secrets.env

# Run (override DATABASE_URL — default path is read-only on macOS)
DATABASE_URL="sqlite:///tmp/uvai_data/app.db" \
  uvicorn src.youtube_extension.backend.main:app --host 0.0.0.0 --port 8000

# Or use the slim entry point (includes v1 router):
DATABASE_URL="sqlite:///tmp/uvai_data/app.db" \
  uvicorn youtube_extension.main:app --host 0.0.0.0 --port 8000
```

**Gotchas:**
- Python 3.14 has path resolution issues — use 3.12
- `youtube-transcript-api` import fails but is handled gracefully (WARNING only)
- Default `DATABASE_URL` in `.env` points to `/.runtime` which is read-only on macOS

---

## 7. Audit Results (3 Viewpoints)

Three independent agents tested the system as: (1) an end user, (2) an LLM integrator, (3) the project owner.

### Grade Summary

| Viewpoint | Grade | Strongest Area | Weakest Area |
|-----------|-------|---------------|--------------|
| **End User** | **C+** | Landing page polish, video analysis quality | Deployment fails (no live URL), generic code |
| **LLM Integrator** | **B−** | OpenAPI spec (37 endpoints), self-describing GETs | `url` vs `video_url` inconsistency, no rate-limit headers |
| **Project Owner** | **C+** | Clean frontend architecture, working pipeline | No auth/rate-limiting, broken CORS, generic codegen |

### Composite Grade: **C+**

### What Works Well ✅
1. **Video analysis is genuinely impressive** — Gemini with Google Search grounding returns accurate, detailed analysis with events, actions, topics, and sentiment
2. **Full pipeline runs end-to-end** — YouTube URL → backend analysis → code generation → GitHub repo creation in ~30s
3. **Strong API design** — OpenAPI spec with 37 endpoints, self-describing GET endpoints, Swagger UI at `/docs`
4. **Professional frontend** — Clean landing page, Zustand state management, proper fallback strategies
5. **Solid infrastructure** — Multi-stage Docker, non-root user, healthchecks, auto-deploy from GitHub on Vercel (frontend) and Cloud Run (backend via `deploy-cloud-run.yml`)

### What Needs Fixing 🔴

| Priority | Issue | Impact |
|----------|-------|--------|
| 🔴 **P0** | No API authentication | Anyone can burn Gemini credits + create repos in your org |
| 🔴 **P0** | Rate limiting commented out | Backend wide open to abuse |
| 🔴 **P0** | Generated code is generic boilerplate | Does not reflect video content — same 4-file template every time |
| 🟡 **P1** | Vercel deployment step fails | `build_status: "failed"`, `live_url: ""` — core value prop broken |
| 🟡 **P1** | CORS misconfigured | `*.vercel.app` glob doesn't work in Starlette — browser calls may fail |
| 🟡 **P1** | `url` vs `video_url` field inconsistency | Frontend uses `url`, backend uses `video_url` — breaks LLM integration |
| 🟡 **P1** | 60+ deleted test files uncommitted | Test suite accidentally deleted, sitting in working tree |
| 🟠 **P2** | Branding confusion | "EventRelay" vs "UVAI" vs "uvai.io" across UI, meta tags, and URLs |
| 🟠 **P2** | No YouTube API key on Cloud Run | Limits transcript extraction to Gemini Search only |
| 🟠 **P2** | Cold start latency | Backend first request takes ~5-24s due to Cloud Run cold start |

---

## 8. What a Future LLM Needs to Know

### To Continue Development
1. **The vision is YouTube URL → deployed software** — NOT just JSON analysis. If you're only returning analysis results, you've missed the point.
2. **The pipeline components exist but the codegen is stub quality** — `code_generator.py` creates template files, not video-derived software. This is the #1 area to improve.
3. **Always use `gemini-3-pro-preview`** when you need `responseSchema` + `googleSearch` together on Vertex AI. Other models return 400.
4. **Vertex AI Express Mode** uses `apiKey` (NOT Bearer token, NOT project+location). These are mutually exclusive in the SDK.
5. **The owner's notes (Apple Notes, PKs 998/999/1021/1022/841)** are the source of truth for product intent. When in doubt, re-read them.

### To Use the API
```bash
# Analyze a video (fast, ~30s)
curl -X POST https://uvai.io/api/video \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'

# Full pipeline — analyze + generate code + create repo (slow, ~30-60s)
curl -X POST https://uvai.io/api/pipeline \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'

# Backend direct (uses video_url, not url)
curl -X POST https://api.uvai.io/api/v1/video-to-software \
  -H 'Content-Type: application/json' \
  -d '{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'

# Check backend health
curl https://api.uvai.io/api/v1/health

# Full API docs
open https://api.uvai.io/docs
```

### Key Gotchas
- Frontend field: `url` → Backend field: `video_url` (inconsistent)
- Status values: Frontend returns `"success"` / `"complete"` → Backend returns `"success"` / `"failed"`
- Pipeline timeout is 5 minutes (`AbortController` in `pipeline/route.ts`)
- Generated repos go to `groupthinking/uvai-generated-project-XXXX`
- Cloud Run has cold starts (~5-24s on first request after idle)

---

## 9. PRs Merged This Session

| PR | Title | Key Changes |
|----|-------|-------------|
| #41 | fix: embeddings build errors | Stub types for Firebase Data Connect SDK |
| #43 | feat: Gemini SDK upgrade | `@google/genai`, structured output, Google Search grounding, VideoPack schema |
| #44 | feat: CloudEvents + Chrome Built-in AI | CloudEvents wiring, Prompt API + Summarizer API hooks |
| #45 | feat: A2A inter-agent messaging | AgentOrchestrator wired with A2A framework |
| #46 | feat: LiteRT-LM setup script | Downloads `lit` binary + model |
| #47 | fix: video workflow rewrite | Gemini agentic analysis, YouTube metadata scraper |
| #48 | fix: Vertex AI Express Mode | Removed responseSchema+googleSearch conflict (interim) |
| #49 | fix: restore PK=998 pattern | gemini-3-pro-preview supports both — restored full pattern |
| #50 | feat: end-to-end pipeline | `/api/pipeline`, Deploy button, dashboard pipeline results |
| — | fix: Dockerfile directories | Writable dirs for deployment pipeline on Railway |

---

## 10. File Tree (Key Directories)

```
EventRelay/
├── apps/web/                    # Next.js frontend (Vercel)
│   └── src/
│       ├── app/
│       │   ├── api/
│       │   │   ├── pipeline/    # Full E2E pipeline endpoint
│       │   │   ├── video/       # Video analysis endpoint  
│       │   │   ├── transcribe/  # Gemini transcription
│       │   │   └── extract-events/ # Structured event extraction
│       │   ├── dashboard/       # Dashboard page
│       │   └── playground/      # API playground
│       ├── components/          # React components
│       ├── lib/                 # Gemini client, analyzers, CloudEvents
│       └── store/               # Zustand dashboard store
├── src/youtube_extension/       # Python backend (Railway)
│   ├── main.py                  # Slim FastAPI entry
│   └── backend/
│       ├── main.py              # Full FastAPI app
│       ├── api/v1/router.py     # V1 endpoints incl. video-to-software
│       ├── services/            # Video processing service
│       ├── code_generator.py    # Project code generation
│       ├── deployment_manager.py # GitHub + Vercel deployment
│       └── enhanced_video_processor.py # Gemini video analysis
├── src/agents/                  # Pipeline orchestrator
├── mcp-servers/                 # MCP server implementations
│   ├── litert-mcp/              # LiteRT on-device inference
│   ├── shared-state/            # State Continuity Fabric
│   └── lib/agents/              # A2A framework
├── Dockerfile                   # Multi-stage Python build
├── railway.toml                 # Railway deploy config
└── pyproject.toml               # Python dependencies
```
