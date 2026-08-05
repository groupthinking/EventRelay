import { describe, it, expect, afterEach, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from '@/app/api/billing/checkout/route';
import { getKaizenTraces, resetKaizenTracesForTests } from '@/lib/billing/kaizen-trace';

vi.mock('@/lib/billing/stripe-checkout', () => ({
  createProCheckoutSession: vi.fn().mockResolvedValue({
    sessionId: 'cs_test_123',
    url: 'https://checkout.stripe.com/c/pay/cs_test_123',
  }),
}));

vi.mock('@/lib/billing/turnstile', () => ({
  verifyTurnstileToken: vi.fn(),
}));

import { createProCheckoutSession } from '@/lib/billing/stripe-checkout';
import { verifyTurnstileToken } from '@/lib/billing/turnstile';

afterEach(() => {
  vi.restoreAllMocks();
  resetKaizenTracesForTests();
});

describe('POST /api/billing/checkout', () => {
  it('returns 403 when Turnstile verification fails', async () => {
    vi.mocked(verifyTurnstileToken).mockResolvedValue({ ok: false, error: 'turnstile_verification_failed' });
    const req = new NextRequest('http://localhost/api/billing/checkout', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ annual: false, turnstileToken: 'bad' }),
    });
    const res = await POST(req);
    expect(res.status).toBe(403);
    const body = await res.json();
    expect(body.error).toBe('turnstile_verification_failed');
    expect(createProCheckoutSession).not.toHaveBeenCalled();
  });

  it('creates Stripe session on valid Turnstile token', async () => {
    vi.mocked(verifyTurnstileToken).mockResolvedValue({ ok: true });
    const req = new NextRequest('http://localhost/api/billing/checkout', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ annual: true, turnstileToken: 'valid', email: 'pro@example.com' }),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.sessionId).toBe('cs_test_123');
    expect(createProCheckoutSession).toHaveBeenCalledWith({
      annual: true,
      customerEmail: 'pro@example.com',
      flow: 'acquisition',
    });
  });

  // This route is on PUBLIC_API_EXACT — unauthenticated, so any internet caller
  // can trigger this branch and read the response.
  it('never returns raw Stripe SDK error text', async () => {
    const stripeMessage =
      "No such price: 'price_1QLiveSecret'; Invalid API Key provided: sk_live_****ABCD";
    vi.mocked(verifyTurnstileToken).mockResolvedValue({ ok: true });
    vi.mocked(createProCheckoutSession).mockRejectedValue(new Error(stripeMessage));
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const req = new NextRequest('http://localhost/api/billing/checkout', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ annual: false, turnstileToken: 'valid' }),
    });
    const res = await POST(req);
    const raw = await res.text();

    expect(res.status).toBe(500);
    expect(JSON.parse(raw)).toEqual({ error: 'checkout_failed', code: 'checkout_failed' });
    for (const secret of ['price_1QLiveSecret', 'sk_live', 'No such price']) {
      expect(raw).not.toContain(secret);
    }

    // Raw detail is retained for operators only.
    expect(JSON.stringify(consoleError.mock.calls)).toContain('sk_live_****ABCD');
    expect(getKaizenTraces('billing').some((t) => t.observation === stripeMessage)).toBe(true);
  });
});
