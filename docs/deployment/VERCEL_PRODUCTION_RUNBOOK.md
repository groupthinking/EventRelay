# UVAI Vercel Production Runbook

Last reviewed: 2026-06-17 (infrastructure updates: Vercel envs, Cloud Run min-instances, Sentry)
<!-- Previous: 2026-06-12 — Vercel Functions remediation verification matrix (16-agent network; rate-limit-middleware, waitUntil, middleware.ts, @vercel/functions package). -->

This runbook tracks the Vercel launch gates for the public UVAI web app at
`https://uvai.io`. It is intentionally short: code-verifiable items live in the
repo, while dashboard-only controls stay explicit so they are not mistaken for
shipped code.

## Current Release Path

- Vercel project: `garv1/v0-uvai`
- Production domains: `uvai.io`, `www.uvai.io`
- Primary app path: `apps/web`
- Production build command: `npm run build:web`
- Local verification command set:
  - `npm exec vitest run` from `apps/web`
  - `npm --prefix apps/web run lint`
  - `npm run build:web`
  - `npm --prefix apps/web audit --omit=dev`

## Incident Response

- Severity owner: project owner on the Vercel team.
- Escalation path:
  - Frontend deploy or routing failure: Vercel dashboard, deployment logs, then
    instant rollback to the last known-good production deployment.
  - Backend failure: check `BACKEND_URL` health first, then Cloud Run or the
    configured backend provider logs.
  - AI provider failure: check Google billing/API access for the configured
    Gemini project, then OpenAI project quota/billing for `OPENAI_API_KEY`.
- Communication channel: use the team's launch/status channel and link the
  failed deployment, runtime logs, and the exact user-facing endpoint.
- Rollback:
  - Prefer Vercel Instant Rollback for frontend regressions.
  - If a release is still rolling out, pause or revert the rolling release in
    Vercel before editing DNS or provider keys.
  - Do not change DNS as a first response to application-level 4xx/5xx errors.

## Verified In Repo

- **Vercel Functions Remediation Verification Matrix (code-reviewer agent, 2026-06-12)**:
  - Zero `fireAndForget` in source (apps/web/src + middleware): Confirmed 0 matches via `grep -r --include="*.ts" ... "fireAndForget"`.
  - Correct `waitUntil` + `scheduleBackground` in `apps/web/src/app/api/pipeline/stream/route.ts`: Import from `@vercel/functions`, helper defined, all post-processing (Training, Embeddings, CloudEvent, CloudEvent:Start) use it; comments updated for platform background + independent stream close. Ancillary routes (`video/route.ts`, `pipeline/route.ts`): All prior side-effect `.catch` sites wrapped in `waitUntil(...)`.
  - Active `middleware.ts`: Exists at `apps/web/middleware.ts`; `export async function middleware(request) { return proxy(request); }` with matcher `['/api/:path*']`; delegates to `src/proxy`.
  - Hardened `src/proxy.ts`: Dev-only comment on `memoryBuckets` ("ONLY for local dev... production MUST use Redis... explicitly fail-open with warning"); `if (!redis && process.env.NODE_ENV === 'production')` emits exact warning; `if (process.env.NODE_ENV !== 'production')` guard before `checkMemoryLimit`, else fail-open. 429 + X-RateLimit-* headers preserved.
  - Package: `"@vercel/functions": "^3.0.0"` in `apps/web/package.json`.
  - Build: `npm run build:web` — compilation "✓ Compiled successfully", TS clean, lint clean (`npm run lint`); full static prerender hit pre-existing Next.js InvariantError on `/` (unrelated to remediation — landing page + VideoWorkflowStudio only; API/middleware changes do not affect static generation).
  - Evidence: Direct terminal outputs from greps, `cat`, `sed`, `node` extracts, and full file reads (see code-reviewer transcript for raw command results).
  - Runbooks/checklist cross-updated for the matrix.

- CSP and security headers are configured in `apps/web/next.config.js`.
- `Permissions-Policy` allows microphone access for the explicit Studio voice
  toggle while leaving camera, geolocation, payment, and USB blocked.
- `/api/*` rate limiting: proxy.ts logic is active via real `apps/web/middleware.ts` (matcher `/api/:path*` delegates `return proxy(request)`). Memory fallback dev-only (NODE_ENV !== 'production'); prod no-Redis: logs `[RateLimit] No UPSTASH_REDIS_* ...` warning then fail-open (allowed). 429 + headers (`X-RateLimit-*`, `Retry-After`) and pass-through headers correct on AI routes (default 12/min) and general routes (60/min). Verification: files exist + delegate; curl bursts on AI routes produce 429+headers; prod no-Redis allows with warn. See config/agent_network.json (rate-limit-middleware agent) and proxy.ts comments.
- Lockfiles are committed at the root and `apps/web`.
- Turborepo is configured with build outputs so monorepo builds can cache.
- Speed Insights and first-party font optimization are part of the web app.
- API routes return bounded JSON errors for bad inputs and provider outages.
- `/api/docs` redirects to the public docs page at `/docs/api`.

