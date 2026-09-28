import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { NextRequest } from 'next/server';
import { GET } from '@/app/api/billing/status/route';
import { signBillingEmail } from '@/lib/billing/billing-cookie';
import {
  resetEntitlementStoreForTests,
  saveEntitlement,
} from '@/lib/billing/entitlement-store';

const original = process.env.TEMP_PAYWALL_OFF;

function statusReq(email?: string): NextRequest {
  const headers = new Headers();
  if (email) {
    const signed = signBillingEmail(email);
    headers.set(
      'cookie',
      `er_billing_email=${encodeURIComponent(signed as string)}`,
    );
  }
  return new NextRequest('http://localhost/api/billing/status', { headers });
}

beforeEach(() => {
  resetEntitlementStoreForTests();
  delete process.env.TEMP_PAYWALL_OFF;
});

afterEach(() => {
  if (original === undefined) {
    delete process.env.TEMP_PAYWALL_OFF;
  } else {
    process.env.TEMP_PAYWALL_OFF = original;
  }
});

describe('GET /api/billing/status temporary paywall bypass', () => {
  it('reports plan pro and unlimited chat for a signed-in free session', async () => {
    const res = await GET(statusReq('dogfood@example.com'));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.plan).toBe('pro');
    expect(body.status).toBe('active');
    expect(body.paywallBypass).toBe(true);
    expect(body.features.unlimitedChat).toBe(true);
    expect(body.features.chatDailyLimit).toBeNull();
    expect(body.features.agentDispatch).toBe(false);
    expect(body.routing.plan).toBe('pro');
    expect(body.routing.runtime).toBe('grok-composer');
    expect(body.stripeCustomerId).toBeNull();
    expect(body.stripeSubscriptionId).toBeNull();
  });

  it('leaves anonymous sessions on the free plan', async () => {
    const res = await GET(statusReq());
    const body = await res.json();

    expect(body.plan).toBe('free');
    expect(body.paywallBypass).toBe(false);
    expect(body.features.unlimitedChat).toBe(false);
    expect(body.email).toBeNull();
  });

  it('keeps a real Pro entitlement and does not mark the bypass', async () => {
    await saveEntitlement({
      email: 'paying@example.com',
      plan: 'pro',
      status: 'active',
      stripeCustomerId: 'cus_real',
      stripeSubscriptionId: 'sub_real',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });

    const res = await GET(statusReq('paying@example.com'));
    const body = await res.json();

    expect(body.plan).toBe('pro');
    expect(body.paywallBypass).toBe(false);
    expect(body.features.agentDispatch).toBe(true);
    expect(body.stripeCustomerId).toBe('cus_real');
  });

  it('reports free again when TEMP_PAYWALL_OFF=0', async () => {
    process.env.TEMP_PAYWALL_OFF = '0';
    const res = await GET(statusReq('dogfood@example.com'));
    const body = await res.json();

    expect(body.plan).toBe('free');
    expect(body.status).toBe('inactive');
    expect(body.paywallBypass).toBe(false);
    expect(body.features.unlimitedChat).toBe(false);
    expect(body.routing.plan).toBe('free');
  });
});
