import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from '@/app/api/billing/activate/route';
import { getKaizenTraces, resetKaizenTracesForTests } from '@/lib/billing/kaizen-trace';
import { getEntitlement, saveEntitlement, resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';

const realActivate = vi.hoisted(() => ({
  fn: null as null | typeof import('@/lib/billing/subscription-events').activateFromCheckoutSession,
}));

vi.mock('@/lib/billing/stripe-checkout', () => ({
  getCheckoutSession: vi.fn(),
}));

vi.mock('@/lib/billing/checkout-session-store', () => ({
  CHECKOUT_ACTIVATION_TTL_SECONDS: 60 * 60 * 24,
  getCheckoutActivation: vi.fn().mockResolvedValue(null),
  linkCheckoutActivation: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('@/lib/billing/subscription-events', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/billing/subscription-events')>();
  realActivate.fn = actual.activateFromCheckoutSession;
  return {
    activateFromCheckoutSession: vi.fn(actual.activateFromCheckoutSession),
  };
});

import { getCheckoutSession } from '@/lib/billing/stripe-checkout';
import { activateFromCheckoutSession } from '@/lib/billing/subscription-events';

beforeEach(() => {
  resetEntitlementStoreForTests();
  const real = realActivate.fn;
  if (!real) {
    throw new Error('activateFromCheckoutSession real implementation missing');
  }
  vi.mocked(activateFromCheckoutSession).mockReset();
  vi.mocked(activateFromCheckoutSession).mockImplementation(real);
});

afterEach(() => {
  vi.restoreAllMocks();
  resetKaizenTracesForTests();
});

function activateRequest(sessionId: string): NextRequest {
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
    expect(await res.json()).toEqual({ error: 'invalid_json', code: 'invalid_json' });
  });
});

// Every error branch must carry a stable machine-readable `code`, not only the
// two that were sanitized for CWE-209 — otherwise a client cannot branch on the
// contract this route declares.
describe('POST /api/billing/activate error-code contract', () => {
  it('returns session_id_required with a matching code', async () => {
    const res = await POST(activateRequest('   '));

    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({
      error: 'session_id_required',
      code: 'session_id_required',
    });
  });

  it('returns not_eligible with a matching code', async () => {
    vi.mocked(getCheckoutSession).mockResolvedValue({ id: 'cs_free' } as never);
    vi.mocked(activateFromCheckoutSession).mockResolvedValue(null);
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const res = await POST(activateRequest('cs_free'));

    expect(res.status).toBe(402);
    expect(await res.json()).toEqual({
      error: 'not_eligible',
      code: 'not_eligible',
      sessionId: 'cs_free',
    });
  });

  it('rejects post-TTL stale checkout sessions without calling activateFromCheckoutSession', async () => {
    const expiredCreatedSec = Math.floor((Date.now() - 60 * 60 * 25 * 1000) / 1000);
    vi.mocked(getCheckoutSession).mockResolvedValue({
      id: 'cs_stale_25h',
      created: expiredCreatedSec,
      payment_status: 'paid',
      status: 'complete',
      customer_details: { email: 'stale@example.com' },
      metadata: { plan: 'pro' },
    } as never);
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const res = await POST(activateRequest('cs_stale_25h'));

    expect(res.status).toBe(402);
    expect(await res.json()).toEqual({
      error: 'not_eligible',
      code: 'not_eligible',
      sessionId: 'cs_stale_25h',
    });
    expect(activateFromCheckoutSession).not.toHaveBeenCalled();
  });

  it('blocks replay on fallback when the live entitlement is already downgraded to free', async () => {
    await saveEntitlement({
      email: 'canceled@example.com',
      plan: 'free',
      status: 'canceled',
      stripeCustomerId: 'cus_canceled',
      stripeSubscriptionId: 'sub_canceled',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });

    vi.mocked(getCheckoutSession).mockResolvedValue({
      id: 'cs_replay_after_cancel',
      created: Math.floor(Date.now() / 1000),
      payment_status: 'paid',
      status: 'complete',
      customer_details: { email: 'canceled@example.com' },
      metadata: { plan: 'pro' },
      subscription: 'sub_canceled',
    } as never);
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const res = await POST(activateRequest('cs_replay_after_cancel'));

    expect(res.status).toBe(402);
    expect(await res.json()).toEqual({
      error: 'not_eligible',
      code: 'not_eligible',
      sessionId: 'cs_replay_after_cancel',
    });
    expect(activateFromCheckoutSession).toHaveBeenCalled();
    const stored = await getEntitlement('canceled@example.com');
    expect(stored?.plan).toBe('free');
    expect(stored?.stripeSubscriptionId).toBe('sub_canceled');
  });

  it('activates pro when a canceled user buys a new subscription', async () => {
    await saveEntitlement({
      email: 'returning@example.com',
      plan: 'free',
      status: 'canceled',
      stripeCustomerId: 'cus_returning',
      stripeSubscriptionId: 'sub_canceled',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });

    vi.mocked(getCheckoutSession).mockResolvedValue({
      id: 'cs_new_after_cancel',
      created: Math.floor(Date.now() / 1000),
      payment_status: 'paid',
      status: 'complete',
      customer_details: { email: 'returning@example.com' },
      metadata: { plan: 'pro' },
      subscription: 'sub_new',
    } as never);
    vi.spyOn(console, 'info').mockImplementation(() => {});

    const res = await POST(activateRequest('cs_new_after_cancel'));

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.plan).toBe('pro');
    expect(body.status).toBe('active');
    expect(body.email).toBe('returning@example.com');
    expect(activateFromCheckoutSession).toHaveBeenCalled();
    const stored = await getEntitlement('returning@example.com');
    expect(stored?.plan).toBe('pro');
    expect(stored?.stripeSubscriptionId).toBe('sub_new');
  });
});
