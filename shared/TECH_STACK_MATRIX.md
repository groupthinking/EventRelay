# Tech Stack Matrix

**Last Updated:** December 21, 2024
**Status:** Active

---

## Project Comparison

| Feature | EventRelay | netmesh-production | MCP Servers | self-correcting-executor |
|---------|------------|-------------------|-------------|--------------------------|
| **Core Type** | Monorepo (Turbo) | Standalone App | Distributed | Docker Container |
| **Backend** | Python (FastAPI) | Cloudflare Workers (Hono) | Express / Python | Python (FastAPI) |
| **Frontend** | React 18.2.0 (CRA) | React 19.1.1 (Vite) | N/A | React (Unknown ver) |
| **Styling** | MUI v7 + Tailwind v3 | Tailwind v4 + shadcn | N/A | TBD |
| **Database** | Postgres / SQLite | D1 (SQLite) | SQLite | Postgres / Redis |
| **ORM** | SQLAlchemy / Prisma | Drizzle | N/A | SQLAlchemy |
| **Language** | Python / TypeScript | TypeScript | TS / Python | Python / TS |

---

## Version Consistency Check

| Library | Version A (EventRelay) | Version B (netmesh) | Status | Recommendation |
|---------|------------------------|---------------------|--------|----------------|
| **React** | `18.2.0` | `19.1.1` | ⚠️ Mixed | Standardize on **18.x** for stability |
| **TypeScript** | `4.9.5` | `5.9.2` | ⚠️ Mixed | Upgrade EventRelay to **5.x** |
| **Tailwind** | `3.4.17` | `4.1.13` | ⚠️ Mixed | Plan migration to **v4** long-term |
| **Build Tool** | CRA (Webpack) | Vite 6 | ⚠️ Mixed | Migrate EventRelay to **Vite** |
| **Express** | N/A | N/A | v4/v5 Mixed | Standardize MCP on **v5** |

---

## Tech Debt Scorecard

### EventRelay
- **Score:** 6/10 (C)
- **Issues:** Outdated TS, mixed React versions, complex styling (3 systems), heavy dependency on CRA.
- **Plan:** Upgrade TS -> Standardize React -> Migrate to Vite.

### netmesh-production
- **Score:** 9/10 (A)
- **Issues:** None major. Bleeding edge stack (React 19, Tailwind v4).
- **Role:** Reference implementation for modern standards.

### MCP Ecosystem
- **Score:** 5/10 (D)
- **Issues:** lack of standardization, mixed Express versions, folder bloat (genkit).
- **Plan:** Consolidate into monorepo, remove bloat.

---

## Standards Definition

- **Frontend:** React 18, Vite, Tailwind, TypeScript 5.x
- **Backend (Serverless):** Cloudflare Workers, Hono, Drizzle
- **Backend (Service):** Python FastAPI, SQLAlchemy, Pydantic
- **Agent Communication:** MCP Protocol (standardized SDKs)
