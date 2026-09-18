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
  getCheckoutSession: vi.fn(async () => ({
    id: 'cs_test_paid_workspace_zip',
    payment_status: 'paid',
    status: 'complete',
    customer_email: 'paid@example.com',
    metadata: { plan: 'pro' },
  })),
  createProCheckoutSession: vi.fn(async () => ({
    sessionId: 'cs_test_workspace_zip',
    url: 'https://checkout.stripe.com/c/pay/cs_test_workspace_zip',
  })),
}));

vi.mock('@/lib/billing/subscription-events', () => ({
  activateFromCheckoutSession: vi.fn(async () => ({
    email: 'paid@example.com',
    plan: 'pro',
    status: 'active',
    leadModel: 'grok-4-1-fast',
    updatedAt: '2026-09-08T00:00:00.000Z',
  })),
}));

import { POST } from '@/app/api/workspace/export/route';
import { getEntitlement, isProSubscriber } from '@/lib/billing/entitlement-store';
import { activateFromCheckoutSession } from '@/lib/billing/subscription-events';
import { createProCheckoutSession, getCheckoutSession } from '@/lib/billing/stripe-checkout';

function request(body: unknown): Request {
  return new Request('http://localhost/api/workspace/export', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('POST /api/workspace/export', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 402 with a Stripe checkout session when the caller is not Pro', async () => {
    vi.mocked(isProSubscriber).mockResolvedValue(false);
    vi.mocked(getEntitlement).mockResolvedValue(null);

    const response = await POST(
      request({
        projectName: 'workspace-pack',
        files: { 'README.md': '# workspace-pack\n' },
      }),
    );
    const body = await response.json();

    expect(response.status).toBe(402);
    expect(body).toEqual({
      error: 'Workspace ZIP exports require Pro. Upgrade to continue.',
      code: 'payment_required',
      upgradeRequired: true,
      plan: 'free',
      checkoutUrl: 'https://checkout.stripe.com/c/pay/cs_test_workspace_zip',
      sessionId: 'cs_test_workspace_zip',
      retryable: true,
      verificationUrl: '/api/billing/activate',
    });
    expect(createProCheckoutSession).toHaveBeenCalledWith({
      annual: false,
      customerEmail: undefined,
      flow: 'acquisition',
    });
  });

  it('returns a ZIP attachment for Pro callers', async () => {
    vi.mocked(isProSubscriber).mockResolvedValue(true);

    const response = await POST(
      request({
        projectName: 'workspace-pack',
        files: {
          'README.md': '# workspace-pack\n',
          'src/index.ts': "console.log('ok');\n",
        },
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toBe('application/zip');
    expect(response.headers.get('content-disposition')).toContain('workspace-pack.zip');
    expect(new Uint8Array(await response.arrayBuffer()).slice(0, 4)).toEqual(
      new Uint8Array([0x50, 0x4b, 0x03, 0x04]),
    );
    expect(createProCheckoutSession).not.toHaveBeenCalled();
  });

  it('verifies a paid checkout session and sets the billing cookie before downloading', async () => {
    vi.mocked(isProSubscriber).mockResolvedValue(false);
    vi.mocked(getEntitlement).mockResolvedValue(null);

    const response = await POST(
      request({
        projectName: 'workspace-pack',
        files: { 'README.md': '# workspace-pack\n' },
        sessionId: 'cs_test_paid_workspace_zip',
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('set-cookie')).toContain('er_billing_email=');
    expect(getCheckoutSession).toHaveBeenCalledWith('cs_test_paid_workspace_zip');
    expect(activateFromCheckoutSession).toHaveBeenCalled();
    expect(createProCheckoutSession).not.toHaveBeenCalled();
  });
});
