# 🎯 EventRelay — AI Video Processing & Event Extraction Platform

[![CI](https://github.com/groupthinking/EventRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/groupthinking/EventRelay/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Node >= 20](https://img.shields.io/badge/Node-%3E%3D20-green)
![Python >= 3.11](https://img.shields.io/badge/Python-%3E%3D3.11-blue)

AI-powered video transcript capture, structured event extraction, and agent execution for YouTube content. Paste a URL → get a word-for-word transcript, typed events, actionable tasks, and AI-driven insights.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Next.js Frontend  (apps/web)         localhost:3000     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Dashboard   │  │ /api/video   │  │ /api/extract-  │  │
│  │  (React +    │──│ (proxy to    │──│  events        │  │
│  │   Zustand)   │  │  backend)    │  │ (OpenAI        │  │
│  └─────────────┘  └──────┬───────┘  │  Responses API) │  │
│                          │          └────────────────┘  │
│  ┌────────────────┐      │                              │
│  │ /api/transcribe │      │   OpenAI STT fallback       │
│  └────────────────┘      │                              │
└──────────────────────────┼──────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│  FastAPI Backend  (src/)           localhost:8000        │
│                          │                              │
│  ┌───────────────────────▼─────────────────────────┐    │
│  │  /api/v1/transcript-action                      │    │
│  │  YouTube transcript → 3 Gemini agents:          │    │
│  │    • transcript_action (summary + tasks)        │    │
│  │    • personality_agent (intent analysis)        │    │
│  │    • strategy_agent   (strategic insights)      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  /api/v1/health  /api/v1/capabilities  /api/v1/videos   │
│  /api/v1/events  /api/v1/agents        /api/v1/chat     │
└─────────────────────────────────────────────────────────┘
```

**Hybrid AI:** Gemini handles deep analysis (personality, strategy), OpenAI Responses API handles structured event/action extraction with JSON Schema strict mode, and OpenAI STT provides transcription fallback when YouTube captions are unavailable.

## Quick Start

### Prerequisites

- Python >= 3.11
- Node.js >= 20
- API keys: `GEMINI_API_KEY` and `OPENAI_API_KEY`

### Setup

```bash
# Clone
git clone https://github.com/groupthinking/EventRelay.git
cd EventRelay

# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

# Frontend
npm install

# API keys (add to shell profile or .env)
export GEMINI_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

### Run

```bash
# Terminal 1: Backend
PYTHONPATH=src python3 -m uvicorn youtube_extension.main:app --port 8000

# Terminal 2: Frontend
cd apps/web && BACKEND_URL=http://localhost:8000 npx next dev --port 3000
```

### OpenAPI + SDKs

- Export the backend schema: `python scripts/export_openapi.py` (writes `openapi/eventrelay.openapi.json`).
- Generate typed SDKs with Stainless: `npm run sdk:generate` (requires `npx stainless`).
- SDK packages live in `sdks/python` and `sdks/typescript` (see `sdks/README.md` for publish steps).

Open http://localhost:3000/dashboard — paste a YouTube URL and watch it process.

## How It Works

1. **Paste URL** → Dashboard sends to `/api/video`
2. **Transcribe** → Backend fetches YouTube transcript (falls back to OpenAI STT if unavailable)
3. **Analyze** → 3 Gemini agents run: summary, personality mapping, strategy
4. **Extract** → OpenAI Responses API returns structured events, actions, topics via strict JSON Schema
5. **Display** → Dashboard shows everything in tabs: insights, transcript, events, agents

## API Endpoints

### Frontend Routes (Next.js)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/video` | Process YouTube URL → transcript + AI analysis |
| POST | `/api/extract-events` | Structured event/action extraction (OpenAI) |
| POST | `/api/transcribe` | Transcription with YouTube/OpenAI STT fallback |
| POST | `/api/chat` | Chat with AI about video content |
| GET | `/api/dashboard` | Backend health check proxy |

### Backend Routes (FastAPI)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/v1/transcript-action` | Core pipeline: transcript → agents → results |
| GET | `/api/v1/health` | Service health check |
| GET | `/api/v1/capabilities` | Available features and providers |
| POST | `/api/v1/videos/process` | Async video processing job |
| GET | `/api/v1/videos/{job_id}/status` | Job status polling |
| POST | `/api/v1/events/extract` | Backend event extraction |
| POST | `/api/v1/agents/dispatch` | Dispatch agent execution |
| POST | `/api/v1/chat` | Conversational AI about videos |

Full API docs at http://localhost:8000/docs (Swagger UI).

## Project Structure

```
EventRelay/
├── apps/web/                        # Next.js frontend
│   └── src/
│       ├── app/
│       │   ├── dashboard/page.tsx   # Main dashboard UI
│       │   └── api/                 # API routes (video, extract-events, transcribe, chat)
│       ├── components/              # TranscriptViewer, EventList, AgentDashboard, ResultsViewer
│       ├── store/                   # Zustand state management
│       └── lib/                     # API client, services, types
├── src/youtube_extension/           # FastAPI backend
│   ├── main.py                      # App entry point
│   └── backend/
│       ├── api/v1/                  # Router + Pydantic models
│       └── services/ai/             # Gemini service, health monitoring
├── tests/unit/                      # Python unit tests
├── docs/                            # Documentation
├── .github/                         # CI workflows, Copilot agent configs
├── Dockerfile                       # Production container
└── package.json                     # Monorepo root (npm workspaces)
```

## Testing

```bash
# Python unit tests (15 tests)
PYTHONPATH=src python3 -m pytest tests/unit/test_api_v1_models.py -v --override-ini="addopts="

# Frontend build check
npm run build:web

# Lint
cd apps/web && npx next lint
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google AI Studio key for Gemini agents |
| `OPENAI_API_KEY` | Yes | OpenAI key for event extraction + STT |
| `BACKEND_URL` | No | Backend URL (default: `http://localhost:8000`) |
| `YOUTUBE_API_KEY` | No | YouTube Data API for enhanced metadata |

## Deployment

```bash
# Docker
docker build -t eventrelay .
docker run -p 8000:8000 -e GEMINI_API_KEY=... -e OPENAI_API_KEY=... eventrelay

# Vercel (frontend)
vercel deploy --prod
```

## Contributing

- Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `chore:`, etc.
- Run tests before opening PRs
- See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) for detailed guidelines

## License

MIT — see [LICENSE](LICENSE)
