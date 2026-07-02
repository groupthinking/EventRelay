import { describe, it, expect, beforeEach, vi } from 'vitest';
import { saveEntitlement, resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { signBillingEmail } from '@/lib/billing/billing-cookie';
import { resetChatQuotaForTests } from '@/lib/billing/chat-quota';
import { resetKaizenTracesForTests, getKaizenTraces } from '@/lib/billing/kaizen-trace';

vi.mock('@/lib/billing/grok-client', () => ({
  grokChatCompletion: vi.fn().mockResolvedValue({
    answer: 'pro reply',
    model: 'grok-4-1-fast',
    provider: 'xai',
  }),
}));

import { POST } from '@/app/api/chat/route';

function cookieReq(email: string, query: string) {
  return new Request('http://localhost/api/chat', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      cookie: `er_billing_email=${encodeURIComponent(signBillingEmail(email) as string)}`,
    },
    body: JSON.stringify({ query }),
  });
}

beforeEach(() => {
  resetEntitlementStoreForTests();
  resetChatQuotaForTests();
  resetKaizenTracesForTests();
});

describe('POST /api/chat billing gating', () => {
  it('blocks free tier after daily quota', async () => {
    const email = 'free@example.com';
    for (let i = 0; i < 5; i++) {
      const res = await POST(cookieReq(email, `msg ${i}`));
      expect(res.status).not.toBe(402);
    }
    const blocked = await POST(cookieReq(email, 'one too many'));
    expect(blocked.status).toBe(402);
    const body = await blocked.json();
    expect(body.upgradeRequired).toBe(true);
  });

  it('routes Pro users to grok-composer model path', async () => {
    await saveEntitlement({
      email: 'pro@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });
    const res = await POST(cookieReq('pro@example.com', 'hello'));
    const body = await res.json();
    expect(body.routing.runtime).toBe('grok-composer');
    expect(body.plan).toBe('pro');
    expect(body.provider).toBe('xai');
    const traces = getKaizenTraces('billing');
    expect(traces.some((t) => t.stage === 'chat_routed')).toBe(true);
  });
});
