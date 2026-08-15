# Next phase — P3 Act same run

**Branch:** `feat/one-loop-studio`  
**Goal command:** see [GOAL.md](./GOAL.md)  
**Live view:** `~/BrainVault/UVAI-EventRelay-SSOT/17-ONE-LOOP-LIVE.md`

P1 is done (`/` and `/studio` call live `/api/pipeline/stream`).  
**P3 implement + verify passed** (`uvai-one-loop-next`, 2026-08-15). Remaining: optional OneLoopStudio `#act-results` test; P2 is audit-pass (no local secret).

## Goal

After Analyze, the same page can Act. Results render here. No second product, no ADK, no Rickroll. Fixture: `auJzb1D-fag`.

```
/goal After Analyze on / , Act on the same run shows tool results on that page. Fixture auJzb1D-fag. Do not add ADK/LWP. Do not use dQw4w9WgXcQ.
```

## Agents and workflows

Run one agent at a time, or the orchestrator.

| Agent | Workflow | Mode | Measurable pass | Fail |
|-------|----------|------|-----------------|------|
| **act-implementer** | `/uvai-p3-act` | read-write | `OneLoopStudio` Act uses the selected video’s transcript/events when present; results stay on `/` | Act only re-kicks URL with no on-page output |
| **act-verifier** | `/uvai-p3-verify` | read-only | Code + curl/browser evidence that Act start returns `runId` and the UI has an Act-results surface | No file read, or only a plan |
| **auth-auditor** | `/uvai-p2-auth` | read-only | `auth-paths.ts`: stream + video-to-actions public; studio-deploy gated; UI 401 → `/login` | Claims local 401 when `.env.local` has no `NEXTAUTH_SECRET` |
| **hygiene** | `/uvai-p4-hygiene` | read-write | Launch Board stale rows noted; GitHub synced PR DB **not** deleted | Deletes the synced PR database |
| **orchestrator** | `/uvai-one-loop-next` | gated | implement → verify (fail closed) → auth audit → hygiene | Continues after a failed verify |

## Order (do not skip)

```
P3 implement  →  P3 verify  →  P2 auth audit  →  P4 hygiene
```

P2 does **not** invent a local `NEXTAUTH_SECRET`. Production gate is already in `auth-paths.ts`.

## Out of scope this phase

ADK, LWP, Ultron, HF AV-Skills training, merging `research/uvai-landscape`, WDK C extras, deleting Notion GitHub sync.

## How to run

```
/goal After Analyze on / , Act on the same run shows tool results on that page. Fixture auJzb1D-fag. Do not add ADK/LWP. Do not use dQw4w9WgXcQ.
/workflow uvai-one-loop-next
```

One agent:

```
/uvai-p3-act
/uvai-p3-verify
/uvai-p2-auth
/uvai-p4-hygiene
```
