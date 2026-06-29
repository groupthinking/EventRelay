import { describe, it, expect, afterEach, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from '@/app/api/billing/checkout/route';
import { resetKaizenTracesForTests } from '@/lib/billing/kaizen-trace';

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
});
