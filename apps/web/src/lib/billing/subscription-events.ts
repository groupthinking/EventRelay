import type Stripe from 'stripe';
import { GROK_BILLING_LEAD_MODEL } from './grok-lead';
import type { EntitlementRecord, PlanTier } from './entitlement-store';
import { saveEntitlement, normalizeBillingEmail } from './entitlement-store';
import { linkCheckoutActivation } from './checkout-session-store';
import { kaizenObserve } from './kaizen-trace';
import { getStripeClient } from './stripe-checkout';
import {
  activateFromStripeCustomerEmail,
  sessionEmail,
  sessionSubscriptionId,
} from './stripe-subscription-lookup';

export function entitlementFromCheckoutSession(
  session: Stripe.Checkout.Session,
): EntitlementRecord | null {
  const email =
    session.customer_details?.email ??
    session.customer_email ??
    session.metadata?.email;
  if (!email) return null;

  const plan = (session.metadata?.plan === 'pro' ? 'pro' : 'free') as PlanTier;
  const isPaid =
    session.payment_status === 'paid' || session.status === 'complete';

  return {
    email: normalizeBillingEmail(email),
    plan: isPaid ? plan : 'free',
    status: isPaid ? 'active' : 'inactive',
    stripeCustomerId:
      typeof session.customer === 'string' ? session.customer : session.customer?.id,
    stripeSubscriptionId:
      typeof session.subscription === 'string'
        ? session.subscription
        : session.subscription?.id,
    leadModel: session.metadata?.lead_model ?? GROK_BILLING_LEAD_MODEL,
    updatedAt: new Date().toISOString(),
  };
}

export function entitlementFromSubscription(
  sub: Stripe.Subscription,
  email?: string,
): EntitlementRecord | null {
  const resolvedEmail =
    email ??
    sub.metadata?.email ??
    (typeof sub.customer === 'object' && sub.customer && 'email' in sub.customer
      ? (sub.customer as Stripe.Customer).email
      : undefined);
  if (!resolvedEmail) return null;

  const active = sub.status === 'active' || sub.status === 'trialing';
  const plan = (sub.metadata?.plan === 'pro' && active ? 'pro' : 'free') as PlanTier;

  return {
    email: normalizeBillingEmail(resolvedEmail),
    plan,
    status: sub.status as EntitlementRecord['status'],
    stripeCustomerId:
      typeof sub.customer === 'string' ? sub.customer : sub.customer?.id,
    stripeSubscriptionId: sub.id,
    leadModel: sub.metadata?.lead_model ?? GROK_BILLING_LEAD_MODEL,
    updatedAt: new Date().toISOString(),
  };
}

export async function activateFromCheckoutSession(
  session: Stripe.Checkout.Session,
): Promise<EntitlementRecord | null> {
  const record = entitlementFromCheckoutSession(session);
  if (record?.plan === 'pro') {
    const saved = await saveEntitlement(record);
    if (session.id) {
      await linkCheckoutActivation(session.id, saved);
      kaizenObserve('billing', 'checkout_linked', `Session ${session.id} linked to ${saved.email}`, {
        decision: 'session_scoped_activation',
      });
    }
    kaizenObserve('billing', 'pro_activated', `Pro activated for ${saved.email}`, {
      decision: `subscription=${saved.stripeSubscriptionId ?? 'none'}`,
    });
    return saved;
  }

  const isPaid =
    session.payment_status === 'paid' || session.status === 'complete';
  if (!isPaid) {
    kaizenObserve('billing', 'activation_skipped', 'Checkout session not eligible for Pro', {
      decision: `payment_status=${session.payment_status} status=${session.status}`,
    });
    return null;
  }

  const subId = sessionSubscriptionId(session);
  if (subId) {
    const stripe = getStripeClient();
    const sub = await stripe.subscriptions.retrieve(subId);
    const synced = await syncFromSubscription(sub, sessionEmail(session) ?? undefined);
    if (synced?.plan === 'pro') return synced;
  }

  const email = sessionEmail(session);
  if (email) {
    const fromStripe = await activateFromStripeCustomerEmail(email);
    if (fromStripe?.plan === 'pro') return fromStripe;
  }

  kaizenObserve('billing', 'activation_skipped', 'Checkout session not eligible for Pro', {
    decision: `payment_status=${session.payment_status} status=${session.status}`,
  });
  return null;
}

export async function syncFromSubscription(
  sub: Stripe.Subscription,
  email?: string,
): Promise<EntitlementRecord | null> {
  const record = entitlementFromSubscription(sub, email);
  if (!record) return null;
  const saved = await saveEntitlement(record);
  kaizenObserve('billing', 'subscription_synced', `Synced ${saved.email} plan=${saved.plan}`, {
    decision: `status=${saved.status}`,
  });
  return saved;
}