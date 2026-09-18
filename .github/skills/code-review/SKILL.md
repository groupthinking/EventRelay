---
name: code-review
description: >-
  Context-aware code review checklist for EventRelay. Use this whenever
  reviewing a pull request or diff in this repository, so feedback is
  tailored to EventRelay's single-workflow architecture, Python/FastAPI and
  Next.js/TypeScript stacks, MCP agent integration, and repo-specific test
  and security conventions instead of generic advice.
---

# EventRelay Code Review

Review diffs against the conventions this repo actually enforces, not generic
style opinions. Ignore trivial formatting nits already covered by `black`,
`ruff`, and ESLint/Prettier — focus on correctness, security, and consistency
with the patterns below.

## Before reviewing

1. Identify which parts of the repo the diff touches:
   - `src/youtube_extension/backend/` — FastAPI backend (`api/v1/`, `services/`,
     `models/`, `middleware/`)
   - `src/youtube_extension/mcp/` or `mcp-servers/` — MCP agent/tool servers
   - `apps/web/` — Next.js/TypeScript frontend
   - `sdk/python/eventrelay_sdk/` — Python SDK types
   - `.github/workflows/` — CI/CD
   - `tests/` — pytest suite (`unit/`, `integration/`, `fixtures/`, `workflows/`)
2. Read `AGENTS.md` / `CLAUDE.md` at the repo root for the current locked
   product rules before flagging anything as "wrong" — some things that look
   like bugs (e.g. `PYTHONPATH=src` imports, Upstash-only pack storage) are
   intentional, documented constraints.

## Single-workflow architecture

EventRelay has **one** workflow: YouTube link → transcript → extracted events
→ dispatched MCP agents → published outputs.

- Flag any new endpoint, UI, or script that introduces an alternate entry
  point, a manual trigger that bypasses event extraction, or a parallel
  "builder" flow not reachable from a YouTube URL.
- Flag agents that are invoked directly/manually instead of being spawned
  from extracted events via the coordinator.

## Backend (Python/FastAPI)

- Type hints are required (mypy strict, `disallow_untyped_defs = true`);
  flag new untyped `def`s in `src/`.
- Request/response models must be Pydantic; flag hand-rolled dict validation
  in route handlers.
- `sdk/python/eventrelay_sdk/types.py` must stay aligned with
  `src/youtube_extension/backend/api/v1/models.py`. If a PR changes one
  without the other, flag the drift. Enum-typed fields (e.g. `job_status`)
  must use the SDK enum, not a bare `str`.
- Flag `try/except TypeError` fallbacks added around Anthropic SDK
  `thinking={"type": "adaptive"}` or `output_config={"effort": ...}` calls —
  the SDK floor (`anthropic>=0.105.0`) already guarantees these exist.
- Flag use of raw SQL string interpolation; parameterized queries via
  SQLAlchemy are required.
- Alembic migrations live in `src/youtube_extension/backend/migrations`, not
  `infrastructure/database` — flag migrations added in the wrong location.
- New top-level `src` packages need an explicit coverage target added in
  `pyproject.toml`, or they silently don't count toward the 90% threshold.

## Frontend (Next.js/TypeScript)

- Flag `dangerouslySetInnerHTML` unless output is sanitized immediately
  before use.
- Flag new environment variables read via `process.env.*` in client code
  that don't use the `REACT_APP_`/`NEXT_PUBLIC_` prefix (whichever the
  surrounding file already uses) — unprefixed vars silently resolve to
  `undefined` at build time, not at review time.
- Check that new pages under retired surfaces (`/dashboard` and sibling
  skins) redirect into the canonical `/studio`, per `apps/web/next.config.js`.

## MCP / agents

- MCP servers must follow JSON-RPC 2.0 with proper error codes; flag
  ad-hoc error shapes that don't match `{"jsonrpc": "2.0", "error": {...}}`.
- Flag servers that read more context than their declared capabilities need
  (MCP servers should not "see into" other servers or the full conversation).
- Cross-check any new `mcp-servers.json` / `.github/mcp-servers.json` entry
  for a hardcoded token/secret instead of `${env:VAR_NAME}` interpolation.

## Tests

- Test video ID must be `auJzb1D-fag`. Flag any use of `dQw4w9WgXcQ`
  (banned — causes flaky/age-gated test failures).
- Flag `pyfakefs` or other fake-filesystem mocks; this repo uses real
  `tempfile`/`shutil` temp directories, cleaned up after the test.
- New backend features should include tests under `tests/unit/` or
  `tests/integration/`; flag untested new endpoints or services.

## Security

- No secrets/API keys/tokens committed to source; they must come from
  environment variables (`.env`, gitignored).
- Validate that new subprocess calls sanitize arguments (no unsanitized
  shell string concatenation).
- Flag new external dependencies that weren't checked against the GitHub
  Advisory Database, and license additions that aren't already covered by
  `allow-licenses`/`allow-dependencies-licenses` in
  `.github/workflows/dependency-review.yml`.

## What not to flag

- Pre-existing issues unrelated to the diff.
- Style already enforced by `black`/`ruff`/`isort` (Python) or
  ESLint/Prettier (TypeScript) — assume CI catches formatting.
- Intentional, documented repo conventions from `AGENTS.md`/`CLAUDE.md`
  (e.g. Upstash-only Video Pack storage, locked pricing values) unless the
  diff itself is trying to change that policy.
