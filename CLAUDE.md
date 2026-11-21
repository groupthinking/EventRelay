# UVAI — Claude Code Context

Read [AGENTS.md](AGENTS.md) first. Its locked product facts and scope take precedence over historical plans. The current execution boundary is [docs/NEXT-PHASE.md](docs/NEXT-PHASE.md); the evidence-based build-out plan is [docs/MASTER_ROADMAP.md](docs/MASTER_ROADMAP.md).

Repository layout, commands, code style, tests, and policies are in [AGENTS.md](AGENTS.md) and [README.md](README.md).

## Anthropic SDK Version

The project requires `anthropic>=0.105.0` (see `pyproject.toml`). This floor guarantees:
- `thinking={"type": "adaptive"}` (adaptive thinking, no `budget_tokens`) — introduced in 0.78.0
- `output_config={"effort": "..."}` (GA effort control, no beta header) — introduced in 0.75.0
- Current model string: `claude-opus-4-8` (no date suffix)

Do not add `try/except TypeError` fallbacks around these parameters — if the SDK is too old the install constraint is wrong, not the call site.
