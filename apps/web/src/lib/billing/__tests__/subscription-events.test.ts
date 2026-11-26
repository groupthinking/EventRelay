import { describe, it, expect, beforeEach, vi } from 'vitest';
import type Stripe from 'stripe';
import {
  entitlementFromCheckoutSession,
  entitlementFromSubscription,
  activateFromCheckoutSession,
  syncFromSubscription,
} from '../subscription-events';
import { getEntitlement, resetEntitlementStoreForTests } from '../entitlement-store';
import { resetKaizenTracesForTests } from '../kaizen-trace';

const stripeMock = vi.hoisted(() => ({
  customersRetrieve: vi.fn(),
}));

vi.mock('../stripe-checkout', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../stripe-checkout')>();
  return {
    ...actual,
    getStripeClient: () => ({
      customers: {
        retrieve: stripeMock.customersRetrieve,
      },
    }),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
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

describe('syncFromSubscription', () => {
  it('resolves customer email via Stripe when customer is a string ID without metadata.email', async () => {
    stripeMock.customersRetrieve.mockResolvedValue({
      id: 'cus_123',
      email: 'canceled@example.com',
    });

    const sub = {
      id: 'sub_123',
      status: 'canceled',
      customer: 'cus_123',
      metadata: { plan: 'pro' },
    } as unknown as Stripe.Subscription;

    const synced = await syncFromSubscription(sub);
    expect(stripeMock.customersRetrieve).toHaveBeenCalledWith('cus_123');
    expect(synced?.email).toBe('canceled@example.com');
    expect(synced?.plan).toBe('free');
    expect(synced?.status).toBe('canceled');

    const loaded = await getEntitlement('canceled@example.com');
    expect(loaded?.plan).toBe('free');
    expect(loaded?.status).toBe('canceled');
  });
});