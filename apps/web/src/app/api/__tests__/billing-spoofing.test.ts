import { describe, it, expect, beforeEach, vi } from 'vitest';
import { saveEntitlement, resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { resetChatQuotaForTests } from '@/lib/billing/chat-quota';

vi.mock('@/lib/billing/grok-client', () => ({
  grokChatCompletion: vi.fn().mockResolvedValue({
    answer: 'grok ok',
    model: 'grok-4-1-fast',
    provider: 'xai',
  }),
}));

import { POST as chatPOST } from '@/app/api/chat/route';

beforeEach(() => {
  resetEntitlementStoreForTests();
  resetChatQuotaForTests();
});

describe('billing identity spoofing', () => {
  it('does not grant Pro chat when body supplies a pro email without cookie', async () => {
    await saveEntitlement({
      email: 'real-pro@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });

    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query: 'hi', billing_email: 'real-pro@example.com' }),
    });
    const res = await chatPOST(req);
    const body = await res.json();
    expect(body.plan).toBe('free');
    expect(body.routing?.runtime).toBe('standard');
  });

  it('grants Pro only with trusted billing cookie', async () => {
    await saveEntitlement({
      email: 'cookie-pro@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });

    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        cookie: 'er_billing_email=cookie-pro@example.com',
      },
      body: JSON.stringify({ query: 'hi' }),
    });

    const res = await chatPOST(req);
    const body = await res.json();
    expect(body.plan).toBe('pro');
    expect(body.routing?.runtime).toBe('grok-composer');
    expect(body.provider).toBe('xai');
  });
});