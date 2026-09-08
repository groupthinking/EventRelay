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
  delete process.env.NEXT_PUBLIC_APP_URL;
  process.env.NODE_ENV = 'test';
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

  it('throws in production when monthly price id is missing', async () => {
    delete process.env.STRIPE_PRICE_PRO_MONTHLY;
    process.env.NODE_ENV = 'production';
    const { createProCheckoutSession } = await import('../stripe-checkout');
    await expect(
      createProCheckoutSession({ annual: false, flow: 'acquisition' }),
    ).rejects.toThrow('STRIPE_PRICE_PRO_MONTHLY missing');
  });

  it('never falls back to dead EventRelay Pro $19/$180 price IDs', async () => {
    delete process.env.STRIPE_PRICE_PRO_MONTHLY;
    delete process.env.STRIPE_PRICE_PRO_ANNUAL;
    process.env.NODE_ENV = 'test';
    const { createProCheckoutSession } = await import('../stripe-checkout');
    await createProCheckoutSession({ annual: false, flow: 'acquisition' });
    await createProCheckoutSession({ annual: true, flow: 'acquisition' });
    const prices = createMock.mock.calls.map((call) => call[0].line_items[0].price);
    expect(prices).toEqual([
      'price_1U9AbLAmTgsI2zgNEZD4Kwed',
      'price_1U9AbLAmTgsI2zgN0SM70JN9',
    ]);
    expect(prices).not.toContain('price_1Tos02AmTgsI2zgNWx7onroJ');
    expect(prices).not.toContain('price_1Tos0AAmTgsI2zgNSu5lwBv6');
  });

  it('sends production success and cancel URLs to https://uvai.io/pricing', async () => {
    delete process.env.NEXT_PUBLIC_APP_URL;
    process.env.NODE_ENV = 'production';
    const { createProCheckoutSession } = await import('../stripe-checkout');
    await createProCheckoutSession({ annual: false, flow: 'acquisition' });
    const args = createMock.mock.calls[createMock.mock.calls.length - 1][0];
    expect(args.success_url).toBe(
      'https://uvai.io/pricing?checkout=success&session_id={CHECKOUT_SESSION_ID}',
    );
    expect(args.cancel_url).toBe('https://uvai.io/pricing?checkout=cancelled');
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