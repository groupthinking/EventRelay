# EventRelay Launch Checklist — Selling Subscriptions

The goal: a customer can **sign in → pay for Pro → reliably use the product**.
This checklist is the authoritative, ordered guide to get there. It reflects a
July 2026 production-readiness audit.

**Good news:** the app already builds, the backend imports, the full frontend
and backend test suites pass, and the Stripe subscription flow is real and
well-tested. The remaining gap is **provisioning + configuration**, not missing
feature code. The items below are what actually gate launch.

---

## 0. Where each secret lives

Two env files, read by two different runtimes — put each var in the right place:

| File | Read by | Put here |
|---|---|---|
| `apps/web/.env.local` (copy from `apps/web/.env.example`) | Next.js app (billing, auth, chat, pipeline) | Stripe, Turnstile, Upstash, NextAuth, AI keys |
| `.env` (copy from `.env.example`) | Python FastAPI backend | Backend AI keys, DB, `BACKEND_URL` targets, MCP creds |

The **platform subscription billing runs entirely in the Next.js app**, so all
billing/auth vars go in `apps/web/.env.local` (or your Vercel project settings),
**not** the root `.env`.

---

## 1. Launch-gating blockers (must do)

### 1.1 Stripe products & prices — ⏳ TEST MODE (LIVE prices NOT yet created)

> **Reality check (verified 2026-07-14):** production checkout runs in Stripe
> **TEST mode**. The LIVE prices this section used to claim as "DONE" are **DEAD** —
> Stripe now returns `No such price` for them (evidence:
> `docs/control-plane/sessions/gate3-reprobe-20260714T2011Z/renew-empty.body`).
> **DO NOT re-apply `price_1Tos02AmTgsI2zgNWx7onroJ` or
> `price_1Tos0AAmTgsI2zgNSu5lwBv6`** — they were reverted and will 500 checkout.

**Current production prices (Stripe TEST mode, account `acct_1ScN2hAmTgsI2zgN`):**

- **$19/mo** (test): `price_1TtCZXPPnkyjEyFR8dYmDo52` — produces `cs_test_` sessions
- **$180/yr** (test): `price_1TtCZYPPnkyjEyFRLMLPjmzE`

The Vercel Production env carries the **env-var names** below (do not hardcode any
price ID as "done" in this doc — the authoritative IDs live only in Vercel/Stripe):
  ```
  STRIPE_SECRET_KEY=sk_test_...          # currently TEST; swap to sk_live_ at cutover
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
  STRIPE_WEBHOOK_SECRET=whsec_...        # from step 1.2 (configured — verified)
  STRIPE_PRICE_PRO_MONTHLY=<test monthly price id above>
  STRIPE_PRICE_PRO_ANNUAL=<test annual price id above>
  ```
- Without the two `STRIPE_PRICE_*` IDs, `requireStripePriceId()` throws and
  checkout 500s. Price IDs are not secrets; the `sk_` key and `whsec_` secret are.

**🔴 LIVE cutover (required before real revenue):** create a fresh LIVE-mode
Product + recurring Prices on `acct_1ScN2hAmTgsI2zgN`, record the NEW live price
IDs, set them plus `sk_live_` / `pk_live_` / a live `whsec_` in Vercel Production,
then re-run the gate3 probe and confirm the renew session returns `cs_live_`
(not `cs_test_`) with no "No such price" error **before** charging real cards.

> **Local drift:** `apps/web/.env.local` (gitignored) currently sets a THIRD
> divergent pair (`price_1TnYlW…`) matching neither prod nor the dead IDs.
> Reconcile it to the TEST IDs above for local↔prod parity.

### 1.2 Stripe webhook endpoint — ✅ CONFIGURED (test mode; redo for live at cutover)
Verified 2026-07-14: unsigned POST → `400 missing_signature` (not 503), bad signature → `400`. `STRIPE_WEBHOOK_SECRET` is live in Vercel Production for endpoint `we_1TtCYr…`. At LIVE cutover, create a new **live-mode** webhook and swap in its `whsec_`.
Original setup steps (for the live re-do):
- In Stripe Dashboard (live mode) → Developers → Webhooks, add an endpoint:
  `https://uvai.io/api/billing/webhook`.
- Subscribe to: `checkout.session.completed`,
  `customer.subscription.updated`, `customer.subscription.deleted`.
- Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
- The handler (`api/billing/webhook/route.ts`) returns 503 until this is set.
- (Webhook creation isn't exposed via the Stripe MCP, hence manual.)

### 1.3 Cloudflare Turnstile (checkout bot-gate) — ✅ LIVE (verified 2026-07-14)
Live keys are set in Vercel Production and validating: fake token → `403 turnstile_verification_failed` (a configured, working gate — not `turnstile_not_configured`). `/api/billing/checkout` is gated by Turnstile; unset → **every new subscriber gets 403**.
- Create a Turnstile widget at Cloudflare → get site key + secret.
- Set in `apps/web/.env.local`:
  ```
  NEXT_PUBLIC_TURNSTILE_SITE_KEY=...
  TURNSTILE_SECRET_KEY=...
  ```
- For local/dev, Cloudflare's always-pass test keys work (already in
  `apps/web/.env.example`): site `1x00000000000000000000AA`,
  secret `1x0000000000000000000000000000000AA`.

