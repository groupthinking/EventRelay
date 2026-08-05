import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from '@/app/api/billing/webhook/route';
import { getKaizenTraces, resetKaizenTracesForTests } from '@/lib/billing/kaizen-trace';

const constructEvent = vi.fn();

vi.mock('@/lib/billing/stripe-checkout', () => ({
  getStripeClient: () => ({ webhooks: { constructEvent } }),
}));

vi.mock('@/lib/billing/subscription-events', () => ({
  activateFromCheckoutSession: vi.fn(),
  syncFromSubscription: vi.fn(),
}));

import { activateFromCheckoutSession } from '@/lib/billing/subscription-events';

const ORIGINAL_SECRET = process.env.STRIPE_WEBHOOK_SECRET;

beforeEach(() => {
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test';
});

afterEach(() => {
  if (ORIGINAL_SECRET === undefined) delete process.env.STRIPE_WEBHOOK_SECRET;
  else process.env.STRIPE_WEBHOOK_SECRET = ORIGINAL_SECRET;
  constructEvent.mockReset();
  vi.restoreAllMocks();
  resetKaizenTracesForTests();
});

function webhookRequest(body: string) {
  return new NextRequest('http://localhost/api/billing/webhook', {
    method: 'POST',
    headers: { 'stripe-signature': 't=1,v1=deadbeef' },
    body,
  });
}

// This route is on PUBLIC_API_EXACT — unauthenticated, so any internet caller
// can trigger both failure branches and read the response.
describe('POST /api/billing/webhook error leakage', () => {
  it('never returns signature-verification internals', async () => {
    const stripeMessage =
      'No signatures found matching the expected signature for payload (tolerance 300s, scheme v1, key sk_live_****ABCD)';
    constructEvent.mockImplementation(() => {
      throw new Error(stripeMessage);
    });
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const res = await POST(webhookRequest('{"id":"evt_1"}'));
    const raw = await res.text();

    expect(res.status).toBe(400);
    expect(JSON.parse(raw)).toEqual({ error: 'invalid_payload', code: 'invalid_payload' });
    for (const token of ['sk_live', 'tolerance', 'scheme v1', 'No signatures found']) {
      expect(raw).not.toContain(token);
    }

    // Raw detail is retained for operators only.
    expect(JSON.stringify(consoleError.mock.calls)).toContain('sk_live_****ABCD');
    expect(getKaizenTraces('billing').some((t) => t.observation === stripeMessage)).toBe(true);
  });

  it('never returns handler internals', async () => {
    const handlerMessage = 'Redis connection refused at 10.0.3.14:6379 for customer cus_live_secret';
    constructEvent.mockReturnValue({
      type: 'checkout.session.completed',
      data: { object: { id: 'cs_test_1' } },
    });
    vi.mocked(activateFromCheckoutSession).mockRejectedValue(new Error(handlerMessage));
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const res = await POST(webhookRequest('{"id":"evt_2"}'));
    const raw = await res.text();

    expect(res.status).toBe(500);
    expect(JSON.parse(raw)).toEqual({
      error: 'webhook_handler_failed',
      code: 'webhook_handler_failed',
    });
    for (const token of ['10.0.3.14', 'cus_live_secret', 'Redis connection refused']) {
      expect(raw).not.toContain(token);
    }

    expect(JSON.stringify(consoleError.mock.calls)).toContain('10.0.3.14:6379');
    expect(getKaizenTraces('billing').some((t) => t.observation === handlerMessage)).toBe(true);
  });
});
