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

All seven criteria are now wired end to end:

- **SC1** URL validation · **SC5** single app + clean contract · **SC6**
  idempotent Job+Event lifecycle over Postgres.
- **SC2** captions transcript (youtube-transcript-api) + injectable STT fallback.
- **SC3** event extraction and **SC4** artifact derivation run against the
  single **model seam** (`app/llm/`), Gemini by default.
- **SC7** the frontend is now a pure consumer of this contract: its second
  backend (`apps/web/src/app/api/*`) and the direct-model `lib/` fallbacks are
  deleted, and the dashboard reads everything through `eventRelay.*`. The one
  remaining (non-blocking) follow-up is regenerating the TS SDK from
  `service/openapi.json` via Stainless to replace the hand-written client.

The live YouTube and model calls require network + an API key and so are not
exercised in CI; the 18-test suite drives the full lifecycle with the
transcript provider and model seam replaced by dependency-injected fakes. No
production path fakes success (REAL_MODE_ONLY) — a misconfigured or failing
stage lands on the job as `failed`.

### The model seam (`app/llm/`)

One interface — `LLMClient.generate_json(system, prompt, schema)` — with the
provider behind it. `GeminiLLMClient` is the default; Anthropic/OpenAI are
drop-in by implementing the same method and swapping it in the container. This
replaces the legacy repo's five competing model seams.

## Run it

```bash
pip install "fastapi>=0.110" "uvicorn[standard]" "pydantic>=2.5" pydantic-settings \
            "sqlalchemy>=2.0" httpx pytest

# tests (in-memory store + fake providers; no DB/keys/network needed)
pytest service/tests -v -o addopts=""   # -o addopts="" skips the repo-root --cov gate

# local server (in-memory store). For real runs also:
#   pip install youtube-transcript-api google-genai
export EVENTRELAY_GEMINI_API_KEY=...                 # SC3/SC4 model seam
export EVENTRELAY_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/eventrelay  # SC6
uvicorn service.app.main:app --reload --port 8080
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

FastAPI generates the OpenAPI document from `app/api/v1/schemas.py`. The
generated document is committed at **`service/openapi.json`** (6 paths, titled
"EventRelay API") and is the source of truth and input to Stainless SDK
generation. Regenerate it with:

```bash
python -c "import json; from service.app.main import app; print(json.dumps(app.openapi(), indent=2))" > service/openapi.json
```

It does **not** overwrite the legacy 40-path `openapi/eventrelay.openapi.json`
(still titled "YouTube Extension API") — that remains the live API's contract
until the SC7 frontend cutover (strangler migration), at which point it is
replaced and the SDKs are regenerated from `service/openapi.json`.

## Frontend (SC7)

`apps/web` is now a **pure SDK consumer**. Its server-side
`apps/web/src/app/api/*` route handlers and the direct-Gemini/OpenAI fallbacks
in `lib/` — a second backend — have been removed; the dashboard store talks to
this service through `lib/eventrelay-client.ts` only. The synthetic multi-agent
visualization (a REAL_MODE_ONLY violation) is gone with it. See
[`docs/SC7_CUTOVER.md`](../docs/SC7_CUTOVER.md) for the executed teardown.
