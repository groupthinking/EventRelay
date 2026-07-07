# Vercel AI & Developer Tooling Setup

This document covers how to wire up Vercel AI Gateway, the Vercel MCP server,
and IDE plugins for AI coding assistants working on EventRelay.

---

## 1. Vercel AI Gateway

### Required environment variables

```bash
# Add to the Vercel project (all environments) — consumed by apps/web at runtime
vercel env add AI_GATEWAY_API_KEY        # Your Vercel AI Gateway API key
```

Get `AI_GATEWAY_API_KEY` from: **Vercel Dashboard → AI → Gateway → API Keys**

> **Security note:** `VERCEL_TOKEN` is a personal access token used only by
> MCP tooling and CI — it must **not** be exposed to the app's runtime
> environment. See section 2 for where to configure it.

### Local development

```bash
# Copy .env.example and fill in values
cp .env.example .env
# Set AI_GATEWAY_API_KEY in your local .env
```

---

## 2. Vercel MCP Server

The Vercel MCP server exposes tools for listing deployments, fetching build
logs, and managing project env vars directly from AI coding assistants.

### Connection details

- **Transport**: SSE
- **URL**: `https://mcp.vercel.com`
- **Auth**: `VERCEL_TOKEN` (+ optional `VERCEL_TEAM_ID`)

`VERCEL_TOKEN` and `VERCEL_TEAM_ID` are **development/CI-scoped** secrets for the
MCP tooling only. Configure them in your local shell or CI secret store, **not**
as Vercel project runtime environment variables:

```bash
# Local shell / CI secret store (NOT the Vercel project runtime env)
export VERCEL_TOKEN=...       # Vercel personal access token
export VERCEL_TEAM_ID=...     # Vercel team ID (starts with team_)
```

---

## 3. Skills.sh (AI agent skill packs)

Install the Vercel agent skill pack so AI assistants understand Vercel-specific
patterns:

```bash
npx skills add vercel-labs/agent-skills
```

---

## 4. Vercel Plugin for IDE AI agents

For **Claude Code**, **GitHub Copilot Workspace**, or **Cursor**:

```bash
npx plugins add vercel/vercel-plugin
```

This gives the agent access to Vercel deployment status, preview URLs, and
environment variable management from within the IDE.

---

## 5. Full Vercel LLM documentation context

For comprehensive Vercel documentation in LLM context windows:

```txt
https://vercel.com/docs/llms-full.txt
```

Add this URL to your AI assistant's context files (`.cursorrules`,
`CLAUDE.md`, etc.) for up-to-date Vercel API and config reference.

---

## 6. Video generation

The `/api/video/generate` endpoint requires:
- `AI_GATEWAY_API_KEY` set with access to Google Veo 3.1
- A function `maxDuration` of 300s for the video route (declared in
  `apps/web/src/app/api/video/generate/route.ts` via `export const maxDuration = 300`).
  Note: `vercel.json` separately raises the `pipeline/stream` route to 240s;
  Fluid Compute is recommended for these long-running functions.

Model: `google/veo-3.1-generate-001`
