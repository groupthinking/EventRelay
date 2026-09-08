import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/billing/billing-context', () => ({
  BILLING_EMAIL_COOKIE: 'er_billing_email',
  resolveTrustedBillingEmail: vi.fn(async () => null),
}));

vi.mock('@/lib/billing/entitlement-store', () => ({
  getEntitlement: vi.fn(async () => null),
  isProSubscriber: vi.fn(async () => false),
}));

vi.mock('@/lib/billing/stripe-checkout', () => ({
  createProCheckoutSession: vi.fn(async () => ({
    sessionId: 'cs_test_refinery_dataset',
    url: 'https://checkout.stripe.com/c/pay/cs_test_refinery_dataset',
  })),
}));

vi.mock('@/lib/training-store', () => ({
  getTrainingStatus: vi.fn(async () => ({
    metadata: {
      totalExamples: 2,
      lastUpdated: '2026-09-08T00:00:00.000Z',
      lastVideoUrl: 'https://youtu.be/auJzb1D-fag',
      lastVideoTitle: 'Canon',
      tuningTriggered: false,
      tuningTriggeredAt: null,
      tuningJobId: null,
      videosProcessed: ['https://youtu.be/auJzb1D-fag'],
    },
    readyForTuning: false,
    progress: 2,
    nextMilestone: 25,
  })),
  readTrainingFile: vi.fn(async () => '{"contents":[{"role":"user","parts":[{"text":"Analyze this video: https://youtu.be/auJzb1D-fag"}]}]}\n'),
}));

import { GET } from '@/app/api/v1/refinery/dataset/route';
import { getEntitlement, isProSubscriber } from '@/lib/billing/entitlement-store';
import { createProCheckoutSession } from '@/lib/billing/stripe-checkout';

function request(query = ''): Request {
  return new Request(`http://localhost/api/v1/refinery/dataset${query}`, {
    method: 'GET',
  });
}

describe('GET /api/v1/refinery/dataset', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 402 with Stripe checkout details for free callers', async () => {
    vi.mocked(isProSubscriber).mockResolvedValue(false);
    vi.mocked(getEntitlement).mockResolvedValue(null);

    const response = await GET(request());
    const body = await response.json();

    expect(response.status).toBe(402);
    expect(body).toEqual({
      error: 'Refinery dataset access requires Pro. Upgrade to continue.',
      code: 'payment_required',
      upgradeRequired: true,
      plan: 'free',
      checkoutUrl: 'https://checkout.stripe.com/c/pay/cs_test_refinery_dataset',
      sessionId: 'cs_test_refinery_dataset',
      retryable: true,
      verificationUrl: '/api/billing/activate',
    });
    expect(createProCheckoutSession).toHaveBeenCalledWith({
      annual: false,
      customerEmail: undefined,
      flow: 'acquisition',
    });
  });

  it('returns the raw dataset as a download for Pro callers', async () => {
    vi.mocked(isProSubscriber).mockResolvedValue(true);

    const response = await GET(request('?download=1'));
    const text = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toBe('application/x-ndjson; charset=utf-8');
    expect(response.headers.get('content-disposition')).toContain('refinery-dataset.jsonl');
    expect(response.headers.get('x-training-examples')).toBe('2');
    expect(text).toContain('Analyze this video: https://youtu.be/auJzb1D-fag');
    expect(createProCheckoutSession).not.toHaveBeenCalled();
  });
});
