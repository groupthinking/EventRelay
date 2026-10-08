# UVAI — Universal Video Action Intelligence

<!-- ✅ AI agent access verified: write/sync capability confirmed via test task resolution -->

[![CI](https://github.com/groupthinking/EventRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/groupthinking/EventRelay/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Paste a YouTube URL → inspect a hashed **Video Pack** → export grounded build rails → attempt to ship with evidence. The product is **UVAI** at [uvai.io](https://uvai.io); **EventRelay** is the internal runtime and repository name, not a second public product. The differentiator is action and shipping, not transcription.

## Start here

- [AGENTS.md](AGENTS.md): locked product, pricing, storage, and scope rules.
- [Repository map](docs/REPO_MAP.md): current entry points and where code lives.
- [Build-out roadmap](docs/MASTER_ROADMAP.md): inspected capabilities, remaining work, and acceptance criteria.
- [Next authorized cut](docs/NEXT-PHASE.md): Origin G.A.T.E.; later product work remains held.
- [G.A.T.E. contract](docs/gate-transition-contract.md): PASS, HOLD, REJECT, and ESCALATE.

## Current product path

```text
/ — URL entry and Get Pro
  → /studio — OneLoopStudio
  → hashed Video Pack — Gemini 3.8 Flash via Vercel AI Gateway
  → Upstash REST pack persistence
  → inspect transcript, visual evidence, SOP, and build rails
  → export / App Builder workspace / optional workflow actions
  → Attempt deploy → visible G.A.T.E. decision
```

`/dashboard` and its retired skins redirect to `/studio`; they are not separate products. App Builder's deterministic sandbox emitter produces a workspace displaying pack evidence. Exporting that workspace is not proof that the app shown in a video has been recreated, installed, tested, or deployed.

The existing Studio gate checks a returned HTTPS URL with a hostname before showing a live result. When a server-side HTTP probe succeeds (`deployment_http_probe` evidence), G.A.T.E. may treat the URL as reachable; it still does **not** establish provider-backed ownership without Origin attestation. See the [contract boundary](docs/gate-transition-contract.md#current-evidence-boundary) before making a live-success claim.

## Locked offers

| Offer | Price | Boundary |
| --- | --- | --- |
| Workflow Pro | $39/mo or $390/yr | Existing Get Pro checkout |
| Maintain | $199/mo per live product | Do not infer checkout availability |
| Ship | Per-job quote | Do not infer checkout availability |

Do not restore the retired EventRelay Pro catalog or invent additional products or prices.

## Development

Requirements come from [package.json](package.json) and [pyproject.toml](pyproject.toml): Node.js 22+, npm 10.8.0 as the pinned package manager, and Python 3.10+ for the internal backend.

From the repository root:

```bash
npm ci
npm run dev:web
```

Use the root npm lockfile; do not create an `apps/web/package-lock.json`. `/` is the public entry page and `/studio` is the workbench.

When the selected workflow needs the Python backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,youtube]'
PYTHONPATH=src python3 -m uvicorn youtube_extension.main:app --reload --port 8000
```

Local readiness checks now bootstrap the parent directory for sqlite URLs
(`DATABASE_URL` / `API_COST_DATABASE_URL`) so the default dev path
`sqlite:///./.runtime/app.db` does not require a manual `.runtime` mkdir first.

Set the web runtime's `BACKEND_URL` to the intended backend. A missing backend must produce an honest unavailable/handoff result, not a fabricated deployment receipt. Provider credentials and auth configuration stay in the environment, never in Git.

### Configuration boundaries

| Area | Configuration / source of truth |
| --- | --- |
| Video Pack extraction | Vercel AI Gateway; model defined in `apps/web/src/lib/video-pack-extractor.ts` |
| Production Video Pack storage | `KV_REST_API_*` or `UPSTASH_REDIS_REST_*` — canonical for **web and Python backend** (`er:videopack:v0:{source_hash}`). Local filesystem packs require `VIDEO_PACK_FILESYSTEM_STORE=1` (dev only). |
| Web authentication | Existing NextAuth configuration and `apps/web/src/lib/auth-paths.ts`; do not replace the auth stack as cleanup |
| Backend-dependent workflows | `BACKEND_URL` and the backend's own auth/provider configuration |
| Billing | Existing Stripe setup under `apps/web/src/lib/billing/`; keep server-side catalog validation |

Redis TCP URLs are **not** the Video Pack store. Backend SQL stores and auxiliary integrations serve other entities; they do not replace the locked Upstash REST pack contract. Direct provider keys used by legacy runtime paths are not a new requirement for every Studio user.

## Verification

Run focused tests for the changed surface, then the broader checks required by that change:

```bash
npm exec --workspace=apps/web -- vitest run src/lib/__tests__/gate-transition.test.ts src/lib/__tests__/emit-app-builder-sandbox.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/video-pack-store.test.ts src/app/api/video/sandbox/__tests__/route.test.ts
npm --workspace=apps/web run type-check
npm --workspace=apps/web run lint
npm run build:web
```

For backend model changes:

```bash
PYTHONPATH=src python3 -m pytest tests/unit/test_api_v1_models.py -v --override-ini='addopts='
```

Default video fixture: `auJzb1D-fag`. Preserve separately documented historical fixtures when checking their original cuts. A passing unit suite, generated bundle, or old smoke receipt is not a fresh production end-to-end result.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `apps/web/` | Next.js App Router product and server routes |
| `src/youtube_extension/` | Internal Python/FastAPI runtime |
| `src/agents/`, `mcp-servers/`, `tools/mcp/` | Internal orchestration and tooling |
| `sdk/` | Client SDKs; keep Python response types aligned with backend models |
| `packages/` | Shared code; root npm workspace membership is defined in `package.json` |
| `tests/`, `apps/web/src/**/__tests__/` | Backend and web verification |
| `docs/`, `scripts/`, `.github/` | Documentation, operational helpers, and CI |

## Contributing and deployment

Use a feature branch and reviewable Conventional Commits. Verify the actual diff, preserve unrelated state, and do not delete working code or historical evidence solely because it is old. Production promotion requires current receipts and operator authorization; this README is not a deployment approval.

See [CONTRIBUTING.md](CONTRIBUTING.md), the [production runbook](docs/deployment/VERCEL_PRODUCTION_RUNBOOK.md), and [AGENTS.md](AGENTS.md). Historical architecture documents are design records, not proof of today's implementation or service health.

## License

MIT — see [LICENSE](LICENSE).
