import { describe, it, expect, beforeEach } from 'vitest';
import {
  linkCheckoutActivation,
  getCheckoutActivation,
  resetCheckoutSessionStoreForTests,
} from '../checkout-session-store';
import type { EntitlementRecord } from '../entitlement-store';

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
    resetCheckoutSessionStoreForTests();
  });

  it('links and retrieves activation by session id', async () => {
    await linkCheckoutActivation('cs_test_link_1', record);
    const linked = await getCheckoutActivation('cs_test_link_1');
    expect(linked?.email).toBe('buyer@example.com');
    expect(linked?.plan).toBe('pro');
    expect(linked?.sessionId).toBe('cs_test_link_1');
  });
});