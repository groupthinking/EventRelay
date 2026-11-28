# Plan 001: Require verified billing identity or Turnstile on `/api/billing/renew`

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 25c5e936e..HEAD -- apps/web/src/app/api/billing/renew/route.ts apps/web/src/app/api/billing/checkout/route.ts`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `25c5e936e` (`origin/main`), 2026-11-19

## Why this matters

`/api/billing/checkout` is gated behind Cloudflare Turnstile (`verifyTurnstileToken`) to stop automated Stripe Checkout session flooding and card-testing bots. However, `/api/billing/renew` is also on `PUBLIC_API_EXACT` and calls `createProCheckoutSession(...)` without requiring either a trusted billing identity (`resolveTrustedBillingEmail`) or a valid Turnstile token. Any unauthenticated bot can bypass Turnstile completely by posting to `/api/billing/renew`.

## Current state

- `apps/web/src/app/api/billing/renew/route.ts` — public renewal checkout endpoint; currently proceeds to Stripe even when `email` is `null` and without Turnstile.
- `apps/web/src/app/api/billing/checkout/route.ts` — exemplar sibling route showing the exact `verifyTurnstileToken` call and error response shape (`403` with `{ error, code: 'turnstile_rejected' }`).

Excerpt of `apps/web/src/app/api/billing/renew/route.ts:7-31` at `25c5e936e`:

```ts
export async function POST(req: NextRequest) {
  let body: { annual?: boolean };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'invalid_json', code: 'invalid_json' }, { status: 400 });
  }

  const email = await resolveTrustedBillingEmail(req);
  const entitlement = email ? await getEntitlement(email) : null;
  const customerId = entitlement?.stripeCustomerId;
...
  try {
    const result = await createProCheckoutSession({
      annual: Boolean(body.annual),
      customerEmail: email ?? undefined,
      customerId,
      flow: 'renewal',
    });
```

Convention to match (`apps/web/src/app/api/billing/checkout/route.ts:14-33`):
- Return `{ error: '<machine_code>', code: '<machine_code>' }` JSON envelopes.
- Never return raw Stripe SDK or Cloudflare response text to clients.
- Emit `kaizenObserve('billing', ...)` structured telemetry on rejection/success.

## Commands you will need

| Purpose   | Command                                                                 | Expected on success |
|-----------|-------------------------------------------------------------------------|---------------------|
| Typecheck | `cd apps/web && npx tsc --noEmit`                                       | exit 0, no errors   |
| Unit test | `cd apps/web && npx vitest run src/lib/billing/__tests__/`              | all tests pass      |
| Full web  | `cd apps/web && npx vitest run`                                         | all tests pass      |

## Scope

**In scope** (the only files you should modify):
- `apps/web/src/app/api/billing/renew/route.ts`
- `apps/web/src/app/api/billing/renew/__tests__/route.test.ts` (create)

**Out of scope** (do NOT touch, even though they look related):
- `apps/web/src/lib/auth-paths.ts` — keep `/api/billing/renew` on `PUBLIC_API_EXACT` so signed `er_billing_email` cookie holders without a NextAuth session can still renew.
- `apps/web/src/app/api/billing/checkout/route.ts` — already enforces Turnstile.
- `apps/web/src/components/billing/ProRenewPanel.tsx` — only renders for returning users with a billing identity.

## Git workflow

- Branch from `origin/main`: `fix/billing-renew-identity-gate`
- Conventional Commits message: `fix(security): require trusted billing identity on /api/billing/renew`
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Reject anonymous callers in `apps/web/src/app/api/billing/renew/route.ts`

Right after `const email = await resolveTrustedBillingEmail(req);`, add a fail-closed guard:

```ts
  if (!email) {
    kaizenObserve('billing', 'renewal_rejected', 'Anonymous renewal attempt blocked', {
      decision: 'unauthenticated_renewal',
    });
    return NextResponse.json(
      { error: 'billing_identity_required', code: 'billing_identity_required' },
      { status: 401 },
    );
  }
```

Then pass `customerEmail: email` (no longer `email ?? undefined`) to `createProCheckoutSession`.

**Verify**: `cd apps/web && npx tsc --noEmit` → exit 0, no errors.

### Step 2: Add unit tests for `/api/billing/renew`

Create `apps/web/src/app/api/billing/renew/__tests__/route.test.ts` testing:
1. Anonymous request (`resolveTrustedBillingEmail` returns `null`) → HTTP `401` with `{ error: 'billing_identity_required', code: 'billing_identity_required' }` and `createProCheckoutSession` is NOT called.
2. Authenticated / signed-cookie request (`resolveTrustedBillingEmail` returns `'pro@example.com'`) → calls `createProCheckoutSession` with `customerEmail: 'pro@example.com'`, `customerId`, `flow: 'renewal'` and returns HTTP `200`.
3. Invalid JSON body → HTTP `400` `{ error: 'invalid_json', code: 'invalid_json' }`.

**Verify**: `cd apps/web && npx vitest run src/app/api/billing/renew/__tests__/route.test.ts` → 3/3 tests pass.

## Test plan

- File: `apps/web/src/app/api/billing/renew/__tests__/route.test.ts` (model after `apps/web/src/lib/billing/__tests__/billing-spine.integration.test.ts`).
- Verification: `cd apps/web && npx vitest run` → exit 0, all tests pass.

## Done criteria

- [ ] `cd apps/web && npx tsc --noEmit` exits 0
- [ ] `cd apps/web && npx vitest run src/app/api/billing/renew/__tests__/route.test.ts` passes all 3 cases
- [ ] `cd apps/web && npx vitest run` exits 0
- [ ] Only in-scope files modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `apps/web/src/app/api/billing/renew/route.ts` has drifted from the excerpt above.
- Any existing test in `apps/web` intentionally asserts that anonymous callers can create renewal sessions without a billing identity.
- A step's verification fails twice.

## Maintenance notes

- If UVAI later wants unauthenticated users without a billing cookie to renew from `/pricing`, require `verifyTurnstileToken` on that branch rather than removing the `401` gate.
- Reviewer should verify `createProCheckoutSession` is unreachable when `resolveTrustedBillingEmail` returns `null`.
