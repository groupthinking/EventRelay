import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from '@/app/api/billing/renew/route';
import { getKaizenTraces, resetKaizenTracesForTests } from '@/lib/billing/kaizen-trace';
import { saveEntitlement, resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { signBillingEmail } from '@/lib/billing/billing-cookie';

vi.mock('@/lib/billing/stripe-checkout', () => ({
  createProCheckoutSession: vi.fn().mockResolvedValue({
    sessionId: 'cs_renew_456',
    url: 'https://checkout.stripe.com/c/pay/cs_renew_456',
  }),
}));

import { createProCheckoutSession } from '@/lib/billing/stripe-checkout';

beforeEach(() => {
  resetEntitlementStoreForTests();
});

afterEach(() => {
  vi.restoreAllMocks();
  resetKaizenTracesForTests();
});

describe('POST /api/billing/renew', () => {
  it('creates renewal checkout from trusted cookie and stored stripe customer', async () => {
    await saveEntitlement({
      email: 'returning@example.com',
      plan: 'pro',
      status: 'active',
      stripeCustomerId: 'cus_stored',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });

    const req = new NextRequest('http://localhost/api/billing/renew', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        cookie: `er_billing_email=${encodeURIComponent(signBillingEmail('returning@example.com') as string)}`,
      },
      body: JSON.stringify({ annual: false }),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.sessionId).toBe('cs_renew_456');
    expect(createProCheckoutSession).toHaveBeenCalledWith({
      annual: false,
      customerEmail: 'returning@example.com',
      customerId: 'cus_stored',
      flow: 'renewal',
    });
    const traces = getKaizenTraces('billing');
    expect(traces.some((t) => t.stage === 'renewal_start')).toBe(true);
    expect(traces.some((t) => t.stage === 'renewal_session')).toBe(true);
  });
});
