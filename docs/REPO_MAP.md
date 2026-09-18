# UVAI repository map

UVAI is the public product; EventRelay is the internal runtime and repository name. This map answers **where the current code lives**, not whether a deployed service is healthy. Locked rules remain in [AGENTS.md](../AGENTS.md).

## Current entry points

| Responsibility | Source |
| --- | --- |
| Public URL entry and Get Pro | [`apps/web/src/app/page.tsx`](../apps/web/src/app/page.tsx) |
| Canonical Studio route | [`apps/web/src/app/studio/page.tsx`](../apps/web/src/app/studio/page.tsx) |
| Workbench, same-run actions, deploy result | [`OneLoopStudio.tsx`](../apps/web/src/components/OneLoopStudio.tsx) |
| Public/authenticated API policy and dashboard redirect helpers | [`auth-paths.ts`](../apps/web/src/lib/auth-paths.ts) |
| Pack HTTP endpoint | [`api/video/pack/route.ts`](../apps/web/src/app/api/video/pack/route.ts) |
| Grounded model extraction | [`video-pack-extractor.ts`](../apps/web/src/lib/video-pack-extractor.ts) |
| Pack identity and format | [`video-pack.ts`](../apps/web/src/lib/video-pack.ts) |
| Upstash REST pack persistence | [`video-pack-store.ts`](../apps/web/src/lib/video-pack-store.ts) |
| Evidence-workspace emitter | [`emit-app-builder-sandbox.ts`](../apps/web/src/lib/emit-app-builder-sandbox.ts) |
| Sandbox HTTP endpoint | [`api/video/sandbox/route.ts`](../apps/web/src/app/api/video/sandbox/route.ts) |
| Four-way transition decision and hashed receipt | [`gate-transition.ts`](../apps/web/src/lib/gate-transition.ts) |
| Studio URL/result validation | [`studio-pipeline-status.ts`](../apps/web/src/lib/studio-pipeline-status.ts) |
| Workflow start/poll adapters | [`studio-workflow.ts`](../apps/web/src/lib/studio-workflow.ts) |

`/dashboard` is not a second workbench. G.A.T.E. currently gates Studio's displayed deployment outcome; it is not a builder, independent deployment probe, or project database.

## Top-level layout

```text
EventRelay/
├── apps/web/                  Next.js App Router product and server routes
├── apps/backend/              Backend workspace wrapper
├── src/youtube_extension/     Internal FastAPI backend and services
├── src/agents/                Internal agent implementations
├── mcp-servers/               Internal MCP implementations
├── tools/mcp/                 Repository tooling servers
├── packages/                  Shared code
├── sdk/                       Python and TypeScript clients
├── tests/                     Backend and integration tests
├── docs/                      Current guidance plus dated historical records
├── scripts/                   CI, development, deployment, maintenance helpers
├── infrastructure/            Deployment/infrastructure definitions
├── .github/                   CI and host-specific agent configuration
├── .claude/skills/            Repository skills, also usable through Grok compatibility
├── .grok/workflows/           Repository automation, not product lineage
└── AGENTS.md, CLAUDE.md,
    GEMINI.md                  Root policy and host-specific guidance
```

Directory presence does not establish an active deployment or npm workspace. Root [package.json](../package.json) currently declares `apps/*` as npm workspaces; use its scripts and root lockfile. Other stores and prototypes do not replace Upstash REST for Video Packs.

## Verification locations

- Web library tests: `apps/web/src/lib/__tests__/`.
- Web component tests: `apps/web/src/components/__tests__/`.
- Route tests: beside routes under `apps/web/src/app/api/`.
- Backend tests: `tests/`; API response models must stay aligned with `sdk/python/eventrelay_sdk/types.py`.
- Commands and requirements: [README.md](../README.md), [package.json](../package.json), [apps/web/package.json](../apps/web/package.json), and [pyproject.toml](../pyproject.toml).

## Documentation authority and history

| Document | Use |
| --- | --- |
| [MASTER_ROADMAP.md](MASTER_ROADMAP.md) | Current inspected baseline, proposed build-out, and acceptance criteria |
| [NEXT-PHASE.md](NEXT-PHASE.md) | Bounded next cut; Origin G.A.T.E. only under root authorization |
| [GOAL.md](GOAL.md) | Goal template for that approved cut |
| [gate-transition-contract.md](gate-transition-contract.md) | Existing contract, tests, and limits |
| [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) | Historical runtime/issue map, not current health |
| [video_to_gtm_architecture.md](video_to_gtm_architecture.md) | Historical March architecture proposal |
| [App Builder cut record](../apps/web/src/lib/app-builder-sandbox-PLAN.md) | Recorded second-video emit smoke; not a current deployment receipt |
| [Workflow catalog](../.github/workflows/README.md) | CI and automation navigation; inspect current workflow definitions before execution |

When a dated record conflicts with locked policy, preserve the record as history and follow the current policy. Do not add another competing roadmap.
