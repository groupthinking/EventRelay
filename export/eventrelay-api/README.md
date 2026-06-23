# EventRelay API

Paste a YouTube URL; get back a **transcript**, **typed events**
(`<domain>.<entity>.<action>`), and **derived artifacts** (summary, tasks,
insights) — over one small, job-centric HTTP contract. No agent mesh, no
workflow engine, no model keys in the client. One linear pipeline behind one
FastAPI app.

```
URL ──▶ ingest ──▶ transcript ──▶ extract_events ──▶ artifacts ──▶ store
        validate    fetch + STT     pure fn            pure fn        jobs+events
```

## Contract

| Method & path | Purpose |
|---|---|
| `POST /api/v1/jobs` | Submit a YouTube URL → `202 { job_id, status }` |
| `GET /api/v1/jobs/{id}` | Job status (`queued → running → succeeded/failed`) |
| `GET /api/v1/jobs/{id}/transcript` | Word-for-word transcript |
| `GET /api/v1/jobs/{id}/events` | Typed `<domain>.<entity>.<action>` events |
| `GET /api/v1/jobs/{id}/artifacts` | Summary + tasks + insights |
| `GET /api/v1/health` | Liveness + version |

The committed [`service/openapi.json`](service/openapi.json) is the source of
truth and the input to SDK generation (Stainless). Regenerate it with
`make openapi`.

## Quickstart

```bash
make install-dev          # editable install with dev + youtube + gemini + postgres extras
make test                 # in-memory store + fake providers; no DB/keys/network needed
make run                  # local server on :8080 (in-memory store)
```

For real runs, provide the model key (and a database for persistence):

```bash
export EVENTRELAY_GEMINI_API_KEY=...                                            # SC3/SC4 model seam
export EVENTRELAY_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/eventrelay  # SC6
make run
```

All configuration is environment-driven with the `EVENTRELAY_` prefix — see
[`.env.example`](.env.example).

## Persistence

Postgres via async SQLAlchemy — **two tables** (`jobs`, `events`). When
`EVENTRELAY_DATABASE_URL` is unset the in-memory store is used (tests/local).
Idempotency key = `video_id:pipeline_version`, so resubmitting the same URL
replays the existing job instead of recomputing.

## Deploy

Container image from [`service/Dockerfile`](service/Dockerfile); target is
Cloud Run. CI builds and deploys on push to `main` —
see [`.github/workflows/deploy-cloud-run.yml`](.github/workflows/deploy-cloud-run.yml).

```bash
make docker-build && make docker-run
```

## Architecture & provenance

This repository was extracted, intact and verified, from the EventRelay
monorepo's clean-spine service. The design rationale (why it shares no code
with the legacy implementation, what was deliberately *not* ported) lives in
[`service/README.md`](service/README.md). The success-criteria ledger and the
frontend cutover that made the UI a pure consumer of this contract are in
`docs/` of the originating repo.
