# UVAI Workflow Pro — subscription revenue process

Recurring revenue is anchored on **UVAI Workflow Pro** ($39/mo or $390/yr) via Stripe Checkout, with acquisition protected by Cloudflare Turnstile and returning-user flows traced via kaizen-style logs.

## Entry point

- **Pricing UI:** `src/app/pricing/page.tsx`
- **Pro CTA:** `ProCheckoutButton` → `POST /api/billing/checkout` (Turnstile required)
- **Renewal:** `POST /api/billing/renew` (no Turnstile; for returning subscribers)

## Environment

Copy from Vercel or use test values in `.env.local`:

| Variable | Purpose |
|----------|---------|
| `STRIPE_SECRET_KEY` | Server-side Stripe API |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Client Stripe.js (future portal) |
| `STRIPE_PRICE_PRO_MONTHLY` / `STRIPE_PRICE_PRO_ANNUAL` | **Required in production.** Last-resort documented fallbacks (non-prod only): `price_1U9AbLAmTgsI2zgNEZD4Kwed` ($39/mo, lookup `uvai-workflow-pro-monthly`) and `price_1U9AbLAmTgsI2zgN0SM70JN9` ($390/yr, lookup `uvai-workflow-pro-annual`). Product `prod_V9TYXeVHLQGrVW`. Never reuse dead EventRelay Pro $19/$180 IDs. |
| `STRIPE_WEBHOOK_SECRET` | Required for `/api/billing/webhook` (checkout.session.completed) |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY` | Widget on pricing |
| `TURNSTILE_SECRET_KEY` | Server siteverify |
| `GROK_BILLING_LEAD_MODEL` | Metadata on subscriptions (`grok-4-1-fast` default) |
| `NEXT_PUBLIC_APP_URL` | Checkout success/cancel URLs |

Local Turnstile test keys (always pass): see [Cloudflare Turnstile testing](https://developers.cloudflare.com/turnstile/troubleshooting/testing/).

## Bootstrap

```bash
cd apps/web
vercel link    # if not linked
vercel env pull .env.local --yes
# Ensure Turnstile + Grok vars from .env.example are present
npm install
npm test
npm run build
npm run dev
```

## Verification checklist

1. Open `/pricing` → Turnstile widget renders on Pro card.
2. Complete widget → click Pro CTA → JSON with `sessionId` and Stripe `url`.
3. `curl -X POST localhost:3000/api/billing/renew -H 'content-type: application/json' -d '{"annual":false}'` → renewal session + `[kaizen]` logs in server stdout.

## Code map

| Path | Role |
|------|------|
| `src/lib/billing/checkout-config.ts` | Pure price/URL resolution |
| `src/lib/billing/stripe-checkout.ts` | Stripe session creation |
| `src/lib/billing/turnstile.ts` | Cloudflare siteverify |
| `src/lib/billing/grok-lead.ts` | Grok/Composer metadata on paid tier |
| `src/lib/billing/kaizen-trace.ts` | Structured trace for renewal/debug |

## Post-payment fulfillment

1. **Webhook** `POST /api/billing/webhook` — handles `checkout.session.completed`, `customer.subscription.updated/deleted`; activates Pro in entitlement store (Redis + memory).
2. **Client activate** `POST /api/billing/activate` — pricing success URL calls with `session_id`; sets `er_billing_email` cookie.
3. **Status** `GET /api/billing/status` — plan, features, Grok routing for returning users.

## Feature gating (Pro unlocks)

| Feature | Free | Pro |
|---------|------|-----|
| AI chat | 5/day | Unlimited, `grok-composer` lead model |
| Agent dispatch | Blocked (402) | Allowed |
| API headers | — | `X-Lead-Model`, `X-Billing-Plan` on backend proxy |

## Returning users

`ProRenewPanel` on `/pricing` calls `POST /api/billing/renew` (no Turnstile). Identity comes from the trusted `er_billing_email` cookie only. Kaizen traces: `renewal_start` → `renewal_session`.

**Production durability:** `saveEntitlement` requires `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` when `NODE_ENV=production`. Local dev may use `ENTITLEMENT_STORE_PATH` file fallback.

**Checkout → activate:** Webhook saves Pro entitlement and `linkCheckoutActivation(sessionId)`. `POST /api/billing/activate` resolves via session link first (not email fallback).

## ClawHub marketplace (MyXstack)

`myxteam/src/gateway/server-methods/skills.ts` calls `gatePremiumSkillInstall` before `installSkill` for slugs in `CLAWHUB_PREMIUM_SKILL_SLUGS`. Pass `billingCookie` on `skills.install` for repeat premium installs.

## Production Turnstile

Replace test keys with a widget created in the Cloudflare dashboard (or `/turnstile-spin` wizard). Register `localhost`, preview URL, and production domain on the widget.

## Verification (revenue spine)

```bash
cd apps/web
SCRATCH=/path/to/scratch node scripts/run-revenue-spine.mjs
```

Truncates scratch logs, runs checkout → signed `checkout.session.completed` webhook → activate → status → pro chat → renew **twice**. MyXstack gate: `myxteam/skills/premium-gate.ts` checks `/api/billing/status`.

## Non-goals (this repo slice)

- Live Gumroad/printable PDF products
- ClawHub marketplace server (external at clawhub.ai)
- Production marketing — only the technical subscription loop