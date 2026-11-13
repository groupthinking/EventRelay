# Video Pack planning contract

This repository supports an interview-first planning flow in `POST /api/chat` for a build derived from a hosted Video Pack. The plan is a source-bound starting point for codebase work, not a claim that the target repository has been changed.

## Runtime flow

1. The request must name a canonical `video_id` and matching `pack_id`. The existing chat grounding path loads a ready pack from its hashed identity and rejects missing, processing, error, identity-only, or mismatched packs.
2. A planning request is detected from the query (including existing sparkle-pill requests) or `planIntent: true` on a follow-up turn. Without a ready pack, it returns `pack_required` or the existing pack error.
3. The first turn returns five questions about the deliverable, trigger, available tools, constraints, and acceptance signal. The Studio and hosted App Builder chat clients display the questions and collect labeled or sequential answers.
4. Once the answers are complete, the planner returns a deterministic plan. It separates user-supplied interview answers from excerpts extracted from the pack. Frontend, backend, middleware, database, LSP, MCP, tools, and environment sections show matching cited excerpts or state that the pack has no explicit evidence for that area.
5. The plan proposes repository inspection, a bounded implementation slice, and build/test verification. It never claims the codebase was changed, tests passed, or anything deployed. The planning branch does not call a model provider.

## Request shape

```json
{
  "query": "Plan a build from this Video Pack",
  "video_id": "auJzb1D-fag",
  "pack_id": "vp:v0:auJzb1D-fag",
  "planIntent": true,
  "planInterview": {
    "useCase": "The exact deliverable to build",
    "trigger": "The event or action that starts it",
    "tools": ["Tools available in the target codebase"],
    "constraints": "Implementation boundaries",
    "successSignal": "An observable acceptance result"
  }
}
```

The first turn omits `planIntent` and `planInterview`. A follow-up turn sends the accumulated interview answers with `planIntent: true`, so the user's intent survives even if the follow-up query does not repeat “plan.” A normal pack chat request remains on the grounded model path.

## Implementation

- `apps/web/src/lib/video-pack-plan.ts` holds intent detection, interview validation, evidence selection, and plan rendering.
- `apps/web/src/app/api/chat/route.ts` invokes it only after ready pack verification and quota checks.
- `apps/web/src/components/studio/StudioIdeChat.tsx` and the hosted chat in `apps/web/src/lib/emit-app-builder-sandbox.ts` handle the two-turn UI flow.
