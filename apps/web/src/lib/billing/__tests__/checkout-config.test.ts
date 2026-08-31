import { afterEach, describe, it, expect } from 'vitest';
import {
  FALLBACK_STRIPE_PRICE_PRO_ANNUAL,
  FALLBACK_STRIPE_PRICE_PRO_MONTHLY,
  resolveCheckoutAppUrl,
  resolveProCheckoutParams,
  resolveStripePriceId,
  requireStripePriceId,
  workflowProPriceLabel,
  WORKFLOW_PRO_ANNUAL_CENTS,
  WORKFLOW_PRO_MONTHLY_CENTS,
  WORKFLOW_PRO_PRODUCT_NAME,
} from '../checkout-config';

const DEAD_EVENTRELAY_PRO_PRICES = [
  'price_1Tos02AmTgsI2zgNWx7onroJ',
  'price_1Tos0AAmTgsI2zgNSu5lwBv6',
] as const;

const LIVE_WORKFLOW_PRO_MONTHLY = 'price_1U9AbLAmTgsI2zgNEZD4Kwed';
const LIVE_WORKFLOW_PRO_ANNUAL = 'price_1U9AbLAmTgsI2zgN0SM70JN9';

const originalEnv = {
  monthly: process.env.STRIPE_PRICE_PRO_MONTHLY,
  annual: process.env.STRIPE_PRICE_PRO_ANNUAL,
  appUrl: process.env.NEXT_PUBLIC_APP_URL,
  nodeEnv: process.env.NODE_ENV,
};

function restoreEnv() {
  if (originalEnv.monthly === undefined) delete process.env.STRIPE_PRICE_PRO_MONTHLY;
  else process.env.STRIPE_PRICE_PRO_MONTHLY = originalEnv.monthly;
  if (originalEnv.annual === undefined) delete process.env.STRIPE_PRICE_PRO_ANNUAL;
  else process.env.STRIPE_PRICE_PRO_ANNUAL = originalEnv.annual;
  if (originalEnv.appUrl === undefined) delete process.env.NEXT_PUBLIC_APP_URL;
  else process.env.NEXT_PUBLIC_APP_URL = originalEnv.appUrl;
  process.env.NODE_ENV = originalEnv.nodeEnv;
}

afterEach(restoreEnv);

describe('resolveProCheckoutParams', () => {
  it('builds monthly Workflow Pro checkout at $39', () => {
    const params = resolveProCheckoutParams({ annual: false, appUrl: 'https://uvai.io/' });
    expect(params.interval).toBe('month');
    expect(params.unitAmountCents).toBe(3900);
    expect(params.unitAmountCents).toBe(WORKFLOW_PRO_MONTHLY_CENTS);
    expect(params.productName).toBe('UVAI Workflow Pro');
    expect(params.productName).toBe(WORKFLOW_PRO_PRODUCT_NAME);
    expect(params.mode).toBe('subscription');
    expect(params.successUrl).toBe(
      'https://uvai.io/pricing?checkout=success&session_id={CHECKOUT_SESSION_ID}',
    );
    expect(params.cancelUrl).toBe('https://uvai.io/pricing?checkout=cancelled');
  });

  it('builds annual Workflow Pro checkout at $390/yr', () => {
    const params = resolveProCheckoutParams({ annual: true, appUrl: 'https://uvai.io' });
    expect(params.interval).toBe('year');
    expect(params.unitAmountCents).toBe(39_000);
    expect(params.unitAmountCents).toBe(WORKFLOW_PRO_ANNUAL_CENTS);
    expect(params.productName).toBe('UVAI Workflow Pro');
    expect(params.successUrl).toContain('https://uvai.io/pricing');
    expect(params.cancelUrl).toContain('https://uvai.io/pricing');
  });

  it('never encodes the stale EventRelay Pro $19/$180 amounts', () => {
    const monthly = resolveProCheckoutParams({ annual: false, appUrl: 'https://uvai.io' });
    const annual = resolveProCheckoutParams({ annual: true, appUrl: 'https://uvai.io' });
    expect(monthly.unitAmountCents).not.toBe(1900);
    expect(annual.unitAmountCents).not.toBe(18_000);
    expect(monthly.productName).not.toBe('EventRelay Pro');
    expect(annual.productName).not.toBe('EventRelay Pro');
  });
});

describe('workflowProPriceLabel', () => {
  it('says $39/mo and $390/yr for UVAI Workflow Pro', () => {
    expect(workflowProPriceLabel(false)).toBe('$39/mo');
    expect(workflowProPriceLabel(true)).toBe('$390/yr');
    expect(workflowProPriceLabel(false)).not.toBe('$19/mo');
    expect(workflowProPriceLabel(true)).not.toBe('$180/yr');
  });
});

describe('resolveCheckoutAppUrl', () => {
  it('prefers NEXT_PUBLIC_APP_URL when set', () => {
    process.env.NEXT_PUBLIC_APP_URL = 'https://preview.example.com/';
    expect(resolveCheckoutAppUrl()).toBe('https://preview.example.com');
  });

  it('defaults production checkout redirects to uvai.io', () => {
    delete process.env.NEXT_PUBLIC_APP_URL;
    process.env.NODE_ENV = 'production';
    expect(resolveCheckoutAppUrl()).toBe('https://uvai.io');
  });
});

describe('resolveStripePriceId', () => {
  it('reads price ids from env when set', () => {
    process.env.STRIPE_PRICE_PRO_MONTHLY = 'price_monthly_test';
    process.env.STRIPE_PRICE_PRO_ANNUAL = 'price_annual_test';
    expect(resolveStripePriceId(false)).toBe('price_monthly_test');
    expect(resolveStripePriceId(true)).toBe('price_annual_test');
  });

  it('uses documented Workflow Pro live price IDs as last-resort fallbacks outside production', () => {
    delete process.env.STRIPE_PRICE_PRO_MONTHLY;
    delete process.env.STRIPE_PRICE_PRO_ANNUAL;
    process.env.NODE_ENV = 'test';
    expect(resolveStripePriceId(false)).toBe(LIVE_WORKFLOW_PRO_MONTHLY);
    expect(resolveStripePriceId(true)).toBe(LIVE_WORKFLOW_PRO_ANNUAL);
    expect(FALLBACK_STRIPE_PRICE_PRO_MONTHLY).toBe(LIVE_WORKFLOW_PRO_MONTHLY);
    expect(FALLBACK_STRIPE_PRICE_PRO_ANNUAL).toBe(LIVE_WORKFLOW_PRO_ANNUAL);
    expect(DEAD_EVENTRELAY_PRO_PRICES).not.toContain(resolveStripePriceId(false));
    expect(DEAD_EVENTRELAY_PRO_PRICES).not.toContain(resolveStripePriceId(true));
  });
});

describe('requireStripePriceId', () => {
  it('throws in production when env price is unset', () => {
    delete process.env.STRIPE_PRICE_PRO_MONTHLY;
    process.env.NODE_ENV = 'production';
    expect(() => requireStripePriceId(false)).toThrow('STRIPE_PRICE_PRO_MONTHLY missing');
  });

  it('throws in production when annual env price is unset', () => {
    delete process.env.STRIPE_PRICE_PRO_ANNUAL;
    process.env.NODE_ENV = 'production';
    expect(() => requireStripePriceId(true)).toThrow('STRIPE_PRICE_PRO_ANNUAL missing');
  });
});
