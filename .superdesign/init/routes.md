# App routes

Production is a Next.js 16 App Router application deployed from `apps/web`. The source inventory below is authoritative for the current commit.

## Page purposes

- `/` — marketing landing with hero, workflow, templates, developer and contact sections.
- `/dashboard` — persisted browser library plus upload/analyze entry; selected videos open the analysis workspace.
- `/dashboard/agents` — agent-specific dashboard surface.
- `/studio` — workflow studio for generating a deployable implementation package.
- `/features`, `/pricing`, `/playground`, `/docs/api` — product education and interactive public surfaces.
- `/login` — authentication entry.
- `/app` and `/prototype` — alternate application/prototype surfaces retained in source.
- `/privacy`, `/terms` — legal pages.

## Full route-file inventory

```text
apps/web/src/app/api/agents/actions/route.ts
apps/web/src/app/api/agents/dispatch/route.ts
apps/web/src/app/api/agents/status/route.ts
apps/web/src/app/api/auth/[...nextauth]/route.ts
apps/web/src/app/api/billing/activate/route.ts
apps/web/src/app/api/billing/checkout/route.ts
apps/web/src/app/api/billing/renew/route.ts
apps/web/src/app/api/billing/status/route.ts
apps/web/src/app/api/billing/webhook/route.ts
apps/web/src/app/api/chat/route.ts
apps/web/src/app/api/dashboard/route.ts
apps/web/src/app/api/docs/route.ts
apps/web/src/app/api/extract-events/route.ts
apps/web/src/app/api/jobs/[jobId]/route.ts
apps/web/src/app/api/pipeline/route.ts
apps/web/src/app/api/pipeline/stream/route.ts
apps/web/src/app/api/realtime/session/route.ts
apps/web/src/app/api/route.ts
apps/web/src/app/api/search/route.ts
apps/web/src/app/api/training/status/route.ts
apps/web/src/app/api/training/trigger/route.ts
apps/web/src/app/api/transcribe/route.ts
apps/web/src/app/api/v1/preferences/route.ts
apps/web/src/app/api/video/generate/route.ts
apps/web/src/app/api/video/route.ts
apps/web/src/app/api/video/search/route.ts
apps/web/src/app/api/workflows/video-to-actions/[runId]/route.ts
apps/web/src/app/api/workflows/video-to-actions/route.ts
apps/web/src/app/app/page.tsx
apps/web/src/app/dashboard/agents/page.tsx
apps/web/src/app/dashboard/page.tsx
apps/web/src/app/docs/api/page.tsx
apps/web/src/app/features/page.tsx
apps/web/src/app/layout.tsx
apps/web/src/app/login/page.tsx
apps/web/src/app/page.tsx
apps/web/src/app/playground/page.tsx
apps/web/src/app/pricing/page.tsx
apps/web/src/app/privacy/page.tsx
apps/web/src/app/prototype/layout.tsx
apps/web/src/app/prototype/page.tsx
apps/web/src/app/studio/page.tsx
apps/web/src/app/terms/page.tsx
```
