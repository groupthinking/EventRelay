import { describe, it, expect, beforeEach, vi } from 'vitest';
import { resetKaizenTracesForTests } from '../kaizen-trace';

const createMock = vi.fn().mockResolvedValue({
  id: 'cs_test_mock',
  url: 'https://checkout.stripe.com/mock',
  payment_status: 'unpaid',
});

vi.mock('stripe', () => {
  class StripeMock {
    checkout = { sessions: { create: createMock, retrieve: vi.fn() } };
    webhooks = { constructEvent: vi.fn() };
  }
  return { default: StripeMock };
});

beforeEach(() => {
  resetKaizenTracesForTests();
  createMock.mockClear();
  process.env.STRIPE_SECRET_KEY = 'sk_test_mock';
  process.env.STRIPE_PRICE_PRO_MONTHLY = 'price_monthly_env';
  process.env.STRIPE_PRICE_PRO_ANNUAL = 'price_annual_env';
});

describe('createProCheckoutSession', () => {
  it('creates subscription session with env price id', async () => {
    const { createProCheckoutSession } = await import('../stripe-checkout');
    const result = await createProCheckoutSession({
      annual: false,
      flow: 'acquisition',
      customerEmail: 'new@example.com',
    });
    expect(result.sessionId).toBe('cs_test_mock');
    expect(createMock).toHaveBeenCalledOnce();
    const args = createMock.mock.calls[0][0];
    expect(args.mode).toBe('subscription');
    expect(args.line_items[0].price).toBe('price_monthly_env');
    expect(args.metadata.flow).toBe('acquisition');
    expect(args.metadata.lead_model).toBeTruthy();
  });

  it('throws when monthly price id is missing', async () => {
    delete process.env.STRIPE_PRICE_PRO_MONTHLY;
    const { createProCheckoutSession } = await import('../stripe-checkout');
    await expect(
      createProCheckoutSession({ annual: false, flow: 'acquisition' }),
    ).rejects.toThrow('STRIPE_PRICE_PRO_MONTHLY missing');
  });

  it('uses env price id for annual renewal', async () => {
    const { createProCheckoutSession } = await import('../stripe-checkout');
    await createProCheckoutSession({
      annual: true,
      flow: 'renewal',
      customerId: 'cus_existing',
    });
    const args = createMock.mock.calls[createMock.mock.calls.length - 1][0];
    expect(args.line_items[0].price).toBe('price_annual_env');
    expect(args.customer).toBe('cus_existing');
    expect(args.metadata.flow).toBe('renewal');
  });
});