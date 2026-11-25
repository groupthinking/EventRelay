# UVAI — Gemini CLI Context

Read [AGENTS.md](AGENTS.md) first; its locked facts and scope override historical plans. Use [docs/NEXT-PHASE.md](docs/NEXT-PHASE.md) for the next authorized cut and [docs/MASTER_ROADMAP.md](docs/MASTER_ROADMAP.md) for the remaining build-out.

Repository layout, commands, code style, tests, and policies are in [AGENTS.md](AGENTS.md) and [README.md](README.md).

## MCP Extensions (configured in .gemini/settings.json)

The following MCP servers are pre-configured for Gemini CLI:

| Server | Purpose | Trust |
|---|---|---|
| `github` | GitHub repo management via `@github/github-mcp-server` | `false` — external npm package |
| `git-workflow` | Safe git operations (status/add/commit/pull/push) | `true` — local project code |
| `stitch` | Google Stitch HTTP MCP endpoint | `false` — remote HTTP service |

`trust: true` bypasses per-call confirmation prompts; use only for local project tools.
Environment variables (e.g. `$GITHUB_TOKEN`) are expanded by Gemini CLI from the shell environment.

Run `/mcp` inside Gemini CLI to verify connected servers and available tools.
