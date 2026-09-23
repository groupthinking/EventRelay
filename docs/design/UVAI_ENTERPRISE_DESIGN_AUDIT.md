# UVAI Enterprise Design Audit

**Product surface:** UVAI Video Pack `/d/{videoId}` (chapters / SOP / chat)  
**Dogfood READY example:** `https://uvai.io/d/XYMcBrFSJ4c`  
**Repo:** groupthinking/EventRelay  
**Audit date:** 2026-09-20 (CDT)  
**Skill source:** bergside/awesome-design-skills → enterprise (skills.sh)  
**Prior artifact replaced:** Gemini stub zip (Drive `1SEuH7uLyYPxdDN4q7_wl_BNhXnSQd8Yg`, ~4.5KB static HTML claiming WebRTC/WhisperX)

---

## Executive summary

UVAI `/d` already ships a working Video Pack: chapters, SOP extraction, and chat against a processed video. The Gemini stub zip over-claimed (WhisperX ms tokens, live WebRTC, WCAG AAA) while delivering a non-interactive three-panel shell. This audit maps the **enterprise-design-system** skill onto the real `/d` surface, sets an honest competitive bar against Google-adjacent and creator tools, and phases UI work so **Claim ≠ PASS**.

**Hard rule for this program:** Studio remakes (Google AI Studio remix UIs, NotebookLM-style panels, Synthesia avatars) are **reference aesthetics and interaction patterns**, not ship targets. Shipping bar is the live EventRelay `/d` pack, not a clone of another product.

---

## 1. Competitive analysis

| Product | Primary job | Ease of use | Clear value in &lt;30s | Google-dev quality bar | Relevance to UVAI `/d` |
|---|---|---|---|---|---|
| **Google AI Studio remix** | Prompt → multimodal playground | Very high (single canvas, model picker) | Instant generation feedback | Excellent tokens, calm density, predictable chrome | Inspiration for density + model/status chips — **not** a Video Pack target |
| **NotebookLM** | Source-grounded Q&A + audio overview | High (sources rail + chat) | “Ask this corpus” is obvious | Strong empty/loading states, citation UX | Citation / grounding patterns map to SOP + chat citations |
| **Synthesia** | Avatar video generation | Medium (template wizard) | Clear “talking avatar” outcome | Marketing polish &gt; engineering density | Weak overlap; avoid avatar-first framing for `/d` |
| **OpusClip** | Long → short clips | High (upload → clips) | Clip grid sells itself | Creator-tool polish, not enterprise telemetry | Chapter/clip affordances inform chapter rail, not agent MCP |
| **Vertex GenMedia** | Cloud GenAI media APIs | Low–medium (console + SDK) | Value is API/docs, not UI | Console is Google-dev baseline: tokens, tables, ops | Ops/telemetry density target for Agent/MCP rail |
| **UVAI `/d` (today)** | Video → Pack (chapters, SOP, chat) | Medium (READY packs clear; processing opaque) | Strong when READY; weak during PARTIAL/FAILED | Functional; needs enterprise tokens, transcript sync, telemetry density | **Ship surface** — upgrade in place |

### Ease of use + clear value (UVAI gap)

1. **READY packs** already communicate value (chapters + SOP + chat). Keep that loop sacred.
2. **PARTIAL / FAILED** states need enterprise status chips and progressive disclosure — not silent empty panels.
3. **Transcript ↔ playback sync** is the highest-ROI “Google-dev quality” leap: click word → seek, active word highlight, keyboard transport.
4. **Agent/MCP telemetry** should read like Vertex console density: cards, tool log, expandable payloads — not pastel toy dashboards.

### Quality bar (what “Google developer relations would approve” means)

- Dark enterprise surface (`#09090b` / `#111827` / `#1f2937`), high contrast text (`#fafafa` on dark), IBM Plex Sans, 8pt grid.
- WCAG **2.2 AA** (measured contrast, focus-visible, reduced-motion). Do **not** claim AAA without audit evidence.
- No pastel gradients, no unverified “realtime WebRTC live” badges.
- Simulated research features labeled **SIMULATED** / **EXAMPLE DATA**.

---

## 2. Enterprise design-system skill → UVAI panel mapping

