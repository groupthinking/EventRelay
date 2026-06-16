# Vercel Production Checklist Audit

Audit date: 2026-06-10

Project: `garv1/v0-uvai`

Plan: Pro

Primary domain: `https://uvai.io`

## Summary

The app is close to production-ready from the repository side. Build, lint, high-severity production audit, CSP/header smoke checks, and API rate-limit smoke checks pass locally. Vercel now has both `BACKEND_URL` and `NEXT_PUBLIC_BACKEND_URL` configured for Production, Preview, and Development with the Cloud Run backend URL. The remaining hard launch blocker is backend health: the Cloud Run health endpoint returns `500`, and `https://api.uvai.io/api/v1/health` returns `503`. Remaining non-code items are account/dashboard checks plus residual moderate/low dependency advisories whose fixes require major framework or AI SDK upgrades.

## Operational Excellence

| Checklist item | Status | Evidence | Next action |
| --- | --- | --- | --- |
| Incident response plan | Done | `docs/deployment/VERCEL_PRODUCTION_RUNBOOK.md` | Keep owners and contact channels current. |
| Stage, promote, rollback | Done | Runbook has preview, promote, rollback flow. Vercel dashboard shows Instant Rollback. | Run one preview-to-production promotion rehearsal before launch. |
| Monorepo build caching | Done | `turbo.json` defines cached build outputs. | Enable/confirm Vercel Remote Cache if the team uses it. |
| Zero-downtime DNS migration to Vercel DNS | Partial | Live DNS still shows Cloudflare nameservers (`andy.ns.cloudflare.com`, `sofia.ns.cloudflare.com`). `uvai.io` and `www.uvai.io` resolve to Vercel addresses. | Either keep Cloudflare authoritative DNS intentionally, or move nameservers using the runbook cutover steps. |

## Security

| Checklist item | Status | Evidence | Next action |
| --- | --- | --- | --- |
| CSP and security headers | Done | `apps/web/next.config.js`; local `curl -I /` confirmed CSP/HSTS/permissions headers. | Re-test on production after deploy. |
| Deployment Protection | Done | Confirmed in dashboard screenshot. | Confirm preview and production policy match launch intent. |
| WAF custom rules and managed rulesets | Needs dashboard/API verification | Dashboard shows Firewall active; MCP did not expose rule configuration. | Confirm managed rules, bot rules, path rules for `/api/*`, and IP blocks in Vercel Firewall. |
| Log Drains | Needs dashboard/API verification | Not exposed by available Vercel MCP or CLI project/environment checks. | Configure a durable drain in team settings. |
| SSL certificate issues | Done | `curl -I https://uvai.io` returned valid HTTPS from Vercel. | Recheck after DNS or domain changes. |
| Preview Deployment Suffix | Needs dashboard verification | Not exposed by available MCP tools. | Configure if branded previews are required. |
| Lockfiles committed | Done | Root lockfile updated for workspace install. | Keep root `package-lock.json` as the Vercel source of truth. |
| Rate limiting | Partial | `apps/web/src/proxy.ts`; local `/api` smoke showed `X-RateLimit-*`. Vercel env list does not show `UPSTASH_REDIS_REST_URL` or `UPSTASH_REDIS_REST_TOKEN`. | Add Upstash env vars in Vercel for distributed production limits. |
| Access roles | Needs dashboard verification | Not exposed by available MCP tools. | Confirm least-privilege team roles and 2FA. |
| Enterprise-only controls | Not applicable | Plan is Pro. | SAML, SCIM, Audit Logs, cookie policy, function failover, and Secure Compute failover require Enterprise. |
| Block unwanted bots | Partial | Dashboard shows Firewall active; app has API rate limit fallback. | Add explicit Vercel Firewall bot/challenge/block rules. |

## Reliability

