# TASK: UVAI Workflow Pro Stripe checkout (slice 1)

## 1. Goal & Scope
* **Objective:** Point EventRelay web checkout at UVAI Workflow Pro $39/mo and $390/yr, with Turnstile still fail-closed.
* **Context:** Live Stripe (UVAI account) already has product `prod_V9TYXeVHLQGrVW` and prices `price_1U9AbLAmTgsI2zgNEZD4Kwed` / `price_1U9AbLAmTgsI2zgN0SM70JN9`. Checkout-config still encodes stale EventRelay Pro $19/$180 amounts.
* **Scope:**
  * Modify: `checkout-config.ts`, `stripe-checkout.ts`, billing tests, `REVENUE-PROCESS.md`, `LAUNCH_CHECKLIST.md`, `.env.example` comments, revenue-spine helper amounts.
  * Do not touch Video Pack, Mission Workspace, Agent Factory, Origin G.A.T.E., Chrome/mobile/desktop, FORGE, VIZUL, Workbench, Living Notebook, ClipToAction, or the cancelled contest.
  * Do not add Maintain $199/mo or Ship per-job.
  * Do not hardcode `STRIPE_SECRET_KEY`.
 * *Initial check:* Existing files cover this. No new production modules.

## 2. Execution Plan
- [x] Update unit tests to assert 3900 / 39000 cents and `UVAI Workflow Pro`
- [x] Watch those tests fail against current 1900 / 18000 + EventRelay Pro
- [x] Update `checkout-config.ts` amounts, product name, documented last-resort price IDs (env preferred; production still requires env)
- [x] Default production success/cancel base URL to `https://uvai.io` so redirects stay on `/pricing`
- [x] Sweep named docs and billing tests; keep Turnstile fail-closed tests
- [x] Run focused billing tests; open PR against main
- [x] Pricing UI shows UVAI Workflow Pro at $39/mo and $390/yr

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Checkout params and `/pricing` UI are Workflow Pro $39/$390. Production still throws if `STRIPE_PRICE_PRO_*` is missing. Turnstile still 403s checkout. Success/cancel stay on `/pricing` under `https://uvai.io`. Domain stays on Vercel project v0-uvai.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/billing src/app/api/__tests__/billing src/app/pricing`
* **Proof Artifact:** 16 files, 59 passed (2026-08-31). PR: https://github.com/groupthinking/EventRelay/pull/1599

## 4. Post-Task Reflection
* **What was done:** Replaced stale EventRelay Pro $19/$180 checkout amounts and `/pricing` copy with UVAI Workflow Pro $39/$390. Production still requires `STRIPE_PRICE_PRO_*`. Non-prod last-resort fallbacks are the live Workflow Pro Price IDs. Production success/cancel default to `https://uvai.io/pricing`. Turnstile fail-closed tests unchanged. No Origin/domain retarget.
* **Why it was needed:** Live Stripe already sells Workflow Pro at $39/$390; UI and checkout-config still hid or encoded the cancelled $19/$180 catalog.
* **How it was tested:** RED: catalog helper and pricing source tests failed. GREEN: 59 billing+pricing tests passed, including Turnstile 403 and production missing-env throw.
