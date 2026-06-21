# Vercel AI & Developer Tooling Setup

This document covers how to wire up Vercel AI Gateway, the Vercel MCP server,
and IDE plugins for AI coding assistants working on EventRelay.

---

## 1. Vercel AI Gateway

### Required environment variables

```bash
# Add to Vercel project (all environments)
vercel env add AI_GATEWAY_API_KEY        # Your Vercel AI Gateway API key
vercel env add VERCEL_TOKEN              # Your Vercel personal access token
vercel env add VERCEL_TEAM_ID            # Your Vercel team ID (starts with team_)
```

Get `AI_GATEWAY_API_KEY` from: **Vercel Dashboard → AI → Gateway → API Keys**

### Local development

```bash
# Copy .env.example and fill in values
cp .env.example .env
# Set AI_GATEWAY_API_KEY in your local .env
```

---

## 2. Vercel MCP Server

The Vercel MCP server is registered in `src/mcp/mcp_registry.json`. It exposes
tools for listing deployments, fetching build logs, and managing project env vars
directly from AI coding assistants.

### Connection details

- **Transport**: SSE
- **URL**: `https://mcp.vercel.com/sse`
- **Auth**: `VERCEL_TOKEN` + `VERCEL_TEAM_ID` env vars (set above)

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

```
https://vercel.com/docs/llms-full.txt
```

Add this URL to your AI assistant's context files (`.cursorrules`,
`CLAUDE.md`, etc.) for up-to-date Vercel API and config reference.

---

## 6. Video generation

The `/api/video/generate` endpoint requires:
- `AI_GATEWAY_API_KEY` set with access to Google Veo 3.1
- Vercel Fluid Compute or a function `maxDuration` of 300s (already configured in `vercel.json`)

Model: `google/veo-3.1-generate-001`
