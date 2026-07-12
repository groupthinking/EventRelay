import type Stripe from 'stripe';
import { getStripeClient } from './stripe-checkout';
import { syncFromSubscription } from './subscription-events';
import type { EntitlementRecord } from './entitlement-store';
import { normalizeBillingEmail } from './entitlement-store';
import { kaizenObserve } from './kaizen-trace';

export function sessionEmail(session: Stripe.Checkout.Session): string | null {
  const email =
    session.customer_details?.email ??
    session.customer_email ??
    session.metadata?.email ??
    (typeof session.customer === 'object' && session.customer && 'email' in session.customer
      ? (session.customer as Stripe.Customer).email
      : undefined);
  return email ? normalizeBillingEmail(email) : null;
}

export function sessionSubscriptionId(session: Stripe.Checkout.Session): string | null {
  if (typeof session.subscription === 'string') return session.subscription;
  return session.subscription?.id ?? null;
}

export async function activateFromStripeCustomerEmail(
  email: string,
): Promise<EntitlementRecord | null> {
  const stripe = getStripeClient();
  const customers = await stripe.customers.list({ email: normalizeBillingEmail(email), limit: 1 });
  const customer = customers.data[0];
  if (!customer) return null;

  const subs = await stripe.subscriptions.list({
    customer: customer.id,
    status: 'all',
    limit: 5,
  });

  const active = subs.data.find(
    (s) =>
      (s.status === 'active' || s.status === 'trialing') &&
      (s.metadata?.plan === 'pro' || s.items.data.length > 0),
  );
  if (!active) return null;

  kaizenObserve('billing', 'activate_stripe_lookup', `Found active subscription for ${email}`, {
    decision: `sub=${active.id}`,
  });
  return syncFromSubscription(active, email);
}