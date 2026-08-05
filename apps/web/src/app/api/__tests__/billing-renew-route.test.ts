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

  // This route is on PUBLIC_API_EXACT — unauthenticated, so any internet caller
  // can trigger this branch and read the response.
  it('never returns raw Stripe SDK error text', async () => {
    const stripeMessage = "Invalid API Key provided: sk_live_****ABCD (account acct_1QLive)";
    vi.mocked(createProCheckoutSession).mockRejectedValue(new Error(stripeMessage));
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const req = new NextRequest('http://localhost/api/billing/renew', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ annual: false }),
    });
    const res = await POST(req);
    const raw = await res.text();

    expect(res.status).toBe(500);
    expect(JSON.parse(raw)).toEqual({ error: 'renewal_failed', code: 'renewal_failed' });
    for (const token of ['sk_live', 'acct_1QLive', 'Invalid API Key']) {
      expect(raw).not.toContain(token);
    }

    // Raw detail is retained for operators only.
    expect(JSON.stringify(consoleError.mock.calls)).toContain('sk_live_****ABCD');
    expect(getKaizenTraces('billing').some((t) => t.observation === stripeMessage)).toBe(true);
  });
});