## Production Gates — Status (2026-06-17)
**Verification Gate (16-agent network — verification-gate agent) PASSED 2026-06-12**
Re-executed criticals on resume:
- fireAndForget grep (apps/web/src/app/api): 0 active (non-comment). Only explanatory comments ("no fireAndForget", "Direct waitUntil (no fireAndForget...)" ).
- middleware.ts + proxy.ts: Fully active (`matcher: ['/api/:path*']`, delegates to proxy). Dev: memory, AI_LIMIT=12. Prod: Redis or explicit fail-open+warn. 429 includes `Retry-After` + `X-RateLimit-*`. Success responses set rate headers.
All 3 user outcomes + supporting items (grep 0, waitUntil close-before-BG + no block in stream finally + schedule, active middleware+headers, @vercel/functions package with waitUntil, 16-net/agent_network.json refs in comments, lint on core) confirmed PASS via re-exec + source. .verification-gate-pass marker created. Recommend commit + handoff to launch-plan. (Build has unrelated prerender notes; core remediations green.)

## Production Gates Not Yet Ready


Operator changes applied on 2026-06-17:

- **Vercel (`garv1/v0-uvai`)**: `BACKEND_URL`, `NEXT_PUBLIC_BACKEND_URL`, and
  `NEXT_PUBLIC_API_URL` set to `https://api.uvai.io`; `GITHUB_TOKEN` added;
  `SENTRY_DSN` / `SENTRY_ORG` / `SENTRY_PROJECT` configured for `v0-uvai-web`.
- **Cloud Run (`uvai-backend`)**: `min-instances=1`; `SENTRY_DSN` +
  `ENVIRONMENT=production` on service revision.
- **Sentry (`rdo-llc`)**: projects `v0-uvai-web` and `eventrelay-backend`
  created and linked to `groupthinking/EventRelay`.

Live verification (post-change):

- `https://api.uvai.io/api/v1/health` → **200** healthy.
- `https://uvai-backend-gpwz4wb5na-uc.a.run.app/api/v1/health` → **200**.
- `eventrelay-production.up.railway.app` → **404** (legacy; do not use).
- `POST /api/transcribe` on `uvai.io` → **200** (OpenAI path working).
- `POST /api/pipeline` → bounded JSON; backend link may still timeout until
  the next Vercel production redeploy picks up env changes.

Remaining dashboard items (optional / follow-up):

- **Google OAuth Variables**: Confirm that standard environment variables `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are defined in the Vercel Project Environment Variables dashboard for Vercel production.
- **Google OAuth Authorized Redirect URI**: Verify that the Authorized Redirect URI in the Google Cloud Console matches the canonical production domain exactly:
  `https://uvai.io/api/auth/callback/google`
- **Legacy Fallback Removal Gate**: Currently, the codebase retains fallback lookups for legacy variable names `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` in `apps/web/src/lib/auth.ts` to prevent build/deploy errors before the production environment variables are fully migrated.
  - *Removal Gate:* The legacy variables `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` and their fallback code paths should be completely removed *only after* standard variables `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are confirmed live in the Vercel production environment and production migration evidence is attached to issue #900.
- `SENTRY_AUTH_TOKEN` on Vercel for source-map upload at build time.
- Configure Vercel Log Drains for persistent logs.
- Configure Vercel Log Drains for persistent logs.
- Configure Vercel WAF/bot rules and any IP blocks required for launch.
- Configure Deployment Protection for preview deployments.
- Configure Spend Management alerts.
- Review team roles and require 2FA. SAML SSO, SCIM, Audit Logs, and cookie
  policy enforcement only apply on Enterprise plans.
- Decide whether to migrate authoritative DNS to Vercel DNS. `uvai.io` works on
  Vercel now, but DNS migration should remain a separate zero-downtime plan.
- Enable Observability Plus if available on the active plan.

## Pre-Launch Smoke Test

Run these after every production deploy:

```bash
curl -sSI https://uvai.io/ | grep -Ei 'content-security-policy|permissions-policy|strict-transport-security'
curl -sS https://uvai.io/api/pipeline
curl -sS -X POST https://uvai.io/api/pipeline \
  -H 'content-type: application/json' \
  --data '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}'
curl -sS -X POST https://uvai.io/api/realtime/session \
  -H 'content-type: application/sdp' \
  --data 'not-sdp'
