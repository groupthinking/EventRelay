# TASK: Fold Get Pro checkout onto Home

## 1. Goal & Scope
* **Objective:** Put the live Workflow Pro checkout (Turnstile + Continue to UVAI Workflow Pro $39/mo, monthly/annual) on Home (`/`), reusing `ProCheckoutButton` / `POST /api/billing/checkout`. Keep `/pricing` as the deeper plans page that still checkouts.
* **Context:** PR #1668 made Home a sell shell with Get Pro linking to `/pricing`. CoS authorized folding checkout onto Home (2026-09-08 after HOME SIGNED). Live checkout already works on `/pricing`.
* **Scope:**
  * Modify: Home page, new Home checkout island, Nav Get Pro target, home-sell tests, Playwright smoke.
  * Reuse: `ProCheckoutButton`, Turnstile, existing Stripe price IDs. No new SKUs.
  * Do not break paste → Studio handoff. Do not add Origin G.A.T.E., ClipToAction, or Maintain/Ship checkout.
 * *Initial check:* `ProCheckoutButton` already exists. Add a Home client island instead of a second Stripe path.

## 2. Execution Plan
- [x] RED: Home-sell tests require `HomeProCheckout` + `ProCheckoutButton` on `/`
- [x] GREEN: Mount Turnstile + monthly/annual checkout on Home; keep `/pricing`
- [x] Nav Get Pro lands on `/#get-pro`; Pricing nav still goes to `/pricing`
- [x] Playwright: Home has checkout controls; paste handoff still works
- [x] Focused vitest; commit; PR
- [x] CoS AMBER: honest Home copy — no arbitrary-video production E2E / guaranteed transcript claim

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Cold `/` still sell hero + paste + $39/$390/$199. User completes Turnstile → Stripe Checkout $39 from Home. `/pricing` still checkouts. Paste still goes to `/studio?video=`.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/home-sell-surface.test.ts src/app/pricing/__tests__/pricing-catalog.test.ts src/lib/__tests__/studio-handoff.test.ts`
* **Proof Artifact:** `cd apps/web && npx vitest run` — 88 files, 558 passed / 1 skipped.

## 4. Post-Task Reflection
* **What was done:** Added `HomeProCheckout` on `/` that reuses `ProCheckoutButton` (Turnstile → existing `/api/billing/checkout`). Nav Get Pro targets `/#get-pro`. `/pricing` remains the full plans page with the same checkout. Ship/Maintain stay copy-only. Home hero now says Studio workbench + variable transcript quality, not “Ship the work” / “Not a demo.”
* **Why it was needed:** After #1668 Home sold Pro by linking away to `/pricing`. CoS authorized folding live Get Pro onto cold `/`, then AMBER-guarded Home copy so it does not claim production E2E or a guaranteed transcript.
* **How it was tested:** RED: home-sell tests failed without `HomeProCheckout`. GREEN: vitest + Playwright smoke for checkout island, paste handoff, and honest Home copy.
