# 🎯 EventRelay — Agentic Video Execution Platform

AI-powered transcript capture, event extraction, and agent execution for YouTube content. EventRelay ships a FastAPI backend, a React dashboard, Gemini/Veo hybrid orchestration, and an agent workflow that mirrors what happens in the video—transcribing every scene into natural language, grounding it in RAG, and dispatching MCP/A2A agents to take real follow-up actions.

## 📘 Overview
- **What it solves:** Automates end-to-end execution from YouTube videos—capturing word-for-word transcripts, extracting concrete events, and wiring them into agent runtimes that can build code, create tickets, or trigger workflows.
- **Why it matters:** Eliminates manual note-taking, keeps teams aligned on factual video-derived events, and exposes a programmable API for dispatching agents that act on what was actually said and shown.
- **Status:** Production-ready backend + frontend with ongoing instrumentation and MCP ecosystem integration.
- **Learning loop:** Every transcript is grounded into the RAG store and fed back into agents’ skill adapters so subsequent runs refine their prompts, tooling choices, and dispatch heuristics.

## 🔍 Mandatory Context Verification
Before contributing or running automation, review **all lines** in the following governance artifacts:
- `~/.claude/CLAUDE.md`
- `~/CLAUDE.md`
- `/Users/garvey/CLAUDE_CODE_GOVERNANCE.md`

## 🖼️ Visual Context
- Architecture diagram: [`docs/visuals/architecture.md`](docs/visuals/architecture.md)
- Add product screenshots (`png/jpg/gif`) under `docs/visuals/` and link them from this section when ready.

## ⚙️ Prerequisites
- Python >= 3.9 (see `pyproject.toml`)
- Node.js >= 18 and npm >= 8 (`package.json` engines)
- Google Cloud project configured for Speech-to-Text v2 (optional but required for long videos)
- Valid API credentials (YouTube Data API, Gemini, OpenAI, optional Anthropic/Grok)

