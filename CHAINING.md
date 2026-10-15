# Sparkle Pills Chaining Contract

This repository implements an interview-first chaining flow for sparkle-pill use cases in `POST /api/chat`.

## Goal

For sparkle-pill requests, avoid jumping straight to a plan. First collect concrete use-case constraints, then emit an actionable system plan.

## Runtime behavior

1. Detect sparkle-pill intent in `query` or `message` (`/\bsparkle\s*pills?\b/i`).
2. If required interview answers are missing, return interview questions and stop.
3. If interview answers are present and complete, return a deterministic system plan.
4. Do not call model providers for this branch (no Gateway or Grok dependency).

## Request payload

```json
{
  "query": "Build me a system for using sparkle pills",
  "sparkleInterview": {
    "useCase": "I need to manage daily focus sessions across work and school.",
    "trigger": "Start each weekday at 08:30",
    "tools": ["Google Calendar", "Slack"],
    "constraints": "No notifications after 21:00",
    "successSignal": "5 sessions completed per week"
  }
}
```

## Interview-first response shape

```json
{
  "answer": "Before I design the system...",
  "requiresInterview": true,
  "interviewQuestions": [
    "What exact chore or workflow should sparkle pills automate?",
    "What should trigger each run (time, event, or manual action)?",
    "Which tools and systems must it update (for example Calendar, Slack, email)?",
    "What rules or constraints must never be violated?",
    "How will you measure success each week?"
  ]
}
```

## Plan response shape

```json
{
  "answer": "Sparkle Pills System Plan\n...",
  "requiresInterview": false,
  "provider": "sparkle-pills-planner",
  "interview": {
    "useCase": "...",
    "trigger": "...",
    "tools": ["..."],
    "constraints": "...",
    "successSignal": "..."
  }
}
```

## Files

- `apps/web/src/lib/sparkle-pills.ts`
- `apps/web/src/app/api/chat/route.ts`
- `apps/web/src/app/api/__tests__/chat-sparkle-pills-route.test.ts`
