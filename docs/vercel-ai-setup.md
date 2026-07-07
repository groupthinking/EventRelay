# Vercel AI Setup

EventRelay can use Vercel for AI Gateway routing, preview-deployment E2E validation, and MCP-assisted project management.

## Required environment variables

- `AI_GATEWAY_API_KEY` — Vercel AI Gateway key (`vck_...`) for chat fallback, embeddings, and video generation
- `VERCEL_TOKEN` — Vercel access token for the MCP server and deployment automation
- `VERCEL_TEAM_ID` — Team scope used by the Vercel MCP server

Add them in the Vercel dashboard under **Project → Settings → Environment Variables** or with the CLI:

```bash
vercel env add AI_GATEWAY_API_KEY
vercel env add VERCEL_TOKEN
vercel env add VERCEL_TEAM_ID
```

## AI assistant tooling

- **Vercel MCP server** — direct account/project/deployment access from MCP-aware assistants: `https://mcp.vercel.com/sse`
- **Skills.sh package** — reusable Vercel-specific procedural skills for coding agents: `npx skills add vercel-labs/agent-skills`
- **Vercel plugin** — IDE/terminal plugin for Claude Code, Codex, Cursor, and similar agents: `npx plugins add vercel/vercel-plugin`

For AI assistants that support external documentation context, include:

- `https://vercel.com/docs/llms-full.txt`
- `https://vercel.com/docs/ai-gateway`
- `https://vercel.com/docs/production-checklist`

## Suggested workflow

1. Configure `AI_GATEWAY_API_KEY` in the Vercel project.
2. Add `VERCEL_AUTOMATION_BYPASS_SECRET` to GitHub Actions so E2E jobs can access protected previews.
3. Install the Vercel plugin / Skills.sh package in your coding agent of choice.
4. Use the Vercel MCP server to inspect projects, deployments, logs, and domains directly from the agent.
