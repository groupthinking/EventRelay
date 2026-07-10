# CONTROL — Read this first

**Operational source of truth lives here:**

| Priority | Document |
|----------|----------|
| 1 | [`docs/control-plane/00-CEO-DIRECTIVE.md`](docs/control-plane/00-CEO-DIRECTIVE.md) |
| 2 | [`docs/control-plane/plans/EXECUTION-PLAN.md`](docs/control-plane/plans/EXECUTION-PLAN.md) |
| 3 | [`docs/control-plane/inventory/LIVE-STATUS.md`](docs/control-plane/inventory/LIVE-STATUS.md) |
| 4 | [`docs/control-plane/inventory/SURFACES.md`](docs/control-plane/inventory/SURFACES.md) |

**Rules in one line:** Assume nothing works until live-proven. No product code until GATE-0/1. One product path: this repo → Vercel `v0-uvai` (`apps/web`) + `api.uvai.io` on GCP `uvai-730bb`.

**Do not trust without re-verify:** root `ARCHITECTURE.md`, `docs/refactor/STATE.md`, `shared/_core/SYSTEM_STATUS.md`, Drive concept PDFs, empty `packages/*`, `src/vera` (pyc only).

**Owner next action:** complete GATE-3 launch config — Cloudflare Turnstile keys, Stripe webhook secret, Stripe price IDs, Google OAuth (see EXECUTION-PLAN GATE-3) — then trigger the GATE-4 Vercel deploy. (GATE-0 CLI auth is resolved via the `env -u GITHUB_TOKEN` / `env -u VERCEL_TOKEN` workaround.)
