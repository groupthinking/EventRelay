# One loop — architecture vs current

**Owner:** this session (CEO mandate 2026-08-14).  
**Live view:** `~/BrainVault/UVAI-EventRelay-SSOT/17-ONE-LOOP-LIVE.md`  
**Branch:** `feat/one-loop-studio`

## Intent (from sources, not from forcing new systems)

| Source | What we take | What we do not build |
|--------|----------------|----------------------|
| L4 accept | Five wires, Run = public `/api/pipeline/stream` | Fake `buildPackage` brief |
| Google Doc “UVAI MASTER FILE DUMP” | Digital Refinery: video → structured action (`docs/landscape/google-doc-deep-research.json`, `intent_match: false`) | ADK/LWP Virtual Ports, Ultron, OPA, canvas glyphs |
| Notion `approach` | Taskmaster: take action, not a chatbot | Enterprise fleet / contest theater as a second product |
| HF `ViralNow/uvai` | Timestamp-grounded events idea | NVIDIA AV-Skills 2.8M-row **noncommercial** trainer |
| Notion Launch Board | Studio “shipped” was the fake brief | Treating June P0s as live CI |

## Target (one product)

```
uvai.io (/ and /studio)
  paste YouTube
    → processVideo → POST /api/pipeline/stream (public)
    → transcript + events on the same page
    → Act (WDK video-to-actions)
    → Export (buildScaffoldPackage)
    → Deploy (session)
    → Library /dashboard (session)
```

Two trees only: `apps/web` + `src/youtube_extension`.

## Current vs target

| Surface | Before | After (this phase) |
|---------|--------|--------------------|
| `/` | Brochure that promised analysis, sent people to Dashboard | Same OneLoopStudio as `/studio` |
| `/studio` | 100ms OUTPUT_COPY draft | Live `processVideo` |
| `/dashboard` | The real loop, behind login | Library of the same store |
| Status | `job_id` = “live” + “open Dashboard” | live = transcript or events |
| Export | Fake JSON brief | `buildScaffoldPackage` |
| Save | `uvai.savedPackages` | `eventrelay-dashboard-v1` via processVideo |

## Phases (gated)

| Phase | Goal | Pass | Fail |
|-------|------|------|------|
| **P1 One face** | `/` and `/studio` run live stream; no fake brief | Tests + browser: paste URL shows transcript or honest empty | Status still says planning draft |
| **P2 Auth honesty** | Analyze public; save/deploy/library sign-in; 401 → login | Manual: deploy unauth redirects | Hidden 401 as “durable unavailable” |
| **P3 Act same run** | Act uses this transcript; extract-events when signed in | Act results render on the page | Second disconnected kickoff with no output |
| **P4 Hygiene** | Mark stale Launch Board rows; do not merge #227; ignore HF corpus | Board rows match reality | Deleting GitHub synced PR DB |

## Notion delete / keep

**Keep:** EventRelay Synced Database (GitHub PRs) — automated, useful.  
**Keep:** Research SSOT hub.  
**Do not delete:** GitHub PR sync.  
**Mark stale (do not treat as work):** “Studio shipped P0”, June `/api/video` key scare until re-verified, #227 NotebookLM 346k-line PR.  
**Ignore as product:** session-export child spam under SSOT (do not bulk-delete from here).

## Feedback loop

After each phase: print completed → compare to this table → if mismatch, re-run research on the gap, then fix.

**Next phase map:** [NEXT-PHASE.md](./NEXT-PHASE.md) · **Goal:** [GOAL.md](./GOAL.md) · Orchestrator `/uvai-one-loop-next`.
