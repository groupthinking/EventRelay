# Grok Build Terminal — sync note (2026-06-18)

**Canonical prod branch:** `origin/main` (after PR #315 merges)  
**Session:** UX surface clarity + pipeline health checks

## Stop doing this

The other terminal was polling **sync** `POST /api/pipeline` (no `async`) in a loop. That always returns **`local-fallback partial`** within ~8–60s and does **not** prove backend health.

```bash
# BAD — do not use for health checks
curl -X POST 'https://uvai.io/api/pipeline' \
  -H 'content-type: application/json' \
  --data '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}'
```

## Use instead

### 1. Async kickoff (fast backend health)

```bash
curl -sS -X POST 'https://uvai.io/api/pipeline' \
  -H 'content-type: application/json' \
  --data '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw","async":true}'
```

Expect: `pipeline: backend-async`, non-null `job_id`, `status: pending`.

### 2. Full production smoke (stream + async + SSE)

```bash
bash scripts/deployment/production_smoke.sh
```

### 3. Live UI analysis

- **Dashboard:** `POST /api/pipeline/stream` (SSE) — real agent progress
- **Studio (`/`):** local planning **drafts only** — not full pipeline
- **Prototype:** scripted design preview — not production APIs

## Product surface map

| URL | Backend | User-facing label |
|-----|---------|-------------------|
| `/` Studio | Async kickoff check + local draft package | Draft only (amber) unless backend-async OK |
| `/dashboard` | `/api/pipeline/stream` + enrichment fallback | Live pipeline; **PARTIAL** if thin data |
| `/prototype` | None (scenarios) | Design preview |
| `/dashboard/agents` | Live / Serverless / Demo (see header badge) | Agent graph |

## Known backend limitation

`POST api.uvai.io/api/v1/video-to-software` can return **524** on long runs. Dashboard may show **COMPLETE** with empty transcript/actions until `transcript-action` returns richer payloads. Cloud Run revision in use during audit: `uvai-backend-00018-rvn`.

## Shipped in this deploy stack

- Studio: no misleading green Ready on fallback; Dashboard handoff link
- Dashboard: thin-stream enrichment via `/api/video`; PARTIAL badge
- Prototype + Nav: design-preview clarity
- PR: #315 (UX + Sentry AI monitoring + Whisper fallback stack)