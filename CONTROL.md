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

**Owner next action:** fix GitHub + Vercel CLI auth (see EXECUTION-PLAN GATE-0), then say “GATE-0 auth done”.
