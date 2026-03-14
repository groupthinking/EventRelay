# 🎯 EventRelay — AI Video Processing & Event Extraction Platform

[![CI](https://github.com/groupthinking/EventRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/groupthinking/EventRelay/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Node >= 20](https://img.shields.io/badge/Node-%3E%3D20-green)
![Python >= 3.9](https://img.shields.io/badge/Python-%3E%3D3.9-blue)

AI-powered video processing platform: paste a YouTube URL → capture a word-for-word transcript, extract typed events, dispatch multi-agent workflows, and surface AI-driven insights. The system chains a **Next.js** frontend with a **FastAPI** backend through a monorepo of shared TypeScript packages and MCP servers.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Next.js Frontend  (apps/web)              localhost:3000      │
│                                                                │
│  /dashboard  — main UI (React + Zustand)                       │
│  /playground — API explorer                                    │
│                                                                │
│  API Routes (serverless):                                      │
│    POST /api/video           → transcript + AI analysis        │
│    POST /api/pipeline        → full end-to-end pipeline        │
│    POST /api/extract-events  → structured event extraction     │
│    POST /api/transcribe      → YouTube / OpenAI STT            │
│    POST /api/chat            → conversational AI               │
│    GET  /api/dashboard       → backend health proxy            │
└───────────────────────┬────────────────────────────────────────┘
                        │  HTTP (BACKEND_URL)
┌───────────────────────▼────────────────────────────────────────┐
│  FastAPI Backend  (src/youtube_extension/)  localhost:8000     │
│                                                                │
│  POST /api/v1/transcript-action   core pipeline (Gemini)       │
│  POST /api/v1/process-video       async video processing       │
│  POST /api/v1/video-to-software   video → deployable code      │
│  POST /api/v1/events/extract      event extraction             │
│  POST /api/v1/agents/dispatch     agent orchestration          │
│  POST /api/v1/chat                conversational AI            │
│  GET  /api/v1/health              health + readiness           │
│  GET  /api/v1/capabilities        provider feature flags       │
│  GET  /api/v1/videos              processed video listing      │
│  GET  /api/v1/metrics             performance metrics          │
│  ...and more (see /docs)                                       │
│                                                                │
│  Agents: Gemini · OpenAI · Anthropic · Grok (multi-provider)  │
└────────────────────────────────────────────────────────────────┘
```

**Hybrid AI:** Gemini handles deep video analysis; OpenAI Responses API provides structured event/action extraction with strict JSON Schema; OpenAI STT and Gemini serve as transcription fallbacks when YouTube captions are unavailable. The system is multi-provider — Anthropic and Grok are also supported.

## Quick Start

### Prerequisites

- Python >= 3.9
- Node.js >= 20
- At minimum: `GEMINI_API_KEY` **or** `OPENAI_API_KEY`

### Setup

```bash
# Clone
git clone https://github.com/groupthinking/EventRelay.git
cd EventRelay

# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev,youtube,ml]

# Frontend (installs all workspace packages)
npm install

# Copy and edit environment file
cp .env.example .env
# Add at minimum: GEMINI_API_KEY and/or OPENAI_API_KEY
```

### Run

```bash
# Terminal 1: Backend
PYTHONPATH=src uvicorn youtube_extension.main:app --reload --port 8000

# Terminal 2: Frontend
npm run dev:web
# or: cd apps/web && BACKEND_URL=http://localhost:8000 npx next dev --port 3000
```

Open http://localhost:3000/dashboard — paste a YouTube URL and watch it process.  
Full API docs: http://localhost:8000/docs

## How It Works

1. **Paste URL** → Dashboard (or `/api/pipeline`) sends the YouTube link to the backend
2. **Transcribe** → Backend fetches the YouTube transcript; falls back to OpenAI STT or Gemini if captions are unavailable
3. **Analyze** → Gemini agents run: summary, personality mapping, strategic insights
4. **Extract** → OpenAI Responses API (or Gemini) returns structured events, actions, and topics via strict JSON Schema
5. **Dispatch** → Agent orchestrator spawns specialized agents based on extracted events
6. **Display** → Dashboard shows results across tabs: insights, transcript, events, agents

## API Endpoints

### Frontend Routes (Next.js — `apps/web`)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/video` | Process YouTube URL → transcript + AI analysis |
| POST | `/api/pipeline` | Full end-to-end pipeline: analysis → code → deployment |
| POST | `/api/extract-events` | Structured event/action extraction (OpenAI / Gemini) |
| POST | `/api/transcribe` | Transcription with YouTube / OpenAI STT / Gemini fallback |
| POST | `/api/chat` | Chat with AI about video content |
| GET | `/api/dashboard` | Backend health check proxy |

### Backend Routes (FastAPI — `src/youtube_extension/`)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/v1/transcript-action` | Core pipeline: transcript → agents → structured results |
| POST | `/api/v1/process-video` | Async video processing job |
| GET | `/api/v1/videos/{job_id}/status` | Async job status polling |
| POST | `/api/v1/video-to-software` | Convert video concepts into deployable code |
| POST | `/api/v1/events/extract` | Event extraction from transcript |
| POST | `/api/v1/agents/dispatch` | Dispatch agent execution |
| GET | `/api/v1/agents/{agent_id}/status` | Agent execution status |
| POST | `/api/v1/agents/a2a/send` | Agent-to-Agent (A2A) message |
| POST | `/api/v1/chat` | Conversational AI about videos |
| GET | `/api/v1/health` | Service health check |
| GET | `/api/v1/health/detailed` | Detailed component health |
| GET | `/api/v1/capabilities` | Available features and AI providers |
| GET | `/api/v1/videos` | List processed videos |
| GET | `/api/v1/videos/{video_id}` | Video details |
| GET | `/api/v1/metrics` | Performance metrics |
| POST | `/api/v1/feedback` | Submit user feedback |

Full interactive docs at http://localhost:8000/docs (Swagger UI).

## Project Structure

```
EventRelay/
├── apps/
│   └── web/                         # Next.js 15 frontend (TypeScript)
│       └── src/
│           ├── app/
│           │   ├── dashboard/        # Main dashboard UI
│           │   ├── playground/       # Interactive API explorer
│           │   └── api/              # Serverless routes (video, pipeline, chat, …)
│           ├── components/           # TranscriptViewer, EventList, AgentDashboard, …
│           ├── store/                # Zustand state management
│           └── lib/                  # API client, Gemini client, CloudEvents, types
├── packages/                         # Shared TypeScript monorepo packages
│   ├── ai-gateway/                   # Multi-provider AI gateway
│   ├── database/                     # Prisma schema + client
│   ├── embeddings/                   # pgvector semantic search helpers
│   ├── mcp-connectors/               # MCP client utilities
│   ├── state-manager/                # Shared state management
│   ├── vector-store/                 # Vector store abstraction
│   ├── logger/                       # Structured logging
│   ├── observability/                # Metrics + tracing
│   └── ui/                           # Shared UI components
├── mcp-servers/                      # MCP server implementations
│   ├── litert-mcp/                   # LiteRT on-device model server
│   └── shared-state/                 # Cross-agent state continuity fabric
├── src/                              # Python backend source
│   ├── youtube_extension/            # Main FastAPI application
│   │   ├── main.py                   # App entry point
│   │   ├── backend/
│   │   │   ├── api/v1/               # Router + Pydantic models
│   │   │   ├── services/ai/          # Gemini, health monitoring
│   │   │   ├── containers/           # Dependency injection (service container)
│   │   │   └── middleware/           # Auth, rate limiting, security
│   │   ├── services/
│   │   │   ├── workflows/            # Transcript-action, video workflows
│   │   │   └── agents/               # Specialized agent implementations
│   │   └── mcp/                      # Enterprise MCP server
│   ├── agents/                       # Agent framework (A2A, MCP, multi-LLM)
│   └── uvai/                         # UVAI API layer (v2)
├── tests/                            # Python test suite
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   └── workflows/                    # Workflow-level tests
├── infrastructure/                   # Kubernetes, Terraform, DB setup
├── docs/                             # Extended documentation
├── .github/                          # CI/CD workflows, Copilot agent configs
├── Dockerfile                        # Production container (python:3.12-slim)
├── pyproject.toml                    # Python project + dependency config
└── package.json                      # Monorepo root (npm workspaces + Turbo)
```

## Testing

```bash
# Python tests
PYTHONPATH=src pytest tests/ -v

# Python unit tests only
PYTHONPATH=src pytest tests/unit/ -v

# Frontend build check
npm run build:web

# Frontend lint
cd apps/web && npx next lint

# All workspaces (Turbo)
npm run lint
npm test
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Recommended | Google AI Studio key for Gemini agents |
| `OPENAI_API_KEY` | Recommended | OpenAI key for event extraction + STT |
| `ANTHROPIC_API_KEY` | No | Anthropic Claude (alternative provider) |
| `XAI_API_KEY` | No | xAI Grok (alternative provider) |
| `YOUTUBE_API_KEY` | No | YouTube Data API for enhanced metadata |
| `DATABASE_URL` | No | SQLite (default) or PostgreSQL connection string |
| `BACKEND_URL` | No | Backend URL consumed by Next.js (default: `http://localhost:8000`) |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | No | Supabase for auth + storage |
| `NEXTAUTH_SECRET` | No | NextAuth.js session secret |

See `.env.example` for the full list including Redis, GCP, and observability settings.

## Deployment

```bash
# Docker (backend)
docker build -t eventrelay .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=... \   # or OPENAI_API_KEY — at least one required
  eventrelay

# Vercel (frontend)
vercel deploy --prod
```

A `railway.toml` is included for Railway deployments, and `infrastructure/` contains Kubernetes manifests and Terraform configs for GCP / Cloud Run.

## Contributing

- Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `chore:`, etc.
- Run tests before opening PRs
- See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) for detailed guidelines

## License

MIT — see [LICENSE](LICENSE)
