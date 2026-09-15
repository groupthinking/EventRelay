# UVAI — Gemini CLI Context

Read [AGENTS.md](AGENTS.md) first; its locked facts and scope override historical plans. Use [docs/NEXT-PHASE.md](docs/NEXT-PHASE.md) for the next authorized cut and [docs/MASTER_ROADMAP.md](docs/MASTER_ROADMAP.md) for the remaining build-out.

## Project Overview

UVAI (Universal Video Action Intelligence) turns a YouTube URL into a hashed Video Pack and grounded build rails. EventRelay is the internal Python/FastAPI runtime and repository name, not a public product. The web app uses Next.js App Router, React, and TypeScript. `/` is the entry page; `OneLoopStudio` at `/studio` is the workbench. Legacy `/dashboard` skins redirect there.

## Single Workflow

**One product loop:** YouTube URL → Video Pack → inspect evidence and build rails → export / act / attempt to ship. Do not introduce a parallel product or bypass evidence gating. A generated evidence workspace is not proof of recreating or deploying the source app.

Origin G.A.T.E. is the only authorized next cut. Mission Workspace, Agent Factory, ExperienceOS, and held `asRecord` / claim work require the authority described in `AGENTS.md`.

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

# Run backend server (PYTHONPATH=src is required for absolute imports to resolve)
PYTHONPATH=src uvicorn youtube_extension.main:app --reload --port 8000

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
# Node.js >=22; packageManager is npm@10.8.0; root lockfile only
npm ci
npm run build
npm run dev
npm run lint
npm run test
npm --workspace=apps/web run type-check
```

## Code Style

### Python
- **Formatter**: Black, 88-char line length
- **Linter**: Ruff (E, W, F, I, B, C4, UP; E501 ignored)
- **Type checking**: mypy strict (`disallow_untyped_defs = true`)
- Target Python 3.10+; `pyproject.toml` is authoritative

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
- **Product AI**: Gemini 3.8 Flash via Vercel AI Gateway for Video Pack extraction; other providers remain in internal runtime paths
- **MCP integration**: internal orchestration via Model Context Protocol
- **Video Pack store**: Upstash REST only; Redis TCP and backend SQL are not the pack store
- **Other runtime data**: inspect the owning service before modifying SQLAlchemy / Alembic or auxiliary integrations
- **Auth**: existing NextAuth.js web configuration; backend middleware has a separate policy
- **Monorepo**: Turbo; root npm workspaces are `apps/*`, not every shared-code or MCP directory

## Key Policies

- **REAL_MODE_ONLY**: no mock delays or fake data in production code
- **No secrets in code**: all keys in `.env` (gitignored)
- **Security**: Pydantic input validation; no `dangerouslySetInnerHTML`; sanitize subprocess args
- **Type safety**: mypy strict (Python), TypeScript strict (frontend)
- **Minimal changes**: make surgical, precise modifications; never delete working code without justification

## Configuration boundaries

- Video Pack AI uses Vercel AI Gateway; inspect the current extractor and runtime configuration instead of requiring every legacy provider key.
- Production packs require `KV_REST_API_URL` + `KV_REST_API_TOKEN`, or the equivalent `UPSTASH_REDIS_REST_*` pair.
- Backend-dependent actions use `BACKEND_URL` plus the backend's own configured credentials. Missing configuration is not evidence of a successful action.
- Auth, billing, and CLI/MCP credentials belong to their existing integrations. Never print secrets or commit environment files.
- Inspect `.gemini/settings.json` and run `/mcp` before assuming an optional tooling service is connected. See [README.md](README.md) for the current development path.
