import { describe, it, expect, beforeEach } from 'vitest';
import type Stripe from 'stripe';
import {
  entitlementFromCheckoutSession,
  activateFromCheckoutSession,
} from '../subscription-events';
import { getEntitlement, resetEntitlementStoreForTests } from '../entitlement-store';
import { getCheckoutActivation, resetCheckoutSessionStoreForTests } from '../checkout-session-store';
import { resetKaizenTracesForTests } from '../kaizen-trace';

/**
 * Spine integration: paid checkout.session.completed object activates Pro
 * without email/subscription lookup fallbacks.
 */
describe('billing spine integration', () => {
  beforeEach(() => {
    resetEntitlementStoreForTests();
    resetCheckoutSessionStoreForTests();
    resetKaizenTracesForTests();
  });

  it('activates Pro from a paid checkout session fixture', async () => {
    const paidSession = {
      id: 'cs_test_spine_paid',
      object: 'checkout.session',
      payment_status: 'paid',
      status: 'complete',
      customer_details: { email: 'spine-paid@example.com' },
      customer: 'cus_spine_1',
      subscription: 'sub_spine_1',
      metadata: { plan: 'pro', flow: 'acquisition', lead_model: 'grok-4-1-fast' },
    } as unknown as Stripe.Checkout.Session;

    const mapped = entitlementFromCheckoutSession(paidSession);
    expect(mapped?.plan).toBe('pro');
    expect(mapped?.status).toBe('active');

    const saved = await activateFromCheckoutSession(paidSession);
    expect(saved?.plan).toBe('pro');
    expect(saved?.stripeCustomerId).toBe('cus_spine_1');
    expect(saved?.stripeSubscriptionId).toBe('sub_spine_1');

    const loaded = await getEntitlement('spine-paid@example.com');
    expect(loaded?.plan).toBe('pro');
    expect(loaded?.status).toBe('active');

    const linked = await getCheckoutActivation('cs_test_spine_paid');
    expect(linked?.email).toBe('spine-paid@example.com');
    expect(linked?.plan).toBe('pro');
  });

  it('does not activate Pro from an unpaid checkout session fixture', async () => {
    const unpaidSession = {
      id: 'cs_test_spine_unpaid',
      payment_status: 'unpaid',
      status: 'open',
      customer_email: 'spine-unpaid@example.com',
      metadata: { plan: 'pro' },
    } as unknown as Stripe.Checkout.Session;

    const saved = await activateFromCheckoutSession(unpaidSession);
    expect(saved).toBeNull();
    expect(await getEntitlement('spine-unpaid@example.com')).toBeNull();
  });
});