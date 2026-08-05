import { NextRequest, NextResponse } from 'next/server';
import { getCheckoutSession } from '@/lib/billing/stripe-checkout';
import { getCheckoutActivation } from '@/lib/billing/checkout-session-store';
import { activateFromCheckoutSession } from '@/lib/billing/subscription-events';
import type { EntitlementRecord } from '@/lib/billing/entitlement-store';
import { BILLING_EMAIL_COOKIE } from '@/lib/billing/billing-context';
import { signBillingEmail } from '@/lib/billing/billing-cookie';
import { kaizenObserve } from '@/lib/billing/kaizen-trace';

function entitlementFromLink(link: NonNullable<Awaited<ReturnType<typeof getCheckoutActivation>>>): EntitlementRecord {
  return {
    email: link.email,
    plan: link.plan,
    status: link.status,
    stripeCustomerId: link.stripeCustomerId,
    stripeSubscriptionId: link.stripeSubscriptionId,
    leadModel: link.leadModel,
    updatedAt: link.fulfilledAt,
  };
}

export async function POST(req: NextRequest) {
  let body: { sessionId?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'invalid_json' }, { status: 400 });
  }

  if (!body.sessionId?.trim()) {
    return NextResponse.json({ error: 'session_id_required' }, { status: 400 });
  }

  const sessionId = body.sessionId.trim();

  try {
    let entitlement: EntitlementRecord | null = null;
    const linked = await getCheckoutActivation(sessionId);

    if (linked?.plan === 'pro' && (linked.status === 'active' || linked.status === 'trialing')) {
      entitlement = entitlementFromLink(linked);
      kaizenObserve('billing', 'activate_session_link', `Activated via checkout link ${sessionId}`, {
        decision: `email=${linked.email}`,
      });
    } else {
      const session = await getCheckoutSession(sessionId);
      entitlement = await activateFromCheckoutSession(session);
    }

    if (!entitlement || entitlement.plan !== 'pro') {
      return NextResponse.json(
        { error: 'not_eligible', sessionId },
        { status: 402 },
      );
    }

    kaizenObserve('billing', 'activate_api', `Client activated ${entitlement.email}`);

    const res = NextResponse.json({
      plan: entitlement.plan,
      status: entitlement.status,
      email: entitlement.email,
      features: {
        unlimitedChat: true,
        agentDispatch: true,
        apiAccess: true,
        leadModel: entitlement.leadModel,
      },
    });
    // Set an HMAC-signed identity cookie so it cannot be forged client-side.
    // If no signing secret is configured we intentionally do NOT set a cookie
    // rather than fall back to a forgeable plaintext value.
    const signedEmail = signBillingEmail(entitlement.email);
    if (signedEmail) {
      res.cookies.set(BILLING_EMAIL_COOKIE, signedEmail, {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        maxAge: 60 * 60 * 24 * 365,
        secure: process.env.NODE_ENV === 'production',
      });
    } else {
      kaizenObserve(
        'billing',
        'activate_cookie_skipped',
        'No billing cookie secret configured; identity cookie not set',
        { fix: 'set_BILLING_COOKIE_SECRET_or_STRIPE_WEBHOOK_SECRET' },
      );
    }
    return res;
  } catch (err) {
    const message = err instanceof Error ? err.message : 'activation_failed';
    // Unauthenticated public route (PUBLIC_API_EXACT) — keep Stripe SDK text,
    // which can echo account identifiers and partial API keys, server-side.
    console.error('[billing] activation failed:', message);
    kaizenObserve('billing', 'activate_error', message, { fix: 'inspect_stripe_checkout_session' });
    return NextResponse.json(
      { error: 'activation_failed', code: 'activation_failed' },
      { status: 500 },
    );
  }
}