| Checklist item | Status | Evidence | Next action |
| --- | --- | --- | --- |
| Observability Plus | Likely enabled | Dashboard screenshot shows Observability. | Confirm plan/add-on and alert thresholds in Vercel. |
| Function failover | Not applicable | Enterprise-only. | Revisit only if moving to Enterprise. |
| Secure Compute passive failover | Not applicable | Enterprise-only. | Revisit only if moving to Enterprise. |
| Caching headers | Partial | Static pages serve cache headers; API/SSE routes use no-cache where needed. | Review route-by-route caching after traffic data. |
| Caching headers vs ISR | Done | Runbook separates deploy checks; app build output shows static and dynamic routes. | Document ISR explicitly if new ISR routes are added. |
| Distributed tracing | Partial | Repo has observability packages, but web app does not export Vercel/OTel instrumentation. | Add `instrumentation.ts` if tracing is required at launch. |
| Load test | Not applicable | Enterprise checklist item. | Use a small synthetic smoke/load test outside Vercel Enterprise support if needed. |
| Production runtime errors | Improved locally | Vercel logs showed recent `/api/pipeline/stream` 500s from likely JSON SyntaxError; local handler now returns 400. Backend health is still failing upstream. | Deploy the web fixes, fix Cloud Run health, then watch runtime logs for recurrence. |

## Performance

| Checklist item | Status | Evidence | Next action |
| --- | --- | --- | --- |
| Speed Insights | Done | `@vercel/speed-insights` wired in app layout. | Confirm data appears after deploy and traffic. |
| TTFB review | Needs production observation | Observability showed traffic, but no local TTFB budget is enforced. | Review Vercel Observability after launch traffic. |
| Image Optimization | Done | `next/image` is used on dashboard; allowed remote image domains configured. | Continue avoiding raw `<img>` where optimization matters. |
| Script Optimization | Partial | No major third-party scripts beyond Vercel/Stripe allowances. | Use `next/script` if adding client scripts. |
| Font Optimization | Done | `next/font/google` now self-hosts Inter, JetBrains Mono, and Space Grotesk. | Watch build logs for font fetch failures. |
| Function region | Needs review | Vercel production function region is `iad1`; backend is Cloud Run `us-central1`. | Measure latency and consider region changes only with data. |
| Third-party proxy limitations | Not applicable unless Enterprise/CDN proxy requirements apply. | `uvai.io` is served by Vercel; DNS authority is Cloudflare. | Decide whether Cloudflare remains DNS-only or becomes a proxy layer. |

## Cost Optimization

| Checklist item | Status | Evidence | Next action |
| --- | --- | --- | --- |
| Fluid Compute | Done | Confirmed in dashboard screenshot. | Keep long route `maxDuration` settings aligned with actual use. |
| Usage optimization guides | Partial | Runbook has operational checks. | Review Vercel Usage after launch traffic. |
| Spend Management | Needs dashboard verification | Not exposed by available MCP tools. | Configure alerts and project pause policy. |
| Function max duration and memory | Partial | Long AI routes now declare explicit `maxDuration`. | Review memory after production invocations. |
| ISR revalidation | Not currently material | Current build is mostly static plus dynamic APIs. | Set explicit revalidation if ISR is introduced. |
| Image pricing opt-in | Needs dashboard verification | Depends on team creation/billing state. | Check Billing > Image Optimization pricing. |
| Large media to blob storage | Done/monitor | Public assets are normal favicon/OG/manifest assets. | Keep videos/GIFs out of git and use object/blob storage. |

## Residual Dependency Advisories

`npm audit --omit=dev --audit-level=moderate` still reports two moderate
findings through Next's nested `postcss@8.4.31`. The safe `uuid` update has
been applied and now resolves to `uuid@11.1.1`. The remaining low findings are
from AI SDK provider utility packages and require major-version AI SDK upgrades.

Do not upgrade a launch candidate to a Next canary or major AI SDK line without
an explicit release decision.

Current safe gate:

```bash
npm audit --omit=dev --audit-level=high
```

This exits successfully; the remaining advisory is moderate.
