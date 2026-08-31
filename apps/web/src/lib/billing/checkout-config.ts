export type BillingInterval = 'month' | 'year';

export const WORKFLOW_PRO_MONTHLY_CENTS = 3_900;
export const WORKFLOW_PRO_ANNUAL_CENTS = 39_000;
export const WORKFLOW_PRO_PRODUCT_NAME = 'UVAI Workflow Pro';

/**
 * Last-resort documented Stripe Price IDs for UVAI Workflow Pro.
 * Prefer STRIPE_PRICE_PRO_MONTHLY / STRIPE_PRICE_PRO_ANNUAL.
 * Never use the dead EventRelay Pro $19/$180 IDs
 * (price_1Tos02AmTgsI2zgNWx7onroJ / price_1Tos0AAmTgsI2zgNSu5lwBv6).
 * Production still requires env — these are not used when NODE_ENV=production.
 */
export const FALLBACK_STRIPE_PRICE_PRO_MONTHLY = 'price_1U9AbLAmTgsI2zgNEZD4Kwed';
export const FALLBACK_STRIPE_PRICE_PRO_ANNUAL = 'price_1U9AbLAmTgsI2zgN0SM70JN9';

export function workflowProPriceLabel(annual: boolean): string {
  const cents = annual ? WORKFLOW_PRO_ANNUAL_CENTS : WORKFLOW_PRO_MONTHLY_CENTS;
  return `$${cents / 100}${annual ? '/yr' : '/mo'}`;
}

const PRODUCTION_APP_URL = 'https://uvai.io';
const LOCAL_APP_URL = 'http://localhost:3000';

export type ProCheckoutParams = {
  interval: BillingInterval;
  unitAmountCents: number;
  mode: 'subscription';
  productName: string;
  successUrl: string;
  cancelUrl: string;
};

export function resolveCheckoutAppUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_APP_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, '');
  }
  return process.env.NODE_ENV === 'production' ? PRODUCTION_APP_URL : LOCAL_APP_URL;
}

export function resolveProCheckoutParams(input: {
  annual: boolean;
  appUrl: string;
}): ProCheckoutParams {
  const base = input.appUrl.replace(/\/$/, '');
  const interval: BillingInterval = input.annual ? 'year' : 'month';
  const unitAmountCents = input.annual
    ? WORKFLOW_PRO_ANNUAL_CENTS
    : WORKFLOW_PRO_MONTHLY_CENTS;

  return {
    interval,
    unitAmountCents,
    mode: 'subscription',
    productName: WORKFLOW_PRO_PRODUCT_NAME,
    successUrl: `${base}/pricing?checkout=success&session_id={CHECKOUT_SESSION_ID}`,
    cancelUrl: `${base}/pricing?checkout=cancelled`,
  };
}

export function resolveStripePriceId(annual: boolean): string | undefined {
  const raw = annual
    ? process.env.STRIPE_PRICE_PRO_ANNUAL
    : process.env.STRIPE_PRICE_PRO_MONTHLY;
  const trimmed = raw?.trim();
  if (trimmed) {
    return trimmed;
  }
  if (process.env.NODE_ENV === 'production') {
    return undefined;
  }
  return annual ? FALLBACK_STRIPE_PRICE_PRO_ANNUAL : FALLBACK_STRIPE_PRICE_PRO_MONTHLY;
}

export function requireStripePriceId(annual: boolean): string {
  const priceId = resolveStripePriceId(annual);
  if (!priceId) {
    throw new Error(
      annual ? 'STRIPE_PRICE_PRO_ANNUAL missing' : 'STRIPE_PRICE_PRO_MONTHLY missing',
    );
  }
  return priceId;
}
