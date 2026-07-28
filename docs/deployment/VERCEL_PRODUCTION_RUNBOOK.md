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
