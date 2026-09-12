# High-value extractable components

The following components are stable candidates for Superdesign extraction because they are shared, visually distinctive, or own meaningful interaction state.

| Component | Source | Why it should be extracted |
|---|---|---|
| Landing navigation | `components/landing/LandingNav.tsx` | Primary public-site chrome and responsive menu |
| Product navigation | `components/Nav.tsx` | Authenticated/public app chrome, usage meter and account controls |
| Landing footer | `components/landing/LandingFooter.tsx` | Public-site trust and route footer |
| Analysis canvas | `components/dashboard/DashboardCanvasView.tsx` | Core responsive workbench layout |
| Video evidence stage | `components/dashboard/VideoCanvasStage.tsx` | Player, timeline, seek and event markers |
| Analysis panels | `components/dashboard/panels.tsx` | Transcript, actions, events, agents, search and insight modules |
| Pipeline progress | `components/PipelineProgress.tsx` | Shared progress state and execution status |
| Agent flow visualizer | `components/AgentFlowVisualizer.tsx` | Agent trace/progress topology |
| Billing status banner | `components/billing/BillingStatusBanner.tsx` | Entitlement/upgrade guardrail |
| Button, Card, Input, Badge | `components/ui/*.tsx` | Foundational reusable primitives and all current variants |

## Extraction guidance

- Preserve source semantics and state ownership during baseline reproduction.
- For redesign branches, extract an `EvidenceStatus` primitive and a `ProvenanceRow` composition from the analysis panels; these do not exist yet and should be proposed visually before implementation.
- Keep the video stage, transcript rows, agent trace, and evidence state synchronized through one analysis record rather than duplicating their status in local component state.
- Do not extract route-specific wrappers unless they appear on at least two routes.
