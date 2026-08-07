# F8 — uvai.io vs EventRelay web ownership

**Decided:** 2026-08-04  
**SSOT (full evidence):** `/Users/garvey/BrainVault/UVAI-EventRelay-SSOT/11-F8-WEB-OWNERSHIP.md`

## Decision

| Role | Owner |
|------|--------|
| **Canonical product frontend** | **`apps/web`** in this repository |
| **Production domain `https://uvai.io`** | Vercel project **`v0-uvai`** (rootDirectory `apps/web`) |
| **GitHub `groupthinking/uvai.io`** (`package.json` name `next-enterprise`) | **Non-canonical** — freeze; no product feature work |

Root `vercel.json` already permanent-redirects `v0-uvai.vercel.app` and `event-relay-web.vercel.app` to `https://uvai.io`. The EventRelay GitHub homepage is `https://uvai.io`.

## Rules for agents

1. Ship UI/API product changes only under `apps/web`.
2. Do not open product PRs against `groupthinking/uvai.io`.
3. Local clone under `ALL VID-ANYTHING /uvai.io` is retired for product (see `RETIRED.md` there).

## Optional hygiene (not blocking)

- ~~Rename `apps/web` package~~ **done (F8a):** `eventrelay-web` (was `building-production-ai-infrastructure-platform`).
- Point `groupthinking/uvai.io` README at EventRelay if that remote is retained for history.
