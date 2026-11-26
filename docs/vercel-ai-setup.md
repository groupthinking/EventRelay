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
> Vercel CLI, REST, and CI — it must **not** be exposed to the app's runtime
> environment. Vercel MCP does not use this PAT. See section 2.

### Local development

```bash
# Copy .env.example and fill in values
cp .env.example .env
# Set AI_GATEWAY_API_KEY in your local .env
```

---

## 2. Vercel MCP Server

The official Vercel MCP server (`https://mcp.vercel.com`) exposes tools for
listing deployments, fetching build logs, and managing projects from AI
coding assistants. It is **OAuth 2.1**, not a Vercel API PAT.

### Connection details

- **Transport**: Streamable HTTP
- **URL**: `https://mcp.vercel.com`
- **Auth**: OAuth 2.1 browser consent (Grok stores the grant in
  `~/.grok/mcp_credentials.json`)

This repo ships the Grok stub in `.grok/config.toml` as URL-only. Do **not**
add `Authorization: Bearer ${VERCEL_TOKEN}` — a static header makes Grok skip
its OAuth client, and `mcp doctor vercel` then fails with `invalid_token`.

```bash
# Already committed. Re-add only if the stub was deleted:
grok mcp add --transport http -s project vercel https://mcp.vercel.com

# Authorize (interactive TUI; headless doctor will not complete consent):
#   grok --cwd <EventRelay>
#   /mcps → vercel → i
```

`VERCEL_TOKEN` and `VERCEL_TEAM_ID` remain **CLI/REST/CI** secrets (Vercel
deploy scripts, `vercel` CLI). Configure them in your local shell or CI secret
store, **not** as Vercel project runtime environment variables, and **not** as
the Grok MCP Authorization header:

```bash
# Local shell / CI secret store (NOT the Vercel project runtime env, NOT Grok MCP)
export VERCEL_TOKEN=...       # Vercel personal access token (CLI/REST)
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

`POST /api/video/generate` was removed. It had no in-repo caller, and its rate
limiter failed open when Upstash credentials were missing. Video Pack
extraction stays at `POST /api/video/pack` and uses Gemini through
`AI_GATEWAY_API_KEY`.

The Vercel project's Root Directory is `apps/web`, so any deploy-level
overrides belong in `apps/web/vercel.json`, not the repository-root
`vercel.json`.
