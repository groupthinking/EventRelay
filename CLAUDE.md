# CLAUDE.md

This file provides context for Claude Code when working in the EventRelay repository.

## Project Overview

EventRelay is an AI-powered video automation platform that transforms YouTube videos into actionable workflows. It captures transcripts, extracts events, dispatches them to MCP (Model Context Protocol) agents, and builds a RAG-based knowledge store. The backend is Python/FastAPI and the frontend is a Next.js/React/TypeScript monorepo.

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
packages/                     # Shared monorepo packages (eslint-config, tsconfig, logger, etc.)
mcp-servers/                  # MCP server implementations (litert-mcp, shared-state)
tests/                        # Python tests (unit/, integration/, fixtures/, workflows/)
docs/                         # Extended documentation
infrastructure/               # Kubernetes manifests, Terraform, database setup
.github/workflows/            # CI/CD (ci.yml, security.yml, deploy-cloud-run.yml, etc.)
```

## Common Commands

### Python Backend

```bash
# Install (editable with dev extras)
pip install -e .[dev,youtube,ml]

# Run backend server
uvicorn src.youtube_extension.main:app --reload --port 8000

# Run tests
pytest tests/ -v
pytest tests/unit/ -v                    # Unit tests only
pytest tests/ -m "not slow"              # Skip slow tests

# Lint and format
ruff check src/                          # Lint
ruff check src/ --fix                    # Auto-fix
black src/                               # Format
isort src/                               # Sort imports
mypy src/                                # Type check
```

### Frontend (Next.js)

```bash
# Install all workspace dependencies
npm install

# Build (all workspaces via Turbo)
turbo run build
# or: npm run build

# Dev server
turbo run dev
# or: npm run dev

# Lint
turbo run lint

# Test
turbo run test
```

## Code Style

### Python
- **Formatter**: Black, 88-char line length
- **Import sorting**: isort (profile: black)
- **Linter**: Ruff (E, W, F, I, B, C4, UP rules; E501 ignored)
- **Type checking**: mypy strict mode (`disallow_untyped_defs = true`)
- Target Python 3.9+
- Config in `pyproject.toml`

### TypeScript/JavaScript
- **Strict mode** TypeScript (`apps/web/tsconfig.json`)
- **ESLint** with Next.js rules (shared config in `packages/eslint-config/`)
- **Tailwind CSS** for styling
- Path alias: `@/*` maps to `src/*`

## Testing

### Python (pytest)
- Config: `pyproject.toml` `[tool.pytest.ini_options]`
- `pythonpath = src`, `testpaths = tests`
- Async mode: `asyncio_mode = "auto"`
- Markers: `unit`, `integration`, `slow`, `asyncio`, `database`, `security`, `e2e`, `performance`
- Coverage target: 90% minimum, source: `src/youtube_extension`

### Frontend
- Tests in `apps/web/src/components/__tests__/` and `apps/web/src/__tests__/`

## Architecture Notes

- **Event-driven**: Events follow `<domain>.<entity>.<action>` naming (e.g. `youtube.video.captured`)
- **Dependency injection**: Service container pattern in `backend/containers/`
- **Multi-provider AI**: Routes to Gemini, OpenAI, Anthropic, or Grok
- **MCP integration**: Agent orchestration via Model Context Protocol
- **Database**: SQLite (dev), PostgreSQL (prod); migrations via Alembic
- **Auth**: NextAuth.js (frontend), python-jose (backend)
- **Monorepo**: Turbo for JS workspaces (`apps/*`, `packages/*`, `mcp-servers/*`)

## Key Policies

- **REAL_MODE_ONLY**: No mock delays, fake data, or simulated responses in production code
- **No secrets in code**: All keys/credentials go in `.env` (gitignored)
- **Security**: Validate inputs via Pydantic; no `dangerouslySetInnerHTML` in React; sanitize subprocess args
- **Type safety enforced**: mypy strict (Python), TypeScript strict (frontend)

## SDK ↔ Backend Contract Alignment

`sdk/python/eventrelay_sdk/types.py` must stay in sync with `src/youtube_extension/backend/api/v1/models.py`.

**Rules:**
- The backend `models.py` is the source of truth — never infer SDK types from test behaviour or API docs alone.
- When a test fails with `ValidationError`, fix the test mock to match the real response shape; do not weaken the SDK type (e.g., making required fields `Optional`).
- Enum fields (e.g., `job_status: Optional[JobStatus]`) must use the SDK enum type, not `str`.
- After any change to backend response models, audit the corresponding SDK model for drift.

**Verify alignment with:**

```bash
# Backend source of truth
grep -A 30 "class TranscriptActionResponse" src/youtube_extension/backend/api/v1/models.py
# SDK model
grep -A 30 "class TranscriptActionResponse" sdk/python/eventrelay_sdk/types.py
```

## Anthropic SDK Version

The project requires `anthropic>=0.78.0`. This floor guarantees:
- `thinking={"type": "adaptive"}` (adaptive thinking, no `budget_tokens`) — introduced in 0.78.0
- `output_config={"effort": "..."}` (GA effort control, no beta header) — introduced in 0.75.0
- Current model string: `claude-opus-4-8` (no date suffix)

Do not add `try/except TypeError` fallbacks around these parameters — if the SDK is too old the install constraint is wrong, not the call site.
