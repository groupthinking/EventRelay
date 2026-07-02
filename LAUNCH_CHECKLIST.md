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

### 1.1 Stripe products & prices (test mode first)
The checkout code requires two recurring Price IDs (`checkout-config.ts`).
- Create a **Product** "EventRelay Pro" in Stripe (test mode).
- Add two recurring **Prices**: **$19/mo** and **$180/yr**.
- Set in `apps/web/.env.local`:
  ```
  STRIPE_SECRET_KEY=sk_test_...
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
  STRIPE_WEBHOOK_SECRET=whsec_...        # from step 1.2
  STRIPE_PRICE_PRO_MONTHLY=price_...     # the $19/mo Price ID
  STRIPE_PRICE_PRO_ANNUAL=price_...      # the $180/yr Price ID
  ```
- Without the two `STRIPE_PRICE_*` IDs, `requireStripePriceId()` throws and
  checkout 500s.

### 1.2 Stripe webhook endpoint
- In Stripe Dashboard → Developers → Webhooks, add an endpoint pointing at
  `https://<your-domain>/api/billing/webhook`.
- Subscribe to at least: `checkout.session.completed`,
  `customer.subscription.updated`, `customer.subscription.deleted`.
- Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
- The handler (`api/billing/webhook/route.ts`) returns 503 until this is set.

### 1.3 Cloudflare Turnstile (checkout bot-gate)
`/api/billing/checkout` is gated by Turnstile; unset → **every new subscriber
gets 403**.
- Create a Turnstile widget at Cloudflare → get site key + secret.
- Set in `apps/web/.env.local`:
  ```
  NEXT_PUBLIC_TURNSTILE_SITE_KEY=...
  TURNSTILE_SECRET_KEY=...
  ```
- For local/dev, Cloudflare's always-pass test keys work (already in
  `apps/web/.env.example`): site `1x00000000000000000000AA`,
  secret `1x0000000000000000000000000000000AA`.

### 1.4 Upstash Redis (durable entitlements)
Paid status must survive serverless cold starts / multiple instances. In
production `assertEntitlementDurability()` **throws on boot** without Upstash.
- Create an Upstash Redis DB → REST URL + token.
- Set in `apps/web/.env.local`:
  ```
  UPSTASH_REDIS_REST_URL=https://...upstash.io
  UPSTASH_REDIS_REST_TOKEN=...
  ```

### 1.5 Google OAuth + NextAuth (sign-in)
Auth is Google-only and stays **off until `NEXTAUTH_SECRET` is set**.
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
