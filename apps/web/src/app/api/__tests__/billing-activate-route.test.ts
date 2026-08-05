import { describe, it, expect, afterEach, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from '@/app/api/billing/activate/route';
import { getKaizenTraces, resetKaizenTracesForTests } from '@/lib/billing/kaizen-trace';

vi.mock('@/lib/billing/stripe-checkout', () => ({
  getCheckoutSession: vi.fn(),
}));

vi.mock('@/lib/billing/checkout-session-store', () => ({
  getCheckoutActivation: vi.fn().mockResolvedValue(null),
}));

vi.mock('@/lib/billing/subscription-events', () => ({
  activateFromCheckoutSession: vi.fn(),
}));

import { getCheckoutSession } from '@/lib/billing/stripe-checkout';

afterEach(() => {
  vi.restoreAllMocks();
  resetKaizenTracesForTests();
});

function activateRequest(sessionId: string) {
  return new NextRequest('http://localhost/api/billing/activate', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ sessionId }),
  });
}

// This route is on PUBLIC_API_EXACT — unauthenticated, so any internet caller
// can trigger the failure branch and read the response.
describe('POST /api/billing/activate error leakage', () => {
  it('never returns raw Stripe SDK error text', async () => {
    const stripeMessage =
      "No such checkout.session: 'cs_live_secret'; Invalid API Key provided: sk_live_****ABCD";
    vi.mocked(getCheckoutSession).mockRejectedValue(new Error(stripeMessage));
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const res = await POST(activateRequest('cs_live_secret'));
    const raw = await res.text();

    expect(res.status).toBe(500);
    expect(JSON.parse(raw)).toEqual({ error: 'activation_failed', code: 'activation_failed' });
    for (const token of ['sk_live', 'No such checkout.session', 'Invalid API Key']) {
      expect(raw).not.toContain(token);
    }

    // Raw detail is retained for operators only.
    expect(JSON.stringify(consoleError.mock.calls)).toContain('sk_live_****ABCD');
    expect(getKaizenTraces('billing').some((t) => t.observation === stripeMessage)).toBe(true);
  });

  it('rejects a malformed body without echoing parser internals', async () => {
    const req = new NextRequest('http://localhost/api/billing/activate', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{not json',
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: 'invalid_json' });
  });
});
