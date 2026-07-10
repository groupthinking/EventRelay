# Env presence matrix (names only)
Source: `docs/control-plane/sessions/gate3-20260710T1759Z/vercel-env-ls.txt`

| Var | Present on Vercel Production | Role |
|-----|------------------------------|------|
| `STRIPE_SECRET_KEY` | YES | Stripe server |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | YES | Stripe publishable |
| `STRIPE_PRICE_PRO_MONTHLY` | YES | Pro monthly price |
| `STRIPE_PRICE_PRO_ANNUAL` | YES | Pro annual price |
| `STRIPE_WEBHOOK_SECRET` | **NO** | Webhook signing (critical) |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY` | **NO** | Turnstile site |
| `TURNSTILE_SECRET_KEY` | **NO** | Turnstile secret |
| `UPSTASH_REDIS_REST_URL` | **NO** | Entitlement durability (name A) |
| `UPSTASH_REDIS_REST_TOKEN` | **NO** | Entitlement durability (name A) |
| `KV_REST_API_URL` | YES | Vercel KV / Redis alt |
| `KV_REST_API_TOKEN` | YES | Vercel KV token |
| `REDIS_URL` | YES | Redis URL alt |
| `NEXTAUTH_SECRET` | YES | Auth secret |
| `NEXTAUTH_URL` | **NO** | Auth URL |
| `BACKEND_URL` | YES | Backend |
| `NEXT_PUBLIC_BACKEND_URL` | YES | Public backend |
| `EVENTRELAY_API_KEY` | YES | BFF→API key |
| `GEMINI_API_KEY` | YES | Gemini |
| `OPENAI_API_KEY` | YES | OpenAI |
| `SENTRY_DSN` | YES | Sentry |
