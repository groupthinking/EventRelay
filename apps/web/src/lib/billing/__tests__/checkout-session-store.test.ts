import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  CHECKOUT_ACTIVATION_TTL_SECONDS,
  linkCheckoutActivation,
  getCheckoutActivation,
  resetCheckoutSessionStoreForTests,
} from '../checkout-session-store';
import type { EntitlementRecord } from '../entitlement-store';

const redisMocks = vi.hoisted(() => ({
  enabled: false,
  set: vi.fn(async () => 'OK'),
  get: vi.fn(async () => null as unknown),
}));

vi.mock('../upstash-client', () => ({
  createUpstashRedisClient: async () =>
    redisMocks.enabled
      ? {
          set: redisMocks.set,
          get: redisMocks.get,
        }
      : null,
}));

const record: EntitlementRecord = {
  email: 'buyer@example.com',
  plan: 'pro',
  status: 'active',
  stripeCustomerId: 'cus_1',
  stripeSubscriptionId: 'sub_1',
  leadModel: 'grok-4-1-fast',
  updatedAt: new Date().toISOString(),
};

describe('checkout session store', () => {
  beforeEach(() => {
    redisMocks.enabled = false;
    vi.clearAllMocks();
    resetCheckoutSessionStoreForTests();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('links and retrieves activation by session id', async () => {
    await linkCheckoutActivation('cs_test_link_1', record);
    const linked = await getCheckoutActivation('cs_test_link_1');
    expect(linked?.email).toBe('buyer@example.com');
    expect(linked?.plan).toBe('pro');
    expect(linked?.sessionId).toBe('cs_test_link_1');
  });

  it('persists activation link in Redis with a 24-hour TTL', async () => {
    redisMocks.enabled = true;
    const linked = await linkCheckoutActivation('cs_test_ttl_1', record);
    expect(redisMocks.set).toHaveBeenCalledWith(
      'er:checkout:cs_test_ttl_1',
      linked,
      { ex: 86400 },
    );
  });

  it('returns null when fulfilledAt exceeds 24-hour TTL', async () => {
    vi.useFakeTimers();
    const start = new Date('2026-11-19T00:00:00.000Z');
    vi.setSystemTime(start);

    await linkCheckoutActivation('cs_test_expired_1', record);
    expect(await getCheckoutActivation('cs_test_expired_1')).not.toBeNull();

    vi.setSystemTime(
      new Date(start.getTime() + CHECKOUT_ACTIVATION_TTL_SECONDS * 1000 + 1),
    );
    expect(await getCheckoutActivation('cs_test_expired_1')).toBeNull();
  });

  it('returns null when Redis returns an entry whose fulfilledAt exceeds 24-hour TTL', async () => {
    redisMocks.enabled = true;
    redisMocks.get.mockResolvedValueOnce({
      sessionId: 'cs_test_redis_expired',
      email: 'buyer@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      fulfilledAt: new Date(
        Date.now() - (CHECKOUT_ACTIVATION_TTL_SECONDS * 1000 + 1000),
      ).toISOString(),
    });

    expect(await getCheckoutActivation('cs_test_redis_expired')).toBeNull();
  });
});