# EventRelay — Gemini CLI Context

This file provides project context for Gemini CLI when working in the EventRelay repository.

## Project Overview

EventRelay is an AI-powered video automation platform that transforms YouTube videos into
actionable workflows. It captures transcripts, extracts events, dispatches them to MCP
(Model Context Protocol) agents, and builds a RAG-based knowledge store. The backend is
Python/FastAPI and the frontend is a Next.js/React/TypeScript monorepo.

## Single Workflow

**EventRelay has ONE workflow:** YouTube link → transcript → events → agents → outputs.
Never introduce alternative flows or manual triggers that bypass this pipeline.

## Repository Structure

```
src/                          # Python backend
  youtube_extension/
    backend/                  # FastAPI app (api/v1/, services/, models/, middleware/)
    services/                 # Orchestration (agents/, workflows/, ai/)
    mcp/                      # MCP ecosystem coordinator
    main.py                   # FastAPI entry point
apps/
  web/                        # Next.js frontend (port 3000)
packages/                     # Shared monorepo packages
mcp-servers/                  # MCP server implementations (langextract, vercel config)
tests/                        # Python tests (unit/, integration/, fixtures/, workflows/)
docs/                         # Extended documentation
infrastructure/               # Kubernetes manifests, Terraform, Cloud Run deploy scripts
.github/workflows/            # CI/CD pipelines
.gemini/settings.json         # Gemini CLI MCP server configuration
```

## MCP Extensions (configured in .gemini/settings.json)

The following MCP servers are pre-configured for Gemini CLI:

| Server | Purpose | Trust |
|---|---|---|
| `github` | GitHub repo management via `@github/github-mcp-server` | `false` — external npm package |
| `git-workflow` | Safe git operations (status/add/commit/pull/push) | `true` — local project code |
| `stitch` | Google Stitch HTTP MCP endpoint | `false` — remote HTTP service |

`trust: true` bypasses per-call confirmation prompts; use only for local project tools.
Environment variables (e.g. `$GITHUB_TOKEN`) are expanded by Gemini CLI from the shell environment.

Run `/mcp` inside Gemini CLI to verify connected servers and available tools.

## Common Commands

### Python Backend

```bash
# Install (editable with dev extras)
pip install -e .[dev,youtube,ml]

<<<<<<< HEAD
# Run backend server
uvicorn youtube_extension.main:app --reload --port 8000
=======
# Run backend server (PYTHONPATH=src is required for absolute imports to resolve)
PYTHONPATH=src uvicorn youtube_extension.main:app --reload --port 8000
>>>>>>> origin/main

# Tests
pytest tests/ -v
pytest tests/unit/ -v         # unit only
pytest tests/ -m "not slow"   # skip slow tests

# Lint / format
ruff check src/ --fix
black src/
isort src/
mypy src/
```

### Frontend (Next.js / Turbo monorepo)

```bash
npm install          # install all workspace deps
turbo run build      # build all workspaces
turbo run dev        # dev servers
turbo run lint
turbo run test
```

## Code Style

### Python
- **Formatter**: Black, 88-char line length
- **Linter**: Ruff (E, W, F, I, B, C4, UP; E501 ignored)
- **Type checking**: mypy strict (`disallow_untyped_defs = true`)
- Target Python 3.9+; config in `pyproject.toml`

### TypeScript
- Strict mode TypeScript (`apps/web/tsconfig.json`)
- ESLint with Next.js rules (shared config in `packages/eslint-config/`)
- Tailwind CSS; path alias `@/*` → `src/*`

## Testing

- **pytest** — `pythonpath = src`, `testpaths = tests`, `asyncio_mode = auto`
- Coverage target: 90 % minimum enforced via `pytest.ini` on `backend`, `enhanced_video_processor`, and `enterprise_mcp_server`
- Default test video ID: `auJzb1D-fag` — **never** use `dQw4w9WgXcQ` (Rick Roll; causes flaky tests due to age-gating)
- Use real `tempfile`/`shutil` temp dirs; avoid `pyfakefs`

## Architecture Notes

- **Event-driven**: events follow `<domain>.<entity>.<action>` (e.g. `youtube.video.captured`)
- **Dependency injection**: service container pattern in `backend/containers/`
- **Multi-provider AI**: Gemini (primary), OpenAI, Anthropic, Grok
- **MCP integration**: agent orchestration via Model Context Protocol
- **Database**: SQLite (dev), PostgreSQL (prod) via SQLAlchemy / Alembic
- **Auth**: NextAuth.js (frontend), python-jose (backend)
- **Monorepo**: Turbo for JS workspaces (`apps/*`, `packages/*`, `mcp-servers/*`)

## Key Policies

- **REAL_MODE_ONLY**: no mock delays or fake data in production code
- **No secrets in code**: all keys in `.env` (gitignored)
- **Security**: Pydantic input validation; no `dangerouslySetInnerHTML`; sanitize subprocess args
- **Type safety**: mypy strict (Python), TypeScript strict (frontend)
- **Minimal changes**: make surgical, precise modifications; never delete working code without justification

## Environment Variables (required)

```bash
GEMINI_API_KEY=...        # Google Gemini API
OPENAI_API_KEY=...        # OpenAI API
YOUTUBE_API_KEY=...       # YouTube Data API v3
DATABASE_URL=sqlite:///./.runtime/app.db
GITHUB_TOKEN=...          # for github MCP server
STITCH_ACCESS_TOKEN=...   # for stitch MCP server (optional)
```