### 1.4 Upstash Redis (durable entitlements) — ⏳ UNVERIFIED in prod
Code confirms the guard is correct (REST-only: reads `UPSTASH_REDIS_REST_URL/TOKEN` or `KV_REST_API_URL/TOKEN`; no `redis://`/ioredis path), but whether a Vercel integration is actually injecting those REST creds into Production **cannot be confirmed from the repo** (sensitive env). Verify on the integration page, or prove it by completing one paid E2E and checking the entitlement persists. Paid status must survive serverless cold starts / multiple instances. In
production `assertEntitlementDurability()` **throws on boot** without Upstash.
- **Easiest path:** install the Upstash integration from the Vercel project's
  Integrations settings (`vercel.com/<team>/<project>/settings/integrations`)
  and create a Redis DB through it. Vercel **auto-injects**
  `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` into the project env —
  exactly the vars `entitlement-store.ts` reads, so no manual copying.
  (This is an OAuth click-through; it can't be done via API/MCP.)
- Manual alternative: create a DB at upstash.com and set the two vars yourself
  in `apps/web/.env.local` / Vercel env.

### 1.5 Google OAuth + NextAuth (sign-in) — ✅ LIVE (providers 200)
Verified 2026-07-14: `/api/auth/providers` returns Google and `/api/auth/csrf` returns a token, so `NEXTAUTH_SECRET` + Google creds are set in Production. Auth is Google-only and stays **off until `NEXTAUTH_SECRET` is set**.
- Create a Google OAuth app (Authorized redirect URI:
  `https://<domain>/api/auth/callback/google`).
- Set in `apps/web/.env.local`:
  ```
  NEXTAUTH_SECRET=...            # openssl rand -base64 32
  NEXTAUTH_URL=https://<domain>
  GOOGLE_OAUTH_CLIENT_ID=...
  GOOGLE_OAUTH_CLIENT_SECRET=...
  ```
- Decision: confirm Google-only sign-up is acceptable for paying customers
  (no email/password path exists today).

### 1.6 AI provider keys (core product + Pro chat)
- At minimum one of Gemini / OpenAI for the transcript→events pipeline.
- `XAI_API_KEY` for Pro Grok chat.
- Set the relevant keys in `apps/web/.env.local` (frontend pipeline) and `.env`
  (backend), per `.env.example`.

### 1.7 Vercel AI Gateway (recommended)
The frontend already prefers the Gateway when configured
(`apps/web/src/lib/vercel-ai-gateway.ts`; e.g. `extract-events/route.ts` calls
`gatewayChat()` when `hasAiGatewayKey()`), falling back to direct
Gemini/OpenAI otherwise. Enabling it buys unified billing, one key for many
providers, failover, spend caps, and request observability — zero code changes.
- Set `AI_GATEWAY_API_KEY` (or `VERCEL_AI_GATEWAY_API_KEY`) in the Vercel env.
- Optional overrides: `VERCEL_AI_GATEWAY_MODEL` (default
  `google/gemini-2.5-flash`) and `VERCEL_AI_GATEWAY_EMBEDDING_MODEL` (default
  `openai/text-embedding-3-small`).
- Leave unset to keep direct-provider behavior.

---

## 2. Agent dispatch (Pro feature) — backend deploy

Agent dispatch is gated to Pro but requires the **FastAPI backend deployed**;
Vercel has none by default, so `/api/agents/dispatch` returns 503.
- **Decision: deploy the backend now** (agreed). Use the Cloud Run manifests in
  `infrastructure/`; then set `BACKEND_URL` / `NEXT_PUBLIC_BACKEND_URL` in the
  Vercel project to the deployed URL.
- Backend deploy image should install the `[youtube]` extra so server-side
  transcript capture (`youtube-transcript-api`, `yt-dlp`) works without leaning
  on paid AI fallbacks.
- Run Alembic migrations against the prod DB (Postgres) before first traffic.

*(This is tracked as follow-up work after the code/CI hygiene PR lands.)*

---

## 3. Verification before charging real cards

1. `npm install && npm run build` — frontend builds (verified in CI).
2. Backend: install in a clean venv (`python -m venv .venv && . .venv/bin/activate
   && pip install -e .[dev,youtube]`), then `uvicorn src.youtube_extension.main:app`.
3. In test mode: sign in with Google → open `/pricing` → checkout with a Stripe
   **test card** (`4242 4242 4242 4242`) → confirm the webhook flips you to Pro
   and Pro chat / agent dispatch unlock.
4. Confirm entitlement survives a redeploy (Upstash durability).
5. Flip Stripe + Turnstile to **live** keys only after the full test-mode flow
   passes end to end.

---

## 4. Known non-blocking follow-ups

- **Webhook robustness:** add idempotency keys and handle
  `invoice.payment_failed` (dunning) for recurring-revenue reliability
  (`api/billing/webhook/route.ts`).
- **Dead code:** `src/integration/routes.py` (the "monetize generated apps"
  feature, unrelated to subscriptions) imports a non-existent `src.integrations`
  package and is not mounted anywhere. Fix its imports + package exports, or
  remove it, before wiring it up.
- **Backend install hygiene:** `pip install -e .[dev]` against a system Python
  with Debian's `packaging` can fail (`RECORD file not found`); always use a
  clean venv for the backend.
