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
- [ ] Run focused billing tests; open PR against main

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Checkout params are Workflow Pro $39/$390. Production still throws if `STRIPE_PRICE_PRO_*` is missing. Turnstile still 403s checkout. Success/cancel stay on `/pricing` under `https://uvai.io`.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/billing/__tests__/checkout-config.test.ts src/lib/billing/__tests__/stripe-checkout.test.ts src/app/api/__tests__/billing-checkout-route.test.ts`
* **Proof Artifact:** `npx vitest run src/lib/billing src/app/api/__tests__/billing` → 15 files, 56 passed (2026-08-31). PR URL pending.

## 4. Post-Task Reflection
* **What was done:** Replaced stale EventRelay Pro $19/$180 checkout amounts with UVAI Workflow Pro $39/$390. Production still requires `STRIPE_PRICE_PRO_*`. Non-prod last-resort fallbacks are the live Workflow Pro Price IDs. Production success/cancel default to `https://uvai.io/pricing`. Turnstile fail-closed tests unchanged.
* **Why it was needed:** Live Stripe already sells Workflow Pro at $39/$390; checkout-config and docs still encoded the cancelled $19/$180 catalog.
* **How it was tested:** RED: 8 tests failed on 1900/18000 and missing fallbacks. GREEN: 56 billing tests passed, including Turnstile 403 and production missing-env throw.
