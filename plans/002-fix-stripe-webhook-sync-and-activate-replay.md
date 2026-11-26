# Plan 002: Resolve customer email on Stripe subscription webhooks and verify live entitlement on `/api/billing/activate`

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 25c5e936e..HEAD -- apps/web/src/lib/billing/subscription-events.ts apps/web/src/lib/billing/checkout-session-store.ts apps/web/src/app/api/billing/activate/route.ts`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `25c5e936e` (`origin/main`), 2026-11-19

## Why this matters

When Stripe sends `customer.subscription.updated` or `customer.subscription.deleted`, `sub.customer` is a string customer ID (`cus_...`) rather than an expanded `Stripe.Customer` object, and `sub.metadata.email` is never set at checkout. Consequently, `entitlementFromSubscription(sub)` returns `null`, `syncFromSubscription(sub)` silently no-ops while returning HTTP `200 { received: true }`, and canceled/unpaid Pro subscriptions are never downgraded. In addition, `checkout-session-store` persists `er:checkout:<sessionId>` with no TTL, and `/api/billing/activate` trusts that cached link without re-checking the live entitlement record—allowing replay of an old `sessionId` to re-mint a 1-year Pro cookie after cancellation.

## Current state

- `apps/web/src/lib/billing/subscription-events.ts` — maps Stripe Checkout sessions and subscriptions to `EntitlementRecord` and persists via `saveEntitlement`.
- `apps/web/src/lib/billing/checkout-session-store.ts` — caches `CheckoutActivationLink` in Upstash Redis + in-memory `Map` with no TTL.
- `apps/web/src/app/api/billing/activate/route.ts` — exchanges a `sessionId` for a signed `er_billing_email` cookie.

Excerpt of `apps/web/src/lib/billing/subscription-events.ts:42-52, 116-127` at `25c5e936e`:

```ts
export function entitlementFromSubscription(
  sub: Stripe.Subscription,
  email?: string,
): EntitlementRecord | null {
  const resolvedEmail =
    email ??
    sub.metadata?.email ??
    (typeof sub.customer === 'object' && sub.customer && 'email' in sub.customer
      ? (sub.customer as Stripe.Customer).email
      : undefined);
  if (!resolvedEmail) return null;
...
export async function syncFromSubscription(
  sub: Stripe.Subscription,
  email?: string,
): Promise<EntitlementRecord | null> {
  const record = entitlementFromSubscription(sub, email);
  if (!record) return null;
  const saved = await saveEntitlement(record);
```

Excerpt of `apps/web/src/app/api/billing/activate/route.ts:40-52` at `25c5e936e`:

```ts
    let entitlement: EntitlementRecord | null = null;
    const linked = await getCheckoutActivation(sessionId);

    if (linked?.plan === 'pro' && (linked.status === 'active' || linked.status === 'trialing')) {
      entitlement = entitlementFromLink(linked);
      kaizenObserve('billing', 'activate_session_link', `Activated via checkout link ${sessionId}`, {
        decision: `email=${linked.email}`,
      });
    } else {
      const session = await getCheckoutSession(sessionId);
      entitlement = await activateFromCheckoutSession(session);
    }
```

## Commands you will need

| Purpose   | Command                                                                  | Expected on success |
|-----------|--------------------------------------------------------------------------|---------------------|
| Typecheck | `cd apps/web && npx tsc --noEmit`                                        | exit 0, no errors   |
| Billing   | `cd apps/web && npx vitest run src/lib/billing/__tests__/`               | all tests pass      |
| Full web  | `cd apps/web && npx vitest run`                                          | all tests pass      |

## Scope

**In scope** (the only files you should modify):
- `apps/web/src/lib/billing/subscription-events.ts`
- `apps/web/src/lib/billing/checkout-session-store.ts`
- `apps/web/src/app/api/billing/activate/route.ts`
- `apps/web/src/lib/billing/__tests__/subscription-events.test.ts`
- `apps/web/src/lib/billing/__tests__/checkout-session-store.test.ts`

**Out of scope** (do NOT touch):
- `apps/web/src/app/api/billing/webhook/route.ts` — signature verification and switch dispatch are already correct once `syncFromSubscription` resolves string customer IDs.
- `apps/web/src/lib/billing/stripe-checkout.ts` — keep checkout session creation unchanged unless adding `email` metadata is needed later.

## Git workflow

- Branch from `origin/main`: `fix/billing-webhook-sync-and-activate-ttl`
- Conventional Commits message: `fix(billing): resolve Stripe customer email on subscription sync and verify live entitlement`
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Resolve string `sub.customer` IDs in `syncFromSubscription`

In `apps/web/src/lib/billing/subscription-events.ts`, update `syncFromSubscription(sub, email?)`:
- Compute `let resolvedEmail = email ?? sub.metadata?.email ?? (typeof sub.customer === 'object' && sub.customer && 'email' in sub.customer ? (sub.customer as Stripe.Customer).email ?? undefined : undefined);`
- If `!resolvedEmail && typeof sub.customer === 'string' && sub.customer.trim()`:
  - Retrieve customer via `const stripe = getStripeClient(); const customer = await stripe.customers.retrieve(sub.customer);`
  - If `customer && !('deleted' in customer && customer.deleted) && customer.email`, set `resolvedEmail = customer.email`.
- Pass `resolvedEmail` to `entitlementFromSubscription(sub, resolvedEmail)`.

**Verify**: `cd apps/web && npx vitest run src/lib/billing/__tests__/subscription-events.test.ts` → passes.

### Step 2: Add a 24-hour TTL to `checkout-session-store.ts`

In `apps/web/src/lib/billing/checkout-session-store.ts`:
- Define `export const CHECKOUT_ACTIVATION_TTL_SECONDS = 60 * 60 * 24;` (24 hours).
- Pass `{ ex: CHECKOUT_ACTIVATION_TTL_SECONDS }` to `redis.set(sessionKey(link.sessionId), link, { ex: CHECKOUT_ACTIVATION_TTL_SECONDS })`.
- On `getCheckoutActivation`, if `Date.now() - Date.parse(raw.fulfilledAt) > CHECKOUT_ACTIVATION_TTL_SECONDS * 1000`, delete from `memoryLinks` and return `null`.

**Verify**: `cd apps/web && npx vitest run src/lib/billing/__tests__/checkout-session-store.test.ts` → passes.

### Step 3: Re-verify live entitlement in `/api/billing/activate`

In `apps/web/src/app/api/billing/activate/route.ts`:
- Import `getEntitlement` from `@/lib/billing/entitlement-store`.
- When `linked` is found and `linked.plan === 'pro'`:
  - Check `const current = await getEntitlement(linked.email);`
  - If `current` exists and `current.plan !== 'pro'` (e.g., downgraded by webhook to `'free'` / `'canceled'`), do NOT activate from `linked` — set `entitlement = current` (which will fall into the `402 not_eligible` response!).
  - Otherwise use `current ?? entitlementFromLink(linked)`.

**Verify**: `cd apps/web && npx tsc --noEmit && npx vitest run src/lib/billing/__tests__/` → exit 0, all pass.

## Test plan

- Add test in `apps/web/src/lib/billing/__tests__/subscription-events.test.ts`:
  - `customer.subscription.deleted` with string `customer: 'cus_123'` and no `metadata.email` calls `stripe.customers.retrieve('cus_123')` and saves `{ plan: 'free', status: 'canceled' }`.
- Add test in `apps/web/src/lib/billing/__tests__/checkout-session-store.test.ts`:
  - `linkCheckoutActivation` passes `{ ex: 86400 }` to Redis; expired `fulfilledAt` entries return `null`.
- Verification: `cd apps/web && npx vitest run` → all pass.

## Done criteria

- [ ] `cd apps/web && npx tsc --noEmit` exits 0
- [ ] `cd apps/web && npx vitest run src/lib/billing/__tests__/` passes with new webhook downgrade and TTL tests
- [ ] `cd apps/web && npx vitest run` exits 0
- [ ] Only in-scope files modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `redis.set` wrapper in `apps/web/src/lib/billing/upstash-client.ts` does not accept an `{ ex }` options parameter.
- Any file in scope has drifted from `25c5e936e`.
- Verification fails twice after a reasonable fix attempt.

## Maintenance notes

- If Stripe customer lookup latency becomes hot on high-volume webhook traffic, add a secondary `er:customer:<cus_id> -> email` index in `entitlement-store.ts` as a follow-up.
- Reviewer should confirm a canceled subscription cannot be reactivated by replaying an old `sessionId` against `POST /api/billing/activate`.
