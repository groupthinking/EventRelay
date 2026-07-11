export type BillingInterval = 'month' | 'year';

export type ProCheckoutParams = {
  interval: BillingInterval;
  unitAmountCents: number;
  mode: 'subscription';
  productName: string;
  successUrl: string;
  cancelUrl: string;
};

export function resolveProCheckoutParams(input: {
  annual: boolean;
  appUrl: string;
}): ProCheckoutParams {
  const base = input.appUrl.replace(/\/$/, '');
  const interval: BillingInterval = input.annual ? 'year' : 'month';
  const unitAmountCents = input.annual ? 18_000 : 1_900;

  return {
    interval,
    unitAmountCents,
    mode: 'subscription',
    productName: 'EventRelay Pro',
    successUrl: `${base}/pricing?checkout=success&session_id={CHECKOUT_SESSION_ID}`,
    cancelUrl: `${base}/pricing?checkout=cancelled`,
  };
}

export function resolveStripePriceId(annual: boolean): string | undefined {
  const raw = annual
    ? process.env.STRIPE_PRICE_PRO_ANNUAL
    : process.env.STRIPE_PRICE_PRO_MONTHLY;
  const trimmed = raw?.trim();
  return trimmed || undefined;
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