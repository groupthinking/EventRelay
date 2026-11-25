# TASK: Honest Studio Events + Pro export toast

## 1. Goal & Scope
* **Objective:** Production dogfood on `pBsT6v-ciO8` (2026-11-22 ~2:00 AM CST) showed INSIGHT cards and unsigned Export dumping into Stripe. Stop both.
* **Context:** Live pack GET 200 has transcript/architecture/artifacts/tools and **no `events[]`**. Analysis workflow still fills `Video.events` as `type: 'insight'`. Live Events stage counts `visual_elements`. Export 402 assigns `window.location.href = checkoutUrl`.
* **Scope:**
  * `apps/web/src/lib/studio-pipeline-status.ts` — pack `events[]` only; Pro-required toast helper
  * `apps/web/src/components/studio/StudioIdeOutput.tsx` — never render insight cards without pack `events[]`
  * `apps/web/src/components/OneLoopStudio.tsx` — honest eventCount; 402 stays on page
  * `apps/web/src/components/studio/live/LiveStudioWorkspace.tsx` — Events stage from pack `events[]`, not visual_elements
  * `apps/web/src/lib/sample-pack.ts` — do not map visual_elements to insight events
 * *Initial check:* Do not invent events, do not enable Act, do not change G.A.T.E., do not auto-redirect to Stripe.

## 2. Execution Plan
- [x] Failing tests for empty pack events ≠ INSIGHT and 402 stay-on-page toast
- [x] Helpers + UI wiring
- [x] Focused Vitest green

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Pack with no `events[]` shows “no extracted events”, never INSIGHT cards, Events stage is 0, unsigned Export toasts Pro required and does not navigate to Stripe.
* **Verification Method:** Focused Vitest on the touched suites.
* **Proof Artifact:** `cd apps/web && npm test -- src/lib/__tests__/studio-pipeline-status.test.ts src/components/studio/__tests__/StudioIdeOutput.playflow.test.tsx src/lib/__tests__/sample-pack.test.ts src/components/__tests__/LiveStudio.streaming.test.tsx src/components/__tests__/OneLoopStudio.three-panel.test.tsx src/store/__tests__/dashboard-store.test.ts` → **6 files, 83 passed**. ESLint on touched files clean.

## 4. Post-Task Reflection
* **What was done:** Display Events only from pack `events[]`. Unsigned Export 402 stays on Studio with a Pro-required toast.
* **Why it was needed:** Live dogfood of `pBsT6v-ciO8` showed INSIGHT workflow cards and dumped unsigned Export into Stripe Checkout.
* **How it was tested:** Focused Vitest + ESLint. Did not complete live Stripe checkout. Did not browser-verify production (this branch is not deployed yet).
* **Follow-up:** Vercel Agent review on #2782 — `verifyIdentityPack` dropped `events[]`. Pass-through added with tests that a verified envelope with events still reaches `studioDisplayEvents`, and an envelope without events still stays empty.