| Skill concept | Token / pattern | UVAI `/d` panel | Implementation note |
|---|---|---|---|
| Surface / canvas | `--surface: #09090b` | App chrome, page bg | Replace ad-hoc darks |
| Elevated | `--elevated: #111827` | Header, panel heads, transport bar | Sticky chrome |
| Panel | `--panel: #1f2937` | Cards, chips, tool rows | Agent cards, MCP rows |
| Border | `--border: #374151` | 1px separators, 8pt gaps | Grid gutters via 1px border bg |
| Primary | `--primary: #0C5CAB` / hover `#0a4a8a` | Primary CTAs, active scrubber | Brand blue (not cyan-as-primary) |
| Accent | `--accent: #38bdf8` | Highlights, active word, bbox stroke | Secondary emphasis |
| Semantic | success `#10b981`, warning `#f59e0b`, danger `#ef4444` | READY / PARTIAL / FAILED chips | Status only — not decoration |
| Text / muted | `#fafafa` / `#9ca3af` | Body + meta | Meta never below AA on surface |
| Type | IBM Plex Sans | All UI chrome | Load via Google Fonts CDN in demo; self-host in prod |
| Density | 8pt grid | Padding 8/16/24; row heights 32/40 | Compact but calm |
| Focus | `:focus-visible` ring (accent) | All controls | Keyboard Space / arrows |
| Motion | `prefers-reduced-motion` | Bbox animation, VAD meter | Fall back to static frames |
| Progressive disclosure | Expand/collapse | MCP tool log payloads | Default collapsed |
| Empty / loading / error | Explicit states | All three columns | Demo-togglable for QA |

### Depth map by column (target `/d` shell)

```
┌──────────────┬─────────────────────────────┬──────────────────────┐
│ Agent / MCP  │ Video viewport + bbox       │ Transcript + events  │
│ rail         │ + transport                 │ stream               │
├──────────────┼─────────────────────────────┼──────────────────────┤
│ Extract /    │ Playback clock (rAF)        │ Word-level list      │
│ Pack /       │ Scrubber + Space/←→         │ Active word seek     │
│ Verify cards │ SVG/canvas bbox (flagged)   │ Event stream rows    │
│ MCP tool log │ WebRTC btn → SIMULATED VAD  │ Empty/loading/error  │
└──────────────┴─────────────────────────────┴──────────────────────┘
```

---

## 3. Honest phased roadmap

| Phase | Scope | Ship claim | Pass criteria |
|---|---|---|---|
| **P0** | Design tokens + `/d` shell (3-column enterprise chrome) | **Ship** tokens + layout to `/d` | Tokens as CSS vars; IBM Plex; AA contrast; focus rings; reduced-motion |
| **P1** | Transcript sync UI | **Ship** word highlight + click-seek + keyboard transport | Simulated or real transcript JSON; clock sync via rAF; Space/arrows |
| **P2** | Bounding-box overlays | **Behind feature flag**; EXAMPLE DATA until perception pipeline is real | Timed SVG/canvas boxes; badge “EXAMPLE DATA”; flag off by default in prod |
| **P3** | WebRTC research spike | **No ship claim** — demo SIMULATED VAD + latency only | Spike doc + simulated UI; never badge “live RTC” without real media path |
| **P4** | Agent / MCP telemetry density | **Ship** cards + tool log progressive disclosure | READY\|PARTIAL\|FAILED chips; expandable MCP log; empty/loading/error |

### Explicit non-claims

- **Claim ≠ PASS.** Marketing copy or Studio screenshots do not count as acceptance.
- WhisperX millisecond alignment is a **future perception dependency**, not a UI-complete feature.
- WebRTC &lt;300ms turn-taking is a **research spike**, not shipping on `/d`.
- WCAG AAA is **out of scope** until a measured audit; target is **WCAG 2.2 AA**.
- Google AI Studio / NotebookLM remakes are **not** release blockers or product definitions.

---

## 4. Gap vs Gemini stub (Drive ~4.5KB)

| Stub claim | Reality | This program |
|---|---|---|
| “Realtime Video Feed Active” | Static HTML, no clock | rAF playback clock |
| “WhisperX millisecond tokens” | No transcript list | Word list + sync (P1); WhisperX backend phased |
| “WebRTC Audio Session” button | No session, no VAD | SIMULATED meter (P3 spike) |
| WCAG AAA | Unmeasured | WCAG 2.2 AA target |
| Agent swarm online | Static green dots | Status chips + MCP log (P4) |

---

## 5. Recommended acceptance for engineering (summary)

See companion `GITHUB_ISSUE.md` for the paste-ready issue. Demo at `electron-demo/` implements every checklist item as an interactive prototype (browser or Electron).

**Related (not dependency):** EventRelay PR #1971 — track for adjacency only; this design program does not block on it.

---

## 6. References

- Live dogfood: https://uvai.io/d/XYMcBrFSJ4c  
- Skill: https://skills.sh / bergside/awesome-design-skills / enterprise  
- Stub Drive zip: `1SEuH7uLyYPxdDN4q7_wl_BNhXnSQd8Yg`  
- Repo: groupthinking/EventRelay  
