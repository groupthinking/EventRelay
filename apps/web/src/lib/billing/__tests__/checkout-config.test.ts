import { describe, it, expect } from 'vitest';
import {
  resolveProCheckoutParams,
  resolveStripePriceId,
  requireStripePriceId,
} from '../checkout-config';

describe('resolveProCheckoutParams', () => {
  it('builds monthly subscription checkout URLs', () => {
    const params = resolveProCheckoutParams({ annual: false, appUrl: 'http://localhost:3000/' });
    expect(params.interval).toBe('month');
    expect(params.unitAmountCents).toBe(1900);
    expect(params.mode).toBe('subscription');
    expect(params.successUrl).toContain('checkout=success');
    expect(params.cancelUrl).toContain('checkout=cancelled');
  });

  it('builds annual subscription at $180/yr', () => {
    const params = resolveProCheckoutParams({ annual: true, appUrl: 'https://app.example.com' });
    expect(params.interval).toBe('year');
    expect(params.unitAmountCents).toBe(18_000);
  });
});

describe('resolveStripePriceId', () => {
  it('reads price ids from env when set', () => {
    const prevMonthly = process.env.STRIPE_PRICE_PRO_MONTHLY;
    const prevAnnual = process.env.STRIPE_PRICE_PRO_ANNUAL;
    process.env.STRIPE_PRICE_PRO_MONTHLY = 'price_monthly_test';
    process.env.STRIPE_PRICE_PRO_ANNUAL = 'price_annual_test';
    expect(resolveStripePriceId(false)).toBe('price_monthly_test');
    expect(resolveStripePriceId(true)).toBe('price_annual_test');
    process.env.STRIPE_PRICE_PRO_MONTHLY = prevMonthly;
    process.env.STRIPE_PRICE_PRO_ANNUAL = prevAnnual;
  });
});

describe('requireStripePriceId', () => {
  it('throws when env price is unset', () => {
    const prev = process.env.STRIPE_PRICE_PRO_MONTHLY;
    delete process.env.STRIPE_PRICE_PRO_MONTHLY;
    expect(() => requireStripePriceId(false)).toThrow('STRIPE_PRICE_PRO_MONTHLY missing');
    process.env.STRIPE_PRICE_PRO_MONTHLY = prev;
  });
});