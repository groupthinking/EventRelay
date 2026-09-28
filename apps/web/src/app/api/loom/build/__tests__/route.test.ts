import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { saveEntitlement, resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { signBillingEmail } from '@/lib/billing/billing-cookie';

const { buildFromLoomShare } = vi.hoisted(() => ({
  buildFromLoomShare: vi.fn(),
}));

vi.mock('@/lib/loom-pro-build', () => ({
  buildFromLoomShare,
  LoomBuildError: class LoomBuildError extends Error {
    readonly code: string;
    readonly status: number;
    constructor(message: string, code: string, status: number) {
      super(message);
      this.code = code;
      this.status = status;
    }
  },
}));

import { POST } from '@/app/api/loom/build/route';

const SHARE = 'https://www.loom.com/share/c43a642f815f4378b6f80a889bb73d8d';

function requestFor(email: string | null, url: string) {
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (email) {
    headers.cookie = `er_billing_email=${encodeURIComponent(signBillingEmail(email) as string)}`;
  }
  return new Request('http://localhost/api/loom/build', {
    method: 'POST',
    headers,
    body: JSON.stringify({ url }),
  });
}

const savedPaywall = process.env.TEMP_PAYWALL_OFF;

beforeEach(() => {
  resetEntitlementStoreForTests();
  buildFromLoomShare.mockReset();
  process.env.TEMP_PAYWALL_OFF = '0';
  buildFromLoomShare.mockResolvedValue({
    loomId: 'c43a642f815f4378b6f80a889bb73d8d',
    shareUrl: SHARE,
    transcript: 'Ship the queue.',
    duration: 9.5,
    answer: 'Build the queue worker.',
    provider: 'xai',
    model: 'grok-4-1-fast',
    sttModel: 'grok-voice-transcribe-2.0',
    audioSource: 'transcoded-url',
  });
});

afterEach(() => {
  if (savedPaywall === undefined) delete process.env.TEMP_PAYWALL_OFF;
  else process.env.TEMP_PAYWALL_OFF = savedPaywall;
});

describe('POST /api/loom/build', () => {
  it('rejects anonymous and free sessions before transcription', async () => {
    const anon = await POST(requestFor(null, SHARE));
    expect(anon.status).toBe(402);
    expect(buildFromLoomShare).not.toHaveBeenCalled();

    const free = await POST(requestFor('free@example.com', SHARE));
    expect(free.status).toBe(402);
    const freeBody = await free.json();
    expect(freeBody.code).toBe('pro_required');
    expect(buildFromLoomShare).not.toHaveBeenCalled();
  });

  it('runs the Pro Grok build for a stored Pro entitlement', async () => {
    await saveEntitlement({
      email: 'pro@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });
    const response = await POST(requestFor('pro@example.com', SHARE));
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.provider).toBe('xai');
    expect(body.transcript).toBe('Ship the queue.');
    expect(body.duration).toBe(9.5);
    expect(body.answer).toContain('queue worker');
    expect(buildFromLoomShare).toHaveBeenCalledWith(SHARE, expect.any(String));
  });

  it('allows a paywall-bypass signed session without a stored entitlement', async () => {
    process.env.TEMP_PAYWALL_OFF = '1';
    const response = await POST(requestFor('dogfood@example.com', SHARE));
    expect(response.status).toBe(200);
    expect(buildFromLoomShare).toHaveBeenCalledTimes(1);
  });

  it('rejects a non-Loom URL before the Pro check spends a model call', async () => {
    await saveEntitlement({
      email: 'pro@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });
    const response = await POST(requestFor('pro@example.com', 'https://www.youtube.com/watch?v=auJzb1D-fag'));
    expect(response.status).toBe(400);
    expect((await response.json()).code).toBe('loom_url_invalid');
    expect(buildFromLoomShare).not.toHaveBeenCalled();
  });
});
