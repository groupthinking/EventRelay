import { describe, it, expect, beforeEach } from 'vitest';
import type Stripe from 'stripe';
import {
  entitlementFromCheckoutSession,
  entitlementFromSubscription,
  activateFromCheckoutSession,
} from '../subscription-events';
import { getEntitlement, resetEntitlementStoreForTests } from '../entitlement-store';
import { resetKaizenTracesForTests } from '../kaizen-trace';

beforeEach(() => {
  resetEntitlementStoreForTests();
  resetKaizenTracesForTests();
});

describe('entitlementFromCheckoutSession', () => {
  it('maps paid Pro checkout to active entitlement', () => {
    const session = {
      payment_status: 'paid',
      status: 'complete',
      customer_details: { email: 'pro@example.com' },
      customer: 'cus_1',
      subscription: 'sub_1',
      metadata: { plan: 'pro', lead_model: 'grok-4-1-fast' },
    } as unknown as Stripe.Checkout.Session;
    const ent = entitlementFromCheckoutSession(session);
    expect(ent?.plan).toBe('pro');
    expect(ent?.status).toBe('active');
    expect(ent?.leadModel).toBe('grok-4-1-fast');
  });
});

describe('activateFromCheckoutSession', () => {
  it('persists Pro entitlement', async () => {
    const session = {
      payment_status: 'paid',
      status: 'complete',
      customer_email: 'buyer@example.com',
      metadata: { plan: 'pro' },
    } as unknown as Stripe.Checkout.Session;
    const saved = await activateFromCheckoutSession(session);
    expect(saved?.email).toBe('buyer@example.com');
    const loaded = await getEntitlement('buyer@example.com');
    expect(loaded?.plan).toBe('pro');
  });
});

describe('entitlementFromSubscription', () => {
  it('marks canceled subscription as free plan', () => {
    const sub = {
      id: 'sub_x',
      status: 'canceled',
      customer: 'cus_x',
      metadata: { plan: 'pro', email: 'old@example.com' },
    } as unknown as Stripe.Subscription;
    const ent = entitlementFromSubscription(sub);
    expect(ent?.plan).toBe('free');
    expect(ent?.status).toBe('canceled');
  });
});