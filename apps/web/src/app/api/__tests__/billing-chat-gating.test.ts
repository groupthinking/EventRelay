import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { saveEntitlement, resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { signBillingEmail } from '@/lib/billing/billing-cookie';
import { resetChatQuotaForTests } from '@/lib/billing/chat-quota';
import { resetKaizenTracesForTests, getKaizenTraces } from '@/lib/billing/kaizen-trace';

// The free-tier path terminates in `generateText` against the Vercel AI Gateway.
// Stub that boundary so assertions describe billing behaviour rather than the
// developer's ambient credentials, and so the suite never leaves the process.
const { generateText, aiGateway } = vi.hoisted(() => ({
  generateText: vi.fn(async () => ({ text: 'free reply' })),
  aiGateway: vi.fn((model: string) => model),
}));

vi.mock('ai', () => ({
  generateText,
}));

vi.mock('@/lib/ai-gateway', () => ({
  aiGateway,
  GATEWAY_CHAT_MODEL: 'openai/gpt-4o',
}));

vi.mock('@/lib/billing/grok-client', () => ({
  grokChatCompletion: vi.fn().mockResolvedValue({
    answer: 'pro reply',
    model: 'grok-4-1-fast',
    provider: 'xai',
  }),
}));

import { POST } from '@/app/api/chat/route';

const GATEWAY_ENV_KEYS = [
  'AI_GATEWAY_API_KEY',
  'VERCEL_AI_GATEWAY_API_KEY',
  'VERCEL_API_KEY',
] as const;

type GatewayEnvKey = (typeof GATEWAY_ENV_KEYS)[number];

const savedGatewayEnv: Partial<Record<GatewayEnvKey, string | undefined>> = {};

/**
 * Pin the gateway credentials the route reads at request time. Without this the
 * free-tier assertions are decided by whatever happens to be in the shell: with
 * no key the route short-circuits to 503 and every `not.toBe(402)` assertion
 * passes for the wrong reason.
 */
function setGatewayEnv(configured: boolean) {
  for (const key of GATEWAY_ENV_KEYS) {
    delete process.env[key];
  }
  if (configured) {
    process.env.AI_GATEWAY_API_KEY = 'test-gateway-key';
  }
}

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
  generateText.mockClear();
  aiGateway.mockClear();

  for (const key of GATEWAY_ENV_KEYS) {
    savedGatewayEnv[key] = process.env[key];
  }
  setGatewayEnv(true);
});

afterEach(() => {
  for (const key of GATEWAY_ENV_KEYS) {
    const original = savedGatewayEnv[key];
    if (original === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = original;
    }
  }
});

describe('POST /api/chat billing gating', () => {
  it('serves free tier up to the daily quota, then blocks with 402', async () => {
    const email = 'free@example.com';

    for (let i = 0; i < 5; i++) {
      const res = await POST(cookieReq(email, `msg ${i}`));
      // Asserting the exact success status: `not.toBe(402)` was also satisfied
      // by a 503 "gateway not configured", which made this test vacuous.
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.answer).toBe('free reply');
      expect(body.plan).toBe('free');
    }
    expect(generateText).toHaveBeenCalledTimes(5);

    const blocked = await POST(cookieReq(email, 'one too many'));
    expect(blocked.status).toBe(402);
    const body = await blocked.json();
    expect(body.upgradeRequired).toBe(true);
    // The quota rejection must short-circuit before any model call.
    expect(generateText).toHaveBeenCalledTimes(5);
  });

  it('still enforces the quota when no AI gateway key is configured', async () => {
    setGatewayEnv(false);
    const email = 'free-no-gateway@example.com';

    for (let i = 0; i < 5; i++) {
      const res = await POST(cookieReq(email, `msg ${i}`));
      // Allowed by billing, then failing on configuration — a materially
      // different outcome from the 402 this suite is meant to detect.
      expect(res.status).toBe(503);
    }
    expect(generateText).not.toHaveBeenCalled();

    const blocked = await POST(cookieReq(email, 'one too many'));
    expect(blocked.status).toBe(402);
  });

  it('meters quota per billing subject', async () => {
    for (let i = 0; i < 5; i++) {
      expect((await POST(cookieReq('a@example.com', `msg ${i}`))).status).toBe(200);
    }
    expect((await POST(cookieReq('a@example.com', 'blocked'))).status).toBe(402);
    // A different subject starts with a fresh allowance.
    expect((await POST(cookieReq('b@example.com', 'hello'))).status).toBe(200);
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
    // Pro traffic goes to Grok, never the free-tier gateway path.
    expect(generateText).not.toHaveBeenCalled();
  });

  it('does not meter Pro users against the free daily quota', async () => {
    await saveEntitlement({
      email: 'pro-heavy@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });
    for (let i = 0; i < 8; i++) {
      const res = await POST(cookieReq('pro-heavy@example.com', `msg ${i}`));
      expect(res.status).toBe(200);
    }
  });
});