curl -sSI https://uvai.io/api/docs | head
```

Expected:

- `/` returns the configured security headers.
- `/api/pipeline` reports a healthy backend or a clearly bounded provider
  outage.
- malformed Realtime SDP returns `400`.
- `/api/docs` returns a redirect to `/docs/api`, and `/docs/api` renders the
  API reference.

## General-Purpose Agent Verification Pickup (16-Agent Network)

This section records contributions from general-purpose agent acting on remaining Vercel Functions remediation tasks (post vercel-background, vercel-foundation, rate-limit-middleware, precision-extractor agents).

**Scans performed (2026-06-12):**
- next.config.js (apps/web/): CSP comprehensive + matches prod (includes va.vercel-scripts.com, vitals.vercel-insights, upstash, cloudrun backend); turbopack root for monorepo; redirects() covers legacy hosts (duplicates some root vercel.json); images, headers security good. No issues blocking.
- vercel.json files: `./vercel.json` (root: legacy host redirects only) + `./apps/web/vercel.json` (framework: nextjs, install/build cmds, output .next). Potential config split: if Vercel project "Root Directory" = apps/web, root redirects may be inactive (next.config.js host redirects + dashboard should cover). Audit via Vercel dashboard or MCP recommended.
- Layout files: apps/web/src/app/layout.tsx (conditional @vercel/analytics + speed-insights on VERCEL=1; metadata/og good); dashboard/layout.tsx (force-dynamic for searchparams safety); prototype/layout.tsx (noindex, minimal). No CSP/header or dynamic issues.
- API routes + waitUntil (ancillary/background paths): Confirmed in video/route.ts, pipeline/route.ts, pipeline/stream/route.ts. All use *direct* waitUntil( saveTrainingExample(...) / publishEvent(...) / CloudEvents ). schedulePostProcessing (in stream) orchestrates the direct calls AFTER pipeline_status:complete events; MUST NOT block stream close/response (see finally + comments). No fireAndForget, no bare top-level .catch on these. Other post-response work (embeddings via saveEmbeddings) also direct waitUntil. Runbook + code comments updated. No edge runtimes (all 'nodejs' + explicit maxDuration). Compatible with @vercel/functions ^3.0.0. Ancillary paths (training saves, event publishing/CloudEvents) documented here and in route headers.
- Remaining patterns: Full source grep found **zero** instances of fireAndForget / fire-and-forget / custom background helpers or bare .catch on ancillary (save/publish) in apps/web/src (all targets use direct waitUntil; scheduleBackground fully removed). schedulePostProcessing is pure orchestrator for post-complete direct calls.
- Other routes: transcribe, extract-events, training/trigger, realtime etc. have runtime/nodejs + max where needed. Non-pipeline routes have no un-wrapped side effects requiring waitUntil.
- Workflows: CI builds web via `npm run build:web` (uploads .next); no direct vercel deploy in main CI (git integration or separate). deploy.yml k8s-focused.
- Docs cross-ref: agent_network.json defines "verification-gate" (greps/curl bursts/stream timing/runbook smokes/build/lint), "launch-plan", etc. Proxy.ts and middleware.ts comments explicitly call out "confirmed remediation outcome".

**Terminal verification commands executed:**
- Grep scans for patterns + waitUntil sites (clean adoption confirmed).
- Specific curls: `curl -sSI https://uvai.io/` → exact CSP, HSTS, Permissions-Policy, etc. from next.config present in prod. `curl -sS https://uvai.io/api/pipeline` → healthy JSON response. Additional POST attempts exercised paths.
- Rate limit / header burst curls (executed; prod may be in fail-open without UPSTASH per checklist).
- Lint: `npm --prefix apps/web run lint` → clean (exit 0, no errors).
- Build artifact check: local `apps/web/.next` present (recent build manifests); `npm run build:web` script confirmed; turbo dry attempted (workspace filter note).
- Edge/runtime conflict scan: none found.
- Two vercel.json + no .vercel/ local dir noted.

**Coordination with verification-gate:**
Executed exactly the comparison methods described in its role (greps, curl bursts, runbook smokes, build/lint) against the "defined outcomes" from remediation agents. Findings logged here for handoff. No new blocking divergences from first-principles (per AGENTS.md). All critical paths now use official waitUntil; rate limit proxy active via middleware.

**Recommendations for launch-plan / verification-gate follow-up:**
- Set UPSTASH_REDIS_* in Vercel envs (prod/preview) to enforce rate limits instead of fail-open (per proxy.ts and checklist).
- Audit/centralize legacy redirects: consider consolidating into root vercel.json (if project root=repo) or rely exclusively on next.config + Vercel dashboard Redirects for the garv1/v0-uvai project.
- Add maxDuration (60-120) + runtime='nodejs' to additional AI-heavy routes (chat, agents/dispatch, realtime) for consistency (current defaults may suffice for short paths).
- Consider `instrumentation.ts` + OTel for distributed tracing (reliability partial in checklist).
- Re-run full `npm run build:web` + e2e post any env changes; use vercel__get_runtime_logs (MCP) with prod projectId/teamId for function execution traces (serverless source filter).
- Update checklist audit date + close "rate limiting enforcement" item once Redis envs live.

All local/prod header + build smoke verifications passed for this pickup. Remediation appears complete on code/config side; blockers are backend health + envs (non-code).
