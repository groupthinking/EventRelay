# EventRelay — Clean Spine (`service/`)

A single linear pipeline service, grown against the success criteria in
[`docs/PORTING_PARAMETERS.md`](../docs/PORTING_PARAMETERS.md). This tree is the
intended replacement for the legacy `src/` implementation. It shares **no code**
with `src/`; capabilities are ported in only when traced to a success criterion.

> Default rule: everything in the legacy repo is **presumed residue** until
> traced to one of SC1–SC7. See the porting doc for the ledger.

## What it does

```
POST /api/v1/jobs            paste a YouTube URL  → 202 { job_id, status }   (SC1, SC6)
GET  /api/v1/jobs/{id}        job status lifecycle                            (SC6)
GET  /api/v1/jobs/{id}/transcript   word-for-word transcript                 (SC2)
GET  /api/v1/jobs/{id}/events       typed <domain>.<entity>.<action> events  (SC3)
GET  /api/v1/jobs/{id}/artifacts    summary + tasks + insights               (SC4)
GET  /api/v1/health
```

The pipeline is linear and the runner reflects that — there is no agent mesh,
MCP coordinator, or workflow engine:

```
URL ──▶ ingest(SC1) ──▶ transcript(SC2) ──▶ extract_events(SC3) ──▶ artifacts(SC4) ──▶ store(SC6)
        validate         fetch + STT          pure fn               pure fn             jobs+events
```

## Layout

```
service/
  app/
    main.py              # the one FastAPI() app (SC5)
    config.py            # one Settings object
    container.py         # DI container — the one pattern kept from legacy
    api/v1/
      schemas.py         # clean contract models → generates OpenAPI
      routes.py          # thin handlers; no business logic
    domain/events.py     # event taxonomy + Event model (SC3)
    pipeline/            # ingest / transcript / extract / artifacts / runner
    store/               # base (Protocol) · sqlalchemy_store (Postgres, SC6)
                         #   · memory (tests/local) · models (Job, Event)
  tests/test_smoke.py
  Dockerfile             # Cloud Run image
```

## Status

Implemented in the skeleton: **SC1** (URL validation), **SC5** (contract +
single app), **SC6** (idempotent job lifecycle + Postgres store).

Stubbed with `NotImplementedError` and tied to their criterion (port next):
**SC2** transcript, **SC3** event extraction, **SC4** artifacts. Until ported,
a submitted job correctly terminates as `failed` — the skeleton never fakes
success (REAL_MODE_ONLY).

## Run it

```bash
pip install "fastapi>=0.110" "uvicorn[standard]" "pydantic>=2.5" pydantic-settings \
            "sqlalchemy>=2.0" httpx pytest

# tests (uses the in-memory store; no DB needed)
pytest service/tests -v

# local server (in-memory store)
uvicorn service.app.main:app --reload --port 8080

# with Postgres (SC6 durable path)
export EVENTRELAY_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/eventrelay
uvicorn service.app.main:app --port 8080
```

## Persistence (SC6)

Postgres via async SQLAlchemy — **two tables** (`jobs`, `events`). The legacy
10-table multi-tenant/RLS/audit schema is not ported. Production uses Alembic
migrations; `SqlAlchemyJobStore.init_models()` is a local convenience only.
Idempotency key = `video_id:pipeline_version`, so resubmitting the same URL
replays the existing job instead of recomputing.

## Deployment

Cloud Run, from `service/Dockerfile`. This is the single chosen target; the
other five legacy targets (Firebase, Vercel-backend, Railway, root Dockerfiles,
Supabase) are residue.

## Contract & SDKs (SC5)

FastAPI generates the OpenAPI document from `app/api/v1/schemas.py`. That
generated document is the source of truth and the input to Stainless SDK
generation — it replaces the legacy 40-path `openapi/eventrelay.openapi.json`
(still titled "YouTube Extension API") once the spine takes over.

## Frontend (SC7)

`apps/web` is salvageable as a **pure SDK consumer**. Before reuse, delete its
server-side `apps/web/src/app/api/*` route handlers and the direct-Gemini
fallback in `lib/` — those are a second backend and must not survive the move.
