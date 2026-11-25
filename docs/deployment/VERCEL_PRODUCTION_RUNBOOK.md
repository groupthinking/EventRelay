# UVAI Vercel Production Runbook

Last reviewed: 2026-06-17 (infrastructure updates: Vercel envs, Cloud Run min-instances, Sentry)

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

## Google OAuth Production Migration

- Configure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in Vercel Production.
  These are the canonical names used by the app.
- `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` remain temporary
  fallbacks only. Do not remove them until a production deployment has completed
  a real Google sign-in and callback using the canonical names.
- In Google Cloud, authorize exactly
  `https://uvai.io/api/auth/callback/google` as the production redirect URI.
- Never record credential values in repository files, deployment logs, issue
  comments, or build artifacts.

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
  - `apps/web/src/app/api/pipeline/route.ts`, `apps/web/src/app/api/pipeline/stream/route.ts`, and `apps/web/src/app/api/video/route.ts` are not in this tree (pipeline routes removed in #2322). Canonical pack flow is `POST /api/video/pack` and `GET /api/video/pack?video_id=…`.
  - Auth and rate limiting live in `apps/web/src/proxy.ts`. There is no `apps/web/middleware.ts`.
  - Package: `"@vercel/functions": "^3.0.0"` in `apps/web/package.json`.
  - Build: `npm run build:web` — compilation "✓ Compiled successfully", TS clean, lint clean (`npm run lint`); full static prerender hit pre-existing Next.js InvariantError on `/` (unrelated to remediation — landing page + VideoWorkflowStudio only; API/middleware changes do not affect static generation).
  - Evidence: Direct terminal outputs from greps, `cat`, `sed`, `node` extracts, and full file reads (see code-reviewer transcript for raw command results).
  - Runbooks/checklist cross-updated for the matrix.

- CSP and security headers are configured in `apps/web/next.config.js`.
- `Permissions-Policy` allows microphone access for the explicit Studio voice
  toggle while leaving camera, geolocation, payment, and USB blocked.
- `/api/*` rate limiting is in `apps/web/src/proxy.ts` (Next.js 16 loads that file directly).
- Lockfiles are committed at the repository root. There is no `apps/web/package-lock.json`.
- Turborepo is configured with build outputs so monorepo builds can cache.
- Speed Insights and first-party font optimization are part of the web app.
- API routes return bounded JSON errors for bad inputs and provider outages.
- `/api/docs` redirects to the public docs page at `/docs/api`.

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
- `POST /api/pipeline` and `/api/pipeline/stream` are not in this tree (removed in #2322). Smoke-test the Video Pack flow with `scripts/deployment/production_smoke.sh`.

Remaining dashboard items (optional / follow-up):

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
curl -sS -X POST https://uvai.io/api/video/pack \
  -H 'content-type: application/json' \
  --data '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}'
curl -sSI https://uvai.io/api/docs | head
```

Expected:

- `/` returns the configured security headers.
- `POST /api/video/pack` returns 202 (processing) or 200 (ready pack);
  `GET /api/video/pack?video_id=…` resolves to the ready pack.
- `/api/docs` returns a redirect to `/docs/api`, and `/docs/api` renders the
  API reference.
