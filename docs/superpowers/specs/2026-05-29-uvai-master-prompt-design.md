# Design Spec: UVAI Ecosystem Master Prompt (uvai-init Skill)

**Date:** 2026-05-29
**Status:** Implemented
**Skill path:** `~/.claude/skills/uvai-init/SKILL.md`
**Invocation:** `/uvai-init`

---

## Problem Statement

The `uvai-ecosystem-dev` skill provides architectural guidance but only names 5 of the 12+ UVAI
systems and lacks volatile operational data (model selection rules, GitHub contamination status,
env var checks). Developers starting a UVAI session have no single initialization ritual —
context is fragmented across CLAUDE.md, SESSION_HANDOFF.md, memory files, and the skill itself.

Without a session initializer, each session risks:
- Missing the GitHub contamination constraint and accidentally pulling from remote
- Using the wrong Gemini model (causing 400 errors)
- Skipping baseline validation at turning points
- Inconsistent understanding of which domain is canonical

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Format | Standalone SKILL.md | No global CLAUDE.md pollution; invoked only when needed |
| Trigger | Start of every UVAI session | Ensures consistent context before any work begins |
| Output | Context briefing + verification sweep | Surfaces live state issues alongside architecture context |
| Storage | Hybrid (inline + live-read) | Stable principles baked in; volatile data (models, git, env) pulled fresh |

---

## Architecture: Hybrid Tiered SKILL.md

**Inline (stable, rarely changes):**
- Mission and Digital Refinery concept
- 4-stage pipeline (INGEST → REASON → ACT → COMPLY)
- Complete 12-system map with one-line descriptions
- Architecture laws (MCP-First, Event-Driven, Self-Correcting, Zero-Mock, REAL_MODE_ONLY)
- Self-Correcting Executor pattern with OrchestrationEngine sequence
- Critical constraints (GitHub contamination, domain consolidation, baseline validation, dual DB)
- Jules Audit Principle
- MCP integration checklist
- Key file locations

**Live-read at invocation (volatile):**
- Model selection rules ← `SESSION_HANDOFF.md`
- Latest gotchas and memory ← `~/.claude/projects/.../memory/MEMORY.md` + referenced files
- Git contamination state ← bash: `git log origin/main..HEAD` / `git log HEAD..origin/main`
- Env var presence ← bash: `printenv | grep GEMINI/VERTEX/GOOGLE` (values masked)
- Backend health ← curl to Railway health endpoint

---

## Two-Track Execution

When `/uvai-init` is invoked, Claude runs both tracks and combines output into one briefing:

**Track 1 — Live Verification:**
Bash checks for git contamination, env var presence, backend reachability.
Results rendered in the briefing header. Issues surfaced as ⚠️ with stop guidance.

**Track 2 — Live Context Pull:**
File reads of SESSION_HANDOFF.md, memory files, CLAUDE.md.
Extracts model compatibility table and current gotchas.
Renders in the LIVE CONSTRAINTS section of the briefing.

---

## Output Format

```
╔══════════════════════════════════════════════════════════════╗
║  🔬  UVAI ECOSYSTEM — SESSION INITIALIZED                    ║
╠══════════════════════════════════════════════════════════════╣
║  MISSION                                                     ║
║  Digital Refinery: Video → Intelligence → Autonomous Action  ║
║  Pipeline: INGEST → REASON → ACT → COMPLY                   ║
║  Domain:   uvai.io (canonical — all frontends consolidate)   ║
╠══════════════════════════════════════════════════════════════╣
║  VERIFICATION                                                ║
║  Git / Env / Backend health results                          ║
╠══════════════════════════════════════════════════════════════╣
║  LIVE CONSTRAINTS  (from memory + SESSION_HANDOFF)           ║
║  Model rules + memory gotchas                                ║
╚══════════════════════════════════════════════════════════════╝
[Full inline architecture context follows]
```

---

## Verification Checklist

After installing the skill, verify by invoking `/uvai-init` in a fresh session:

1. **Briefing header** — Mission, pipeline, and domain appear correctly
2. **Track 1** — Git check output in briefing; env vars masked (`KEY=***`); health status present
3. **Track 2** — Model rules from SESSION_HANDOFF.md appear; memory gotchas extracted
4. **Inline content** — All 12 systems listed; 4-stage pipeline; self-correcting executor loop; Jules principle
5. **Pre-implementation checklist** — Appears at end of output
6. **Resilience** — If SESSION_HANDOFF.md is missing, skill notes it and continues (does not fail)

---

## Gaps Addressed vs. uvai-ecosystem-dev Skill

| Gap | How uvai-init addresses it |
|-----|---------------------------|
| Only 5/12 systems named | Full 12-system table inline |
| No model selection rules | Live-read from SESSION_HANDOFF.md |
| No git contamination check | Track 1 bash verification |
| No env var check | Track 1 bash verification |
| No baseline validation protocol | Pre-implementation checklist enforces it |
| No self-correcting executor detail | OrchestrationEngine loop inline |
| No domain consolidation rule | Critical constraints section |
| No dual-DB risk warning | Critical constraints section |
| No Jules audit principle | Inline as first-class principle |
