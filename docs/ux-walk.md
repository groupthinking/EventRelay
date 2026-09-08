# Lumen UX walk (current read-only audit)

This is a **read-only** audit of the current entry-to-completion routing in the live web app.

## Scope

- Surface audited: `apps/web` Next.js routes and Studio runtime flow.
- Focus: where users enter, where they are redirected, and what blocks completion.

## Entry routes and routing outcomes

| Entry surface | Current behavior | Evidence |
| --- | --- | --- |
| `/` | Public landing page with paste form and Pro checkout entry. | `apps/web/src/app/page.tsx`, `apps/web/src/components/home/HomePasteForm.tsx` |
| Home paste submit | Validates YouTube URL, fires `POST /api/video/pack`, then navigates to `/studio?video=...`. | `apps/web/src/lib/studio-handoff.ts`, `apps/web/src/lib/emit-video-pack.ts` |
| `/studio` | Canonical workbench (`OneLoopStudio`) for analyze → act → export → deploy actions. | `apps/web/src/app/studio/page.tsx`, `apps/web/src/components/OneLoopStudio.tsx` |
| `/dashboard` + `/dashboard/*` | Retired; redirected to `/studio` (page redirect + middleware + Next redirects). | `apps/web/src/app/dashboard/page.tsx`, `apps/web/src/proxy.ts`, `apps/web/next.config.js` |
| `/dashboard/agents` | Retired; redirected to `/studio`. | `apps/web/src/app/dashboard/agents/page.tsx` |
| `/app` + `/app/*` | Redirected to `/studio`. | `apps/web/src/app/app/page.tsx`, `apps/web/next.config.js` |
| `/prototype` + `/prototype/*` | Redirected to `/studio`. | `apps/web/src/app/prototype/page.tsx`, `apps/web/next.config.js` |
| `/features` | Redirected to `/`. | `apps/web/src/app/features/page.tsx`, `apps/web/next.config.js` |
| `/playground` | Redirected to `/`. | `apps/web/src/app/playground/page.tsx`, `apps/web/next.config.js` |
| `/lumen` | No route found in the current app router or redirects. | repo search for `lumen` in `apps/web/src` and `apps/web/next.config.js` |

## Entry-to-completion flow (today)

1. User enters at `/` and submits YouTube URL.
2. Home handoff normalizes URL and pre-kicks identity pack emit (`/api/video/pack`).
3. User lands on `/studio?video=...`.
4. Studio auto-starts analysis from query param (`applyStudioQueryAutoStart` → `runAnalysis`).
5. `processVideo` runs durable flow:
   - identity pack emit/poll,
   - start `/api/workflows/video-to-actions`,
   - poll run status,
   - persist verified transcript/events/actions into store.
6. Completion happens on the same `/studio` page through:
   - transcript/events + pack surfaces,
   - tool run results,
   - export package,
   - deploy attempt with G.A.T.E. decisioning.

Evidence: `apps/web/src/components/OneLoopStudio.tsx`, `apps/web/src/store/dashboard-store.ts`, `apps/web/src/lib/studio-workflow.ts`, `apps/web/src/lib/gate-transition.ts`.

## Missing / blocked surfaces (gaps)

1. **No distinct Lumen route/shell**  
   The canonical workbench is `/studio`; no `/lumen` route exists.

2. **Completion is single-page only**  
   There is no dedicated “completion” route; users stay on `/studio` and state is in-page/store-driven.

3. **Deploy path is intentionally gated**  
   - `/api/workflows/studio-deploy` is not public in auth policy.
   - 401/403 in Studio deploy/act flows force login redirect.
   - Deploy button can be disabled by stack-check hold (`holdReason`) and by missing payload.

   Evidence: `apps/web/src/lib/auth-paths.ts`, `apps/web/src/components/OneLoopStudio.tsx`, `apps/web/src/lib/official-templates.ts`.

4. **Auth misconfiguration fail-closed behavior**  
   In production with missing `NEXTAUTH_SECRET`, protected surfaces return 503 instead of silently opening.

   Evidence: `apps/web/src/lib/auth-paths.ts`, `apps/web/src/proxy.ts`.

5. **Retired secondary surfaces remain redirects, not experiences**  
   `/dashboard`, `/app`, `/prototype`, `/features`, and `/playground` are compatibility redirects only.

## Summary

Current UX is a consolidated **`/` → `/studio`** flow. Entry is public, analysis can run from a public Studio surface, and completion actions are concentrated in OneLoopStudio with explicit auth and deploy gating.
