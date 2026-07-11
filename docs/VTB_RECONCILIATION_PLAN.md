# VTB → EventRelay Reconciliation Plan

**Date:** April 18, 2026
**Status:** ✅ ALL 6 CHANGES APPLIED

---

## What Changed After Deep Scan

The original report assumed EventRelay was near-empty. In reality, it's a **full production monorepo** with 9 specialized agents, 11 API routes, 7 frontend pages, Supabase persistence, Redis state management, OpenTelemetry observability, 3 MCP servers, and a comprehensive dashboard. This changes the delta significantly.

---

## Revised Feature Delta (What Actually Needs Porting)

### ALREADY EXISTS IN EVENTRELAY (no porting needed)

| Feature | EventRelay Location | Notes |
|---------|-------------------|-------|
| Quality scoring agent | `src/agents/specialized/quality_agent.py` | 1,219 lines. Scores: cyclomatic complexity, maintainability, LOC, comment ratio, duplication, test coverage, code smells, tech debt. Also has `assess_actionability()` for video-extracted actions (0-100 score). |
| Architecture agent | `src/agents/specialized/architecture_agent.py` | Anti-pattern detection, improvement identification, architectural issue analysis with severity levels. |
| Pipeline orchestrator | `src/agents/pipeline_orchestrator.py` | 6-agent sequential pipeline: video-ingest → architect → code-gen → build-validator → deployer → knowledge-capture. Event emission for lifecycle. |
| Pipeline stage indicators | `apps/web/src/app/dashboard/page.tsx` | ProcessingStage component with animated indicators (active/complete/pending). |
| Agent flow visualizer | `apps/web/src/components/AgentFlowVisualizer.tsx` | Network visualization (11KB). |
| Supabase persistence | `supabase/supabase_setup.sql` | Tables: projects, chats, files, media, mcp_logs, nods_page (pgvector). Row-level security. |
| State manager | `packages/state-manager/` | Redis/Upstash with distributed locking, rate limiting, workflow step tracking. |
| Observability | `packages/observability/` | Full OpenTelemetry: traces, metrics, OTLP gRPC exporter, workflow instrumentation. |
| Video processing | `src/youtube_extension/` | Innertube transcript extraction, multiple processor strategies. |
| MCP servers | `mcp-servers/` | 3 servers (LiquidAI, LiteRT, shared-state) + agent network integration. |
| Dashboard | `apps/web/src/app/dashboard/` | Split-view: video embed + tabs (Analysis, Transcript, Actions, Search). |
| A2A framework | `src/agents/a2a_framework.py` | Agent-to-agent communication protocol. |
| Zustand store | `apps/web/src/store/dashboard-store.ts` | Client state management for dashboard. |
| 9 specialized agents | `src/agents/specialized/` | quality, architecture, code_generator, performance, personality, precision_extractor, security, strategy |

### NEEDS PORTING FROM VTB (revised list)

Only **6 changes** remain instead of the original 11. Each one fills a genuine gap.

---

## Change 1: DAG Parallel Execution Layer

**WHY:** EventRelay's `pipeline_orchestrator.py` runs agents sequentially. VTB proved that independent tasks (blueprint, launch plan, platform spec) can run in parallel, cutting total time 40-60%. EventRelay already has 6 pipeline stages — some are independent and could batch.

**WHERE:**
- Modify: `src/agents/pipeline_orchestrator.py` (add parallel batching to existing orchestrator)
- New: `src/agents/dag_executor.py` (topological sort + asyncio.gather for batching)

**WHAT:** Add `asyncio.gather()` batching for independent stages. Keep the existing sequential fallback. Add dependency declarations to each pipeline stage.

**HOW:** Don't replace the orchestrator — extend it. Add a `dependencies` field to `PipelineResult`. Before executing each stage, check if multiple stages have all dependencies met → batch them with `asyncio.gather()`. The existing event emission system (`skill_monitor_emitter`) already supports this.

**VTB source:** `lib/pipeline.ts` (lines 1-180, the `topologicalBatches()` and `executePipeline()` functions)

---

## Change 2: Correction Feedback Loop

**WHY:** EventRelay has a quality agent AND an architecture agent, but they don't talk to each other. The quality agent scores output, but nothing happens with a low score. VTB's architect agent rewrites specs when the judge scores below threshold (70/100), then re-runs generation. This closes the loop.

**WHERE:**
- Modify: `src/agents/pipeline_orchestrator.py` (add correction stage after build-validator)
- Modify: `src/agents/specialized/quality_agent.py` (expose `assess_actionability()` result as pipeline input)
- New: `src/agents/correction_loop.py` (orchestrates quality → architect → re-generation cycle)

**WHAT:** Wire quality_agent output into architecture_agent input. If quality score < threshold, architecture_agent rewrites the plan, then code_generator re-runs. Max 2 iterations.

**HOW:** After the build-validator stage, insert a quality gate. Call `quality_agent.assess_actionability()`. If score < 70, feed the quality report into `architecture_agent` with a correction prompt, then loop back to code-gen. Emit `pipeline.event` with `event: "correction.triggered"` for dashboard visibility.

**VTB source:** `lib/architect.ts` (rewrite prompt), `lib/judge.ts` (threshold logic)

---

## Change 3: User Preferences System

**WHY:** No user customization exists. Every video gets the same treatment regardless of whether the user is in healthcare, finance, or education. VTB preferences (industry, complexity, business model, tone, target audience) inject context into generation prompts, making outputs relevant.

**WHERE:**
- New: `apps/web/src/components/PreferencesPanel.tsx` (collapsible UI)
- New: `apps/web/src/lib/preferences.ts` (persistence via Supabase or localStorage)
- Modify: `apps/web/src/app/dashboard/page.tsx` (mount PreferencesPanel above video input)
- Modify: `src/agents/pipeline_orchestrator.py` (pass preferences as context to agents)

**WHAT:** A collapsible preferences panel with industry/complexity/tone dropdowns and target audience text input. Preferences stored in Supabase `projects` table (JSONB field) and injected into agent prompts.

**HOW:** Port VTB `components/PreferencesPanel.tsx` and `lib/preferences.ts`. Adapt styling from Vite/inline-styles to Tailwind (EventRelay uses Tailwind + dark theme with `#0e0e13` background and `#6af2de` accent). Store in Supabase `projects.metadata` JSONB. Pass to pipeline orchestrator as `options.preferences`.

**VTB source:** `components/PreferencesPanel.tsx`, `lib/preferences.ts`

---

## Change 4: Per-Tab Feedback Widgets

**WHY:** EventRelay has quality scoring but no way for users to give feedback. VTB's feedback widgets (star rating + comment) on each tab feed into the correction loop, creating a human signal that guides automated rewrites.

**WHERE:**
- New: `apps/web/src/components/FeedbackWidget.tsx` (compact star rating + comment)
- New: `apps/web/src/lib/feedback.ts` (Supabase persistence)
- Modify: `apps/web/src/app/dashboard/page.tsx` (add FeedbackWidget to Analysis, Transcript, Actions tabs)
- New: Supabase migration for `feedback` table

**WHAT:** Inline feedback widget on each dashboard tab. 1-5 star rating + optional comment. Stored in Supabase with video_id, tab, rating, comment, timestamp. Consumed by correction loop (Change 2).

**HOW:** Port VTB `components/FeedbackWidget.tsx` and `lib/feedback.ts`. Replace localStorage with Supabase client. Add feedback table migration. Wire into the correction loop's architect prompt via `buildFeedbackContext()`.

**VTB source:** `components/FeedbackWidget.tsx`, `lib/feedback.ts`

---

## Change 5: Business Artifact Generation (Blueprint, Launch Plan, Platform Spec)

**WHY:** EventRelay generates code but no business context. VTB generates three business artifacts alongside code: Blueprint (workflow DAG), Launch Plan (GTM strategy with Google Search grounding), Platform Spec (architecture). These bridge "I watched a video" → "I have a business plan."

**WHERE:**
- New: `src/agents/specialized/blueprint_generator.py`
- New: `src/agents/specialized/launch_plan_generator.py`
- New: `src/agents/specialized/platform_spec_generator.py`
- New tabs in dashboard: `apps/web/src/app/dashboard/page.tsx`
- Modify: `src/agents/pipeline_orchestrator.py` (add as parallel stages after video-ingest)

**WHAT:** Three new agents that run in parallel (via Change 1's DAG engine) after video ingestion. Each produces structured JSON. Launch Plan and Platform Spec use Google Search grounding for market-aware content.

**HOW:** Port VTB generation prompts from `lib/pipeline.ts`. Wrap each in a Python agent following EventRelay's `BaseAgent` pattern from `a2a_framework.py`. Register in pipeline orchestrator as parallel stages depending only on `video-ingest`. Add new tabs to the dashboard's `activeTab` state.

**VTB source:** `lib/pipeline.ts` (BLUEPRINT_FROM_VIDEO_PROMPT, LAUNCH_PLAN_FROM_VIDEO_PROMPT, PLATFORM_SPEC_FROM_VIDEO_PROMPT)

---

## Change 6: Event Classification Taxonomy

**WHY:** uvai.io classifies events as ACTION/TOPIC/CODE/ALERT. EventRelay's `event_routes.py` accepts a generic `type` field with no predefined taxonomy. Structured event types enable filtered views, color-coded displays, and smarter routing.

**WHERE:**
- Modify: `src/youtube_extension/backend/api/event_routes.py` (add enum validation)
- New: `src/core/event_types.py` (enum + metadata)
- Modify: `apps/web/src/components/EventList.tsx` (color-coded badges per type)
- Modify: Agent extraction prompts to output classified events

**WHAT:** A 4-type enum (ACTION, TOPIC, CODE, ALERT) with confidence scores and severity levels. Applied during extraction, not post-processing. EventList component gets color-coded badges.

**HOW:** Define `EventType` enum in a shared module. Update VAI extraction prompts to classify each event. Add badge rendering to EventList.tsx (ACTION=blue, TOPIC=purple, CODE=green, ALERT=red, matching uvai.io's visual language).

**VTB source:** N/A (new implementation based on uvai.io's event taxonomy)

---

## What We DON'T Port (and why)

| VTB Feature | Why Skip |
|------------|----------|
| Vercel deployment | EventRelay already has a deployer agent. Keep existing. |
| UiPath integration | Specific to VTB's enterprise context. Not needed in EventRelay. |
| Gemini provider abstraction | EventRelay already uses google-genai SDK directly. |
| Monaco editor (Code tab) | EventRelay's code_generator handles code differently (files, not single HTML). |
| Mermaid diagram rendering | Nice-to-have but not critical path. Can add later. |
| Pipeline event emitter | EventRelay already has `skill_monitor_emitter.py`. Use it. |

---

## Execution Order

```
Change 1 (DAG Engine)          ← Foundation, enables parallel execution
    ├── Change 5 (Business Artifacts)  ← Uses DAG for parallel generation
    └── Change 2 (Correction Loop)     ← Uses DAG for re-execution
         └── Change 4 (Feedback Widgets) ← Feeds into correction loop
Change 3 (Preferences)         ← Independent, can start anytime
Change 6 (Event Classification) ← Independent, can start anytime
```

**Estimated effort:** 8-10 days total (down from 15-20 in the original report)

---

## File Mapping: VTB Source → EventRelay Target

| VTB File | EventRelay Target | Action |
|----------|------------------|--------|
| `lib/pipeline.ts` (DAG engine) | `src/agents/dag_executor.py` | Port to Python (asyncio) |
| `lib/pipeline.ts` (prompts) | `src/agents/specialized/blueprint_generator.py` etc. | Port prompts to Python agents |
| `lib/judge.ts` | Wire into existing `quality_agent.py` | Adapt threshold logic only |
| `lib/architect.ts` | `src/agents/correction_loop.py` | New file, uses existing architecture_agent |
| `lib/preferences.ts` | `apps/web/src/lib/preferences.ts` | Port + Supabase persistence |
| `lib/feedback.ts` | `apps/web/src/lib/feedback.ts` | Port + Supabase persistence |
| `components/PreferencesPanel.tsx` | `apps/web/src/components/PreferencesPanel.tsx` | Port + Tailwind restyling |
| `components/FeedbackWidget.tsx` | `apps/web/src/components/FeedbackWidget.tsx` | Port + Tailwind restyling |
| `components/PipelineView.tsx` | Enhance existing `AgentFlowVisualizer.tsx` | Merge features, not replace |
| `components/JudgePanel.tsx` | Enhance existing `AnalysisPanel.tsx` | Add scoring display |
