# UVAI evidence-first design system

## Product character

UVAI is a serious video-intelligence workbench, not a generic AI chat surface. It should feel precise, calm, technical, and auditable. Preserve the recognizable black/teal visual language from production while replacing decorative confidence with visible evidence states.

## Color roles

- Canvas: `surface-950` / `#020617`; elevated surfaces use `surface-900` / `#0f172a` with low-opacity white borders.
- Primary action: teal `#14b8a6`; hover/focus may move toward `#2dd4bf`.
- Evidence/source: cyan `#22d3ee`.
- Verified/healthy: green `#22c55e`.
- Needs review/degraded: amber `#facc15`.
- Failed/blocked: red `#ef4444`.
- Text: white for primary, 70% white for secondary, 40–50% white for tertiary. Never use low-opacity text for critical state.

## Typography

- Headings: Space Grotesk, backed by Inter/system sans.
- Body and controls: Inter.
- Transcript timestamps, run IDs, sources, checksums, and agent traces: JetBrains Mono.
- Use compact uppercase labels only for metadata; do not uppercase prose.

## Geometry and density

- App shell radius: 12–16px. Compact evidence rows: 8–10px. Pill radius is reserved for short statuses and filters.
- Desktop workspace is a three-region evidence canvas: transcript/source rail, video/evidence stage, analysis/action rail.
- Mobile uses explicit accessible tabs; do not rely on global descendant selectors to rearrange layout.
- Default control target is at least 44px on touch surfaces.

## Core component states

### EvidenceStatus

Required values: `verified`, `processing`, `degraded`, `failed`, `unavailable`. Pair icon, label, and concise explanation; color alone is insufficient.

### ProvenanceRow

Show source URL/domain, acquisition method, fetched-at timestamp, segment count, duration coverage, and a link/command to inspect raw evidence. Unknown values render as `Unavailable`, never as an invented zero.

### PipelineStage

Show factual run state, elapsed time, and error/retry information. A stage may be `complete` only when its declared output contract validates. Never animate fake progress.

### TranscriptSegment

Show verified source timestamp, text, and confidence/source metadata when available. Seeking requires a playable source and a valid timestamp; otherwise the control is disabled with an explanation.

## Interaction principles

1. A complete state means the input was acquired, transformed, validated, and persisted.
2. Keep errors in context with recovery actions and preserve partial evidence.
3. Destructive actions require confirmation; retries use the same generation/run identity unless the user explicitly starts a new run.
4. Every icon-only control has an accessible name and visible focus state.
5. Motion is limited to state transitions and respects `prefers-reduced-motion`.

## Anti-patterns

- No fabricated agent timelines, hard-coded confidence scores, or universal quality passes.
- No blank cards or blank protocol rows.
- No marketing claims such as “all systems operational” unless backed by current health checks.
- No generic gradient-heavy AI dashboard motifs that obscure hierarchy.
- No local-only result records presented as durable platform history.

## Existing implementation anchors

- Tokens: `apps/web/src/app/globals.css`, `apps/web/tailwind.config.js`.
- Primitives: `apps/web/src/components/ui/`.
- Shell: `apps/web/src/components/Nav.tsx` and landing navigation/footer.
- Workspace: `DashboardCanvasView.tsx`, `VideoCanvasStage.tsx`, and `dashboard/panels.tsx`.
- Complete source/context inventory: `.superdesign/init/`.
