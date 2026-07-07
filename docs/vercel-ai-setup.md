# Vercel AI Gateway & Tooling Setup

This document covers configuring Vercel AI Gateway, MCP server, and Skills.sh
for the EventRelay project.

## AI Gateway Configuration

The Vercel AI Gateway provides a unified endpoint for routing LLM calls to
multiple providers (OpenAI, Anthropic, Google) with built-in observability.

### Environment Variables

| Variable | Purpose | Where to set |
|----------|---------|--------------|
| `AI_GATEWAY_API_KEY` | Vercel AI Gateway key (vck_…) | Vercel Dashboard or `.env.local` |
| `VERCEL_TOKEN` | Personal access token for Vercel MCP | Shell environment |
| `VERCEL_TEAM_ID` | Team/org ID (optional) | Shell environment |

### Setting via Vercel CLI

```bash
# Add AI Gateway key to the Vercel project
vercel env add AI_GATEWAY_API_KEY production preview development
```

### How It Works

1. When `AI_GATEWAY_API_KEY` is set and `BACKEND_URL` is unset, `/api/chat`
   falls back to Vercel AI Gateway using the `ai` SDK's `streamText`.
2. `/api/video/generate` always routes through the AI Gateway for video
   generation using Google Veo 3.1.
3. The existing `vercel-ai-gateway.ts` module provides raw fetch-based access
   for embeddings and chat completions (used by event extraction).

## Vercel MCP Server

The Vercel MCP server allows AI assistants to interact with your Vercel account.

### Setup

Already configured in `.gemini/settings.json`. Requires `VERCEL_TOKEN` in env.

Capabilities:
- Search Vercel documentation
- List and manage projects
- View deployment details and logs
- Check domain availability

## Skills.sh

Install reusable AI agent skills for enhanced Vercel integration:

```bash
npx skills add vercel-labs/agent-skills
```

### Vercel Plugin for Coding Agents

Connect Claude Code, Codex, Cursor, or Roo Code to the AI Gateway:

```bash
npx plugins add vercel/vercel-plugin
```

## IDE Integration

### Cursor / Windsurf

A `.cursorrules` file is included at the repository root. It points AI assistants
to the Vercel docs context at `https://vercel.com/docs/llms-full.txt`.

### Claude Code

Use the WebFetch tool to pull Vercel context:
```
fetch https://vercel.com/docs/llms-full.txt
```

Or reference the Vercel MCP server configured in `.gemini/settings.json`.
