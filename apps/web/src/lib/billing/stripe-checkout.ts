import Stripe from 'stripe';
import { billingLeadMetadata } from './grok-lead';
import {
  resolveCheckoutAppUrl,
  resolveProCheckoutParams,
  requireStripePriceId,
} from './checkout-config';
import { kaizenObserve } from './kaizen-trace';

export function getStripeClient(): Stripe {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) {
    throw new Error('STRIPE_SECRET_KEY missing');
  }
  return new Stripe(key);
}

export type CreateCheckoutInput = {
  annual: boolean;
  customerEmail?: string;
  flow: 'acquisition' | 'renewal';
  customerId?: string;
};

export type CreateCheckoutResult = {
  sessionId: string;
  url: string | null;
};

export async function createProCheckoutSession(
  input: CreateCheckoutInput,
): Promise<CreateCheckoutResult> {
  const stripe = getStripeClient();
  const appUrl = resolveCheckoutAppUrl();
  const params = resolveProCheckoutParams({ annual: input.annual, appUrl });
  const priceId = requireStripePriceId(input.annual);

  kaizenObserve('billing', 'checkout_build', 'Resolving Pro checkout session params', {
    decision: `interval=${params.interval} flow=${input.flow} priceId=${priceId}`,
  });

  const lineItems: Stripe.Checkout.SessionCreateParams.LineItem[] = [
    { price: priceId, quantity: 1 },
  ];

  const session = await stripe.checkout.sessions.create({
    mode: params.mode,
    success_url: params.successUrl,
    cancel_url: params.cancelUrl,
    customer: input.customerId,
    customer_email: input.customerId ? undefined : input.customerEmail,
    line_items: lineItems,
    metadata: {
      plan: 'pro',
      interval: params.interval,
      flow: input.flow,
      ...(input.customerEmail ? { email: input.customerEmail } : {}),
      ...billingLeadMetadata(),
    },
    subscription_data: {
      metadata: {
        plan: 'pro',
        flow: input.flow,
        ...billingLeadMetadata(),
      },
    },
  });

  kaizenObserve('billing', 'checkout_created', `Stripe session ${session.id} created`, {
    decision: `payment_status=${session.payment_status}`,
  });

  return { sessionId: session.id, url: session.url };
}

export async function getCheckoutSession(sessionId: string): Promise<Stripe.Checkout.Session> {
  const stripe = getStripeClient();
  return stripe.checkout.sessions.retrieve(sessionId, {
    expand: ['subscription', 'customer'],
  });
}