# GATE-3 Launch Config Report

**When:** 2026-07-10T17:59:52Z UTC
**Git:** `e70aa66a`
**Vercel project:** `garv1/v0-uvai` (Production env)
**Evidence dir:** `docs/control-plane/sessions/gate3-20260710T1759Z/`
**Method:** `vercel env ls production` (names only) + live HTTP probes (no secret values recorded)

---

## Executive verdict

**GATE-3 is NOT exit-complete.** Money path is **blocked live** by three hard gaps. Stripe product IDs on env **do not match** the Stripe account (renew fails). Auth is **broken** (NextAuth 500). Entitlement Redis is **OK via KV_* aliases**.

| Goal | Status | Live proof |
|------|--------|------------|
| G3-STRIPE-01 keys + price **names** on Vercel | **PARTIAL** | Secret + publishable + price vars **present**; prices **invalid** on live API |
| G3-STRIPE-02 webhook configured | **FAIL** | `POST /api/billing/webhook` → **503** `webhook_not_configured` |
| G3-TURN-01 Turnstile | **FAIL** | `POST /api/billing/checkout` → **403** `turnstile_not_configured` |
| G3-UPSTASH-01 durable entitlements | **PASS** (via alias) | `KV_REST_API_URL` + `KV_REST_API_TOKEN` present; code accepts as Upstash REST |
| G3-AUTH-01 NextAuth + Google | **FAIL** | `/api/auth/*` → **500** config problem; no `GOOGLE_OAUTH_*` / `NEXTAUTH_URL` on Vercel |
| G3-E2E-01 paid lifecycle | **NOT RUN** | Blocked by Turnstile + webhook + price/auth |

**Cannot sell Pro end-to-end on production today.**

---

## 1) Vercel Production env matrix (names only)

Source: `vercel-env-ls.txt` / `env-matrix.md`

### Launch-critical

| Variable | On Vercel Prod? | Live behavior if missing/wrong |
|----------|-----------------|--------------------------------|
| `STRIPE_SECRET_KEY` | YES | Required for checkout/renew |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | YES | Client Stripe.js |
| `STRIPE_PRICE_PRO_MONTHLY` | YES | Value present but **Stripe rejects price** on renew |
| `STRIPE_PRICE_PRO_ANNUAL` | YES | same class of risk |
| `STRIPE_WEBHOOK_SECRET` | **NO** | Webhook **503** |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY` | **NO** | UI may still mention turnstile; server has no secret |
| `TURNSTILE_SECRET_KEY` | **NO** | Checkout **403** `turnstile_not_configured` |
| `UPSTASH_REDIS_REST_URL` / `_TOKEN` | **NO** | |
| `KV_REST_API_URL` / `KV_REST_API_TOKEN` | **YES** | Code `resolveUpstashRedisCredentials()` accepts these → durability **configured** |
| `NEXTAUTH_SECRET` | YES | Alone insufficient |
| `NEXTAUTH_URL` | **NO** | Auth misconfig likely |
| `GOOGLE_OAUTH_CLIENT_ID` | **NO** | Auth **500** |
| `GOOGLE_OAUTH_CLIENT_SECRET` | **NO** | Auth **500** |
| `BACKEND_URL` / `NEXT_PUBLIC_BACKEND_URL` | YES | Agent dispatch dependency |
| `EVENTRELAY_API_KEY` | YES | BFF → API |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | YES | Product AI |
| `AI_GATEWAY_API_KEY` | YES | Optional gateway |
| `SENTRY_DSN` | YES | Observability |

Also present: Neon/Postgres/Supabase suite, XAI/GROK keys, Upstash **Search** (not Redis entitlement names).

---

## 2) Live HTTP probes (production uvai.io)

| Probe | HTTP | Body (truncated) | Interpretation |
|-------|------|-----------------|----------------|
| `GET /api/billing/status` | 200 | free / inactive | Status endpoint works |
| `POST /api/billing/checkout` `{}` | **403** | `turnstile_not_configured` | Turnstile secret missing |
| `POST /api/billing/checkout` + fake token | **403** | `turnstile_not_configured` | Same (fails before token verify) |
| `POST /api/billing/webhook` | **503** | `webhook_not_configured` | `STRIPE_WEBHOOK_SECRET` missing |
| `POST /api/billing/renew` `{}` | **500** | `No such price: 'price_1Tos02AmTgsI2zgNWx7onroJ'` | Price ID not in Stripe account for current secret key |
| `POST /api/billing/activate` `{}` | 400 | `session_id_required` | Expected validation |
| `GET /api/auth/providers` | **500** | server configuration problem | NextAuth not usable |
| `GET /api/auth/csrf` | **500** | same | |
| `GET /api/auth/session` | **500** | same | |
| `GET /pricing` | 200 | page loads; HTML contains “turnstile”/“stripe”/“checkout” strings | UI exists |
| `GET /login` | 307 / error shell | broken auth surface | Login not healthy |

Evidence files: `bill-status.txt`, `checkout-*.txt`, `webhook-*.txt`, `renew-empty.txt`, `auth-*.txt`, `pricing-page.txt`, `login-page.txt`.

---

## 3) Code ↔ config alignment

| Component | File | Reads | Prod status |
|-----------|------|-------|-------------|
| Turnstile | `lib/billing/turnstile.ts` | `TURNSTILE_SECRET_KEY` | Missing → hard fail |
| Checkout | `api/billing/checkout/route.ts` | Turnstile then Stripe | Blocked at Turnstile |
| Webhook | `api/billing/webhook/route.ts` | `STRIPE_WEBHOOK_SECRET` first | 503 if unset |
| Entitlements | `lib/billing/redis-credentials.ts` | `UPSTASH_REDIS_REST_*` **or** `KV_REST_API_*` | **KV present → OK** |
| Auth | `lib/auth.ts` | `NEXTAUTH_SECRET`, Google OAuth client id/secret; docs also want `NEXTAUTH_URL` | OAuth vars missing → 500 |

---

## 4) LAUNCH_CHECKLIST.md vs reality

| Checklist claim | Rechecked live |
|-----------------|----------------|
| Stripe products/prices DONE (2026-07-02) | Price **IDs stored** but Stripe API says **No such price** for monthly ID → **not DONE** for this secret/account |
| Webhook endpoint | Handler live but **not configured** (no secret) → **FAIL** |
| Turnstile | **FAIL** not configured |
| Upstash Redis | **PASS via Vercel KV env names** (not the UPSTASH_* names) |
| Google OAuth + NextAuth | **FAIL** 500 / missing OAuth env |

---

## 5) Ordered owner actions to finish GATE-3 (no code required first)

Do these in Vercel Production + Stripe + Cloudflare dashboards. Do **not** paste secret values into git/chat.

### P0 blockers (must fix before any paid customer)

1. **Stripe price / account consistency**
   - In Stripe Dashboard (same mode as `STRIPE_SECRET_KEY` — live vs test): confirm prices exist
   - If missing: recreate and set `STRIPE_PRICE_PRO_MONTHLY` / `ANNUAL`
   - Re-test: `POST /api/billing/renew` should not return `No such price` (may still need customer id; error should change)

2. **`STRIPE_WEBHOOK_SECRET`**
   - Stripe → Webhooks → endpoint `https://uvai.io/api/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Put signing secret in Vercel Production
   - Re-test: webhook without signature → **400** `missing_signature` (not 503)

3. **Turnstile**
   - Cloudflare Turnstile widget for `uvai.io`
   - Set `NEXT_PUBLIC_TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET_KEY` on Vercel
   - Redeploy (public key is client-bundled)
   - Re-test: checkout without token → `turnstile_token_missing` (not `turnstile_not_configured`)

4. **Google OAuth + NextAuth**
   - Set `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
   - Set `NEXTAUTH_URL=https://uvai.io`
   - Google redirect URI: `https://uvai.io/api/auth/callback/google`
   - Re-test: `GET /api/auth/providers` → **200** with google provider

### P1 after P0

5. Browser E2E (G3-E2E-01): sign in → checkout → Stripe test/live payment → webhook → `billing/status` shows pro
6. Confirm KV Redis actually read/write entitlement after webhook (optional redis CLI / status after paid session)

---

## 6) What we will NOT claim

- “Stripe is fully set up” — prices rejected by Stripe API
- “Billing works” — checkout 403, webhook 503
- “Users can sign in” — auth 500
- “Need Upstash-named vars only” — KV aliases satisfy code

---

## GATE-3 exit status

| Criterion | Met? |
|-----------|------|
| Env inventory with evidence | **YES** |
| Live probe of money path | **YES** |
| One paid lifecycle success | **NO** |
| Documented blockers with exact next steps | **YES** |

**GATE-3 status: COMPLETE as audit / incomplete as launch readiness.**
Launch readiness blocked on: **Turnstile + Webhook secret + Stripe price validity + Google OAuth**.
