# UVAI — Claude Code Context

Read [AGENTS.md](AGENTS.md) first. Its locked product facts and scope take precedence over historical plans. The current execution boundary is [docs/NEXT-PHASE.md](docs/NEXT-PHASE.md); the evidence-based build-out plan is [docs/MASTER_ROADMAP.md](docs/MASTER_ROADMAP.md).

Repository layout, commands, code style, tests, and policies are in [AGENTS.md](AGENTS.md) and [README.md](README.md).

### Frontend (Next.js)

```bash
# Node.js >=22; packageManager is npm@10.8.0; root lockfile only
```

## Key Policies

- **Protected previews**: E2E reaches Vercel deployment-protected previews with `VERCEL_AUTOMATION_BYPASS_SECRET` forwarded as `x-vercel-protection-bypass`. Do not send `x-vercel-set-bypass-cookie` from stateless test clients; it creates redirect loops instead of a durable session.
- **E2E Attribution**: Synthetic requests must carry `X-EventRelay-Probe: e2e` and `User-Agent: EventRelay-E2E/<run-id>` to enable Vercel log filtering. The proxy emits bounded `e2e_probe_request` events; these headers are observability-only and do not authorize access or bypass limits.
- **Vercel Filesystem**: The `/var/task` environment is read-only. Do not write persistent data to local disk.
- **Preview Verification**: Missing PR previews fail closed. Do not fall back to production.

## Anthropic SDK Version

The project requires `anthropic>=0.105.0` (see `pyproject.toml`). This floor guarantees:
- `thinking={"type": "adaptive"}` (adaptive thinking, no `budget_tokens`) — introduced in 0.78.0
- `output_config={"effort": "..."}` (GA effort control, no beta header) — introduced in 0.75.0
- Current model string: `claude-opus-4-8` (no date suffix)

Do not add `try/except TypeError` fallbacks around these parameters — if the SDK is too old the install constraint is wrong, not the call site.
