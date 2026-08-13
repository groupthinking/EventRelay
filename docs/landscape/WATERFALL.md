# UVAI landscape research — gated waterfall

**Track:** side research only. Branch `research/uvai-landscape`.
**Does not ship product.** No merge to `main` until L3 skeptic + human accept.
**Product waterfall stays in** `~/BrainVault/UVAI-EventRelay-SSOT/14-MASTER-TRACKING.md`.

## Why this exists

EventRelay already has a serving product (`uvai.io` / `v0-uvai`). The machine also has years of adjacent code (`.uvai`, `.eventrelay`, `video-intelligence-workbench`, `YOUTUBE-EXTENSION`, BrainVault/Obsidian, Notion). External systems (Vision Agents, Stream, Inworld, Anam, Hermes, S-EMBER, VidaForge, Genkit, Chromium audio, ml5, karpathy) are comparison sources, not a license to rewrite EventRelay from scratch.

**End goal of this track:** one evidence-backed *proposed* folder structure and integration map. Not a second product, not a new orchestration framework.

## Gates (do not skip)

| Gate | Must produce | Pass criteria | Fail / stop |
|------|----------------|---------------|-------------|
| **L0 Inventory** | One brief per source family | Path or URL visited; 5–12 facts with file/URL citations; no invented APIs | Skip a source only if path missing or URL 404, and say so |
| **L1 Compare** | EventRelay vs each family | Table: keep / adapt / ignore, with EventRelay path citations | No “rewrite EventRelay” without naming the exact gap |
| **L2 Propose** | `docs/landscape/proposed-structure.md` | Every new top-level dir maps to an L1 keep/adapt; no empty ceremony dirs | Blocked until L1 exists |
| **L3 Skeptic** | Independent refute of L2 | At least one over-build called out, or explicit “none, with evidence” | Fail if skeptic never read EventRelay `apps/` |
| **L4 Human** | Accept / reject / narrow | Written accept in SSOT or PR comment | No merge to `main` without this |

## Source families (L0 work list)

1. **EventRelay live** — `groupthinking/EventRelay`, `apps/web`, `docs/WORKFLOW_DEVKIT.md`, Vercel `v0-uvai`
2. **Local corpus** — `~/.uvai`, `~/Dev`, `~/video-intelligence-workbench`, `~/YOUTUBE-EXTENSION`, `~/.eventrelay`
3. **Memory** — `~/BrainVault` (Obsidian), Notion “UVAI / EventRelay Research SSOT” + “EventRelay — Live Launch Board”
4. **Video agents** — visionagents.ai, GetStream/vision-agents, getstream.io/video, inworld.ai
5. **Avatars / realtime** — anam.ai/interactive-avatars
6. **Data / models** — facebook/S-EMBER, VidaForge-3M, Hermes-3-Llama-3.1-8B
7. **Learn / runtime** — karpathy/build-nanogpt, ml5 neural-network, Chromium `audio_thread.h` + `browser_main_loop.cc`, genkit youtube summarize, qualiastudios.dev

## How to run

```text
/uvai-landscape-research          # orchestrator, all families
/uvai-source-brief source=...     # one family
/wdk-product-waterfall            # product gates (separate track)
```

## Anti-patterns

- Do not copy webpack/build trees into EventRelay.
- Do not create coordinator classes, discovery frameworks, or a second monorepo root.
- Do not start WDK C from this branch.
- Do not treat a READY Vercel preview as product proof.
