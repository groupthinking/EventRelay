# KNOWN FAILURES — Live-measured only

**Started:** 2026-07-10T17:57Z
**Rule:** Only entries with probe date + evidence path. No rumor.

---

## KF-001 — Relative `status_url` breaks naive clients

| Field | Value |
|-------|--------|
| Seen | 2026-07-10 GATE-2 |
| Surface | `POST /api/pipeline` async response |
| Behavior | Returns `"status_url": "/api/jobs/{id}"` (relative) |
| Failure | Curl/clients that treat it as absolute URL get connection failure (HTTP 000) |
| Product impact | Medium — browsers OK if same origin; scripts/agents fail |
| Evidence | `sessions/gate2-20260710T1755Z/pipeline-post-async.json`; first poll attempts code 000 |
| Workaround | Prefix `https://uvai.io` |
| Fix later | GATE-5: return absolute URL or document contract |

---

## KF-002 — Sync pipeline (`async:false`) degrades to local-fallback + Gemini TIMEOUT

| Field | Value |
|-------|--------|
| Seen | 2026-07-10 GATE-2 |
| Surface | `POST https://uvai.io/api/pipeline` body `async:false` |
| Behavior | HTTP 200, `status: partial`, `pipeline: local-fallback`, `gemini_error.code: TIMEOUT` |
| Product impact | High for anyone expecting full analysis/codegen in one request |
| Evidence | `sessions/gate2-20260710T1755Z/pipeline-post-sync.json` |
| Note | Default path is async; sync is discouraged in code comments (`maxDuration` 60s) |

---

## KF-003 — Handoff messaging says backend unavailable while health says available

| Field | Value |
|-------|--------|
| Seen | 2026-07-10 GATE-2 sync response |
| Surface | same sync POST |
| Behavior | `backend.available: true` but `build_status: handoff_ready_backend_unavailable` and deployment blockers include “Backend pipeline is not available” |
| Product impact | Medium — confuses operators/users |
| Evidence | `pipeline-post-sync.summary.json` |
| Fix later | Align handoff copy with actual failure (Gemini timeout vs backend down) |

---

## KF-004 — Unauthenticated direct job API rejected (expected)

| Field | Value |
|-------|--------|
| Seen | 2026-07-10 |
| Surface | `GET https://api.uvai.io/api/v1/jobs/{id}` without key |
| Behavior | HTTP **401** `Authentication required` / `X-API-Key` |
| Product impact | None if clients use web proxy `/api/jobs/{id}` |
| Evidence | live curl 401 |
| Note | Web BFF injects `EVENTRELAY_API_KEY` — do not expose key to browser |

---

## Not failures (baseline OK)

| Check | Result |
|-------|--------|
| Async kickoff + job complete + transcript | **Works** for Me-at-the-zoo (`job_638c836f7b`) |
| Health endpoints | **Works** |
| Billing status free shape | **Works** |

---

## Security baseline (not re-exploited in GATE-2)

See repo `eventrelay-audit-report.md` — High cluster: yt-dlp SSRF/arg injection, ungated Veo. Tracked for GATE-4. GATE-2 did **not** attempt exploit traffic.

---

## KF-005 — Checkout blocked: Turnstile not configured (prod)

| Field | Value |
|-------|--------|
| Seen | 2026-07-10 GATE-3 |
| Surface | `POST https://uvai.io/api/billing/checkout` |
| Behavior | HTTP **403** `{"error":"turnstile_not_configured"}` |
| Root | `TURNSTILE_SECRET_KEY` absent on Vercel Production (`NEXT_PUBLIC_TURNSTILE_SITE_KEY` also absent) |
| Evidence | `sessions/gate3-20260710T1759Z/checkout-empty.txt` |
| Fix | Add Cloudflare Turnstile keys to Vercel Production + redeploy |

---

## KF-006 — Webhook not configured (prod)

| Field | Value |
|-------|--------|
| Seen | 2026-07-10 GATE-3 |
| Surface | `POST https://uvai.io/api/billing/webhook` |
| Behavior | HTTP **503** `{"error":"webhook_not_configured"}` |
| Root | `STRIPE_WEBHOOK_SECRET` not in Vercel Production env list |
| Evidence | `sessions/gate3-20260710T1759Z/webhook-nosig.txt` |
| Fix | Stripe webhook endpoint + secret on Vercel |

---

## KF-007 — Stripe price ID rejected by Stripe API

| Field | Value |
|-------|--------|
| Seen | 2026-07-10 GATE-3 |
| Surface | `POST /api/billing/renew` |
| Behavior | HTTP **500** `No such price: 'price_1Tos02AmTgsI2zgNWx7onroJ'` |
| Root | Env has `STRIPE_PRICE_PRO_MONTHLY` but price not found for the Stripe account/mode tied to `STRIPE_SECRET_KEY` (live/test mismatch or deleted price) |
| Evidence | `sessions/gate3-20260710T1759Z/renew-empty.txt` |
| Fix | Align price IDs with Dashboard for that secret; update Vercel env |

---

## KF-008 — NextAuth / Google sign-in broken (prod)

| Field | Value |
|-------|--------|
| Seen | 2026-07-10 GATE-3 |
| Surface | `GET /api/auth/providers`, `/csrf`, `/session` |
| Behavior | HTTP **500** “problem with the server configuration” |
| Root | `NEXTAUTH_SECRET` present but `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` / `NEXTAUTH_URL` not on Vercel Production list |
| Evidence | `sessions/gate3-20260710T1759Z/auth-providers.txt` |
| Fix | Add Google OAuth + `NEXTAUTH_URL=https://uvai.io` |

---

## KF-009 — Entitlement Redis names (not a failure)

| Field | Value |
|-------|--------|
| Note | `UPSTASH_REDIS_REST_*` absent, but `KV_REST_API_URL` + `KV_REST_API_TOKEN` **present** |
| Code | `lib/billing/redis-credentials.ts` accepts either pair |
| Verdict | Durable entitlements **configured** via Vercel KV naming |