## 🚀 Installation & Setup
1. **Clone & create virtual env**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev,youtube,ml]
   ```
2. **Install frontend dependencies**
   ```bash
   npm install --prefix frontend
   ```
3. **Export required environment variables** (adjust for your workspace):
   ```bash
   export YOUTUBE_API_KEY="<your-youtube-data-api-key>"
   export GEMINI_API_KEY="<your-gemini-api-key>"
   export OPENAI_API_KEY="<your-openai-api-key>"
   export GOOGLE_SPEECH_PROJECT_ID="cloudhub-470100"
   export GOOGLE_SPEECH_LOCATION="us-central1"
   export GOOGLE_SPEECH_RECOGNIZER="transcript-recognizer"
   export GOOGLE_SPEECH_GCS_BUCKET="gcf-v2-sources-833571612383-us-central1"  # required for long form
   export GOOGLE_SPEECH_GCS_PREFIX="speech-transcripts"                        # optional prefix
   ```
   See `scripts/check_credentials.py` for the complete credential inventory (MCP, LiveKit, Redis, OTEL, etc.).
4. **Boot the backend**
   ```bash
   uvicorn uvai.api.main:app --reload --port 8000
   ```
5. **Boot the frontend**
   ```bash
   npm start --prefix frontend
   ```

## 🔧 Configuration
- **Environment files:** `.env`, `.env.local`, `.env.production` (create as needed); keep secrets out of source control.
- **MCP tooling:** Align `~/.cursor/mcp.json` with the cleaned config described in `docs/status/MCP_CONFIGURATION_FIXES.md` before enabling MCP-based agents.
- **Optional providers:** `ANTHROPIC_API_KEY`, `GROK_API_KEY`, `LIVEKIT_*`, `REDIS_URL`, and `OTEL_EXPORTER_OTLP_ENDPOINT` unlock additional integrations.
- **Speech-to-Text batch:** Ensure your Google project has access to the configured GCS bucket for >30 minute videos.

## 🛠️ Usage
- **CLI helpers** (`youtube-extension`):
  - `youtube-extension serve --host 0.0.0.0 --port 8000` – start FastAPI dev server
  - `youtube-extension test -v --coverage` – run pytest with optional coverage (expects `tests/` directory)
  - `youtube-extension lint` / `format` – run Ruff + mypy, or Black + isort
- **REST APIs:** Once the backend is running, visit `http://localhost:8000/docs` for FastAPI Swagger UI.
  - Transcript workflow example:
    ```bash
    curl -X POST http://127.0.0.1:8000/api/v1/transcript-action \
         -H "Content-Type: application/json" \
         -d '{"video_url":"https://www.youtube.com/watch?v=m0XAPRAOJ8A","language":"en"}'
    ```
  - Cloud AI analysis endpoints live under `/api/v1/cloud-ai/*` (see [API Reference](#-api-reference)).
- **Frontend dashboard:** `npm start --prefix frontend` launches the React UI with hot reload and proxying to the backend.
- **Sample payloads:** `transcript_action_sample.json` illustrates the end-to-end response (event log, execution graph, task dispatch) for the transcript workflow.

## 🗂️ Project Structure
```
youtube_extension/
├── src/youtube_extension/
│   ├── backend/                 # FastAPI routers, deployment helpers
│   ├── services/                # Agents, workflows, deployment manager
│   ├── integrations/            # Cloud AI, external providers
│   ├── mcp/                     # MCP ecosystem coordinator and servers
│   └── main.py                  # FastAPI entry point
├── frontend/                    # React dashboard + MCP-aware hooks
│   └── src/
│       ├── components/          # UI components + tests
│       ├── hooks/               # Data fetching & integration hooks
│       └── services/            # API clients / stores
├── docs/                        # Living documentation & status reports
├── deployment/                  # Production assembly tooling
├── scripts/                     # Credential checks, monitoring, utilities
├── Dockerfile* / docker-compose.*.yml
├── pyproject.toml / package.json
└── LICENSE
```

## 🧠 Adaptive Learning & Memory
- **Transcript memory:** Each transcription is persisted to `database/` tables and `youtube_processed_videos/`, then vectorized through the RAG workers in `src/rag/` for factual recall.
- **Agent skill adapters:** The MCP orchestration in `mcp_youtube-0.2.0/` and `scripts/youtube_innovation_mcp_server.py` captures execution traces so subsequent runs reuse the highest scoring tools and prompts.
- **Feedback signals:** Task outcomes and competitive insights are logged via `scripts/youtube_innovation_learning_database.py`, producing pattern tables (`learning_outcomes`, `pattern_database`) that agents query before acting.
- **Custom model loops:** Fine-tuning recipes in `fastvlm_gemini_hybrid/` and `fine_tuned_execution/` let you continually improve planners and dispatch heuristics once enough labeled events accumulate.

## 🧾 API Reference
- `GET /` – server metadata and feature list
- `GET /health` – service heartbeat
- `POST /api/v1/transcript-action` – transcript → event extraction → agent dispatch
- `POST /api/v1/process-video` – placeholder for legacy workflow
- `GET /api/v1/cloud-ai/providers/status` – provider availability snapshot
- `POST /api/v1/cloud-ai/analyze/video` – single video multi-provider analysis
- `POST /api/v1/cloud-ai/analyze/batch` – batch analysis with provider fallback
- `POST /api/v1/cloud-ai/analyze/multi-provider` – parallel provider invocation
- `GET /api/v1/cloud-ai/analysis-types` – supported analysis enumerations
- Full REST schema is discoverable via FastAPI docs (`/docs`, `/redoc`).

## 🧪 Testing
- **Backend:**
  ```bash
  pytest tests/unit/test_gemini_service_model_selection.py \
         tests/unit/test_hybrid_processor_cloud.py \
         tests/unit/test_transcript_action_workflow.py -q
  ```
  _Heads-up: the repository currently references `tests/` in several scripts, but the folder may be missing in some branches—recreate or restore before running the suite._
- **Frontend:**
  ```bash
  npm test -- --watch=false --prefix frontend
  ```
  Unit specs live under `frontend/src/components/__tests__/` and smoke tests under `frontend/src/__tests__/`.
- **Lint & type-check:**
  ```bash
  youtube-extension lint
  youtube-extension format
  ```

## 🚢 Deployment
- **Local production:**
  ```bash
  docker compose -f docker-compose.full.yml up --build
  ```
  Or run tailored stacks (e.g., `docker-compose.youtube-packager.yml`) for scoped deployments.
- **Containers:** Dockerfiles exist for backend, orchestrator, MCP server, and frontend (`Dockerfile.production`, `Dockerfile.youtube-packager`, etc.).
- **Environments:** Keep secrets in your orchestrator (Fly.io, Vercel, etc.) and mirror the environment variables from the setup section.

## 🧰 Troubleshooting
- **`ModuleNotFoundError` on startup:** Verify the virtual environment is active before running CLI commands.
- **`GOOGLE_SPEECH_*` errors:** Re-export credentials or copy `.env.example` to `.env` and populate required keys.
- **Port 8000/3000 already in use:** Stop existing services (`lsof -i :8000`) or override the port flags.
- **Frontend `npm start` fails:** Remove `node_modules`, clear npm cache, and reinstall with `npm install --prefix frontend`.
- **Missing tests directory:** Some branches omit `tests/`; recreate from templates in `docs/status/` before running pytest.

## 🤝 Contributing
- Follow the Python style guide (4-space indent, type hints, Black/Isort/Ruff) and React conventions (PascalCase components, camelCase hooks).
- Run `youtube-extension lint` and `youtube-extension test` before opening a PR.
- Document new agents in `development/agents/` and wire feature flags through `src/youtube_extension/services/agents/`.
- Review `AGENTS.md` and `development/agents/architecture/*` when extending the agent stack.
- Use imperative commit messages and include motivation, implementation notes, and test evidence in PR descriptions.

## 📢 Support & Contact
- File issues or requests through the repository issue tracker.
- For security concerns, reference `SECURITY.md` (currently a template—update with final contact details when available).
- Internal teams can document playbooks and escalation paths under `docs/status/`.

## 🔐 Security
- Never commit secrets—`.env.example` is provided as a template only.
- Rotate API credentials stored in your shell profile or secret manager regularly.
- Align with the guidance in `SECURITY.md` and `/Users/garvey/CLAUDE_CODE_GOVERNANCE.md` before enabling production agents.
- Rate limiting and circuit breakers are enforced in `mcp_servers/youtube_api_proxy.py`; keep defaults unless you understand provider quotas.

## 📦 Dependencies
- Python packages are declared in `pyproject.toml`; install optional extras with `pip install -e .[dev,youtube,ml]` as needed.
- Frontend dependencies live in `frontend/package.json`; Node 18+ is required by the `engines` constraint.
- Docker images reference `Dockerfile.production` and `Dockerfile.youtube-packager` for backend and packaging workloads respectively.

## 📈 Monitoring & Observability
- Health checks: `GET /health` and per-container Docker health probes (see `docker-compose.full.yml`).
- Metrics service tracks transcript fallback success, provider latency, and quota usage—wire into dashboards via `metrics_service`.
- `scripts/check_credentials.py` audits required keys across `.env` files.
- Processed artifacts persist in `.runtime/`, `youtube_processed_videos/`, and configured cloud buckets.

## 📄 License
Released under the MIT License. See `LICENSE` for full terms.

## 🔄 Changelog & Roadmap
- Operational status reports live in `docs/status/` and historical plans in `PLAN.md`.
- Release history is tracked in [`docs/changelog/CHANGELOG.md`](docs/changelog/CHANGELOG.md); update the "Unreleased" section as features land and cut tagged releases for production drops.

## 📊 Status Badges
_Add CI/Test/Coverage badges here once your pipelines are active._

---
Built for agentic video understanding, transcript automation, and actionable execution planning.
