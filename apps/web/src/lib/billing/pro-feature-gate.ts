import { NextResponse } from 'next/server';
import { BILLING_EMAIL_COOKIE, resolveTrustedBillingEmail } from './billing-context';
import { signBillingEmail } from './billing-cookie';
import { getCheckoutActivation } from './checkout-session-store';
import type { EntitlementRecord } from './entitlement-store';
import { getEntitlement, isProSubscriber } from './entitlement-store';
import { kaizenObserve } from './kaizen-trace';
import { createProCheckoutSession, getCheckoutSession } from './stripe-checkout';
import { activateFromCheckoutSession } from './subscription-events';

type ProFeatureLabel = 'Workspace ZIP exports' | 'Refinery dataset access';

type ProAccessGranted = {
  ok: true;
  signedBillingEmail?: string;
};

type ProAccessBlocked = {
  ok: false;
  response: NextResponse;
};

function proRequirementVerb(featureLabel: ProFeatureLabel): 'require' | 'requires' {
  return featureLabel === 'Workspace ZIP exports' ? 'require' : 'requires';
}

function entitlementFromActivationLink(
  link: NonNullable<Awaited<ReturnType<typeof getCheckoutActivation>>>,
): EntitlementRecord {
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

async function verifySessionEntitlement(
  sessionId?: string | null,
): Promise<EntitlementRecord | null> {
  const trimmed = sessionId?.trim();
  if (!trimmed) return null;

  const linked = await getCheckoutActivation(trimmed);
  if (linked?.plan === 'pro' && (linked.status === 'active' || linked.status === 'trialing')) {
    return entitlementFromActivationLink(linked);
  }

  const session = await getCheckoutSession(trimmed);
  return activateFromCheckoutSession(session);
}

export function applyVerifiedBillingCookie(
  response: NextResponse,
  signedBillingEmail?: string,
): void {
  if (!signedBillingEmail) return;

  response.cookies.set(BILLING_EMAIL_COOKIE, signedBillingEmail, {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 365,
    secure: process.env.NODE_ENV === 'production',
  });
}

export async function requireProFeatureAccess(
  request: Request,
  input: {
    featureKey: 'workspace_export' | 'refinery_dataset';
    featureLabel: ProFeatureLabel;
    sessionId?: string | null;
  },
): Promise<ProAccessGranted | ProAccessBlocked> {
  const billingEmail = await resolveTrustedBillingEmail(request);
  if (await isProSubscriber(billingEmail)) {
    return { ok: true };
  }

  try {
    const verified = await verifySessionEntitlement(input.sessionId);
    if (verified?.plan === 'pro' && (verified.status === 'active' || verified.status === 'trialing')) {
      return {
        ok: true,
        signedBillingEmail: signBillingEmail(verified.email) ?? undefined,
      };
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'verification_failed';
    console.error(`[billing] ${input.featureKey} verification failed:`, message);
    kaizenObserve('billing', `${input.featureKey}_verification_error`, message, {
      fix: 'inspect_stripe_checkout_session',
    });
  }

  try {
    const entitlement = billingEmail ? await getEntitlement(billingEmail) : null;
    const checkout = await createProCheckoutSession({
      annual: false,
      customerEmail: billingEmail ?? undefined,
      customerId: entitlement?.stripeCustomerId,
      flow: entitlement?.stripeCustomerId ? 'renewal' : 'acquisition',
    });

    kaizenObserve(
      'billing',
      `${input.featureKey}_blocked`,
      `${input.featureLabel} ${proRequirementVerb(input.featureLabel)} Pro`,
      {
      decision: `email=${billingEmail ?? 'anonymous'}`,
      fix: 'upgrade_to_pro',
      },
    );

    return {
      ok: false,
      response: NextResponse.json(
        {
          error: `${input.featureLabel} ${proRequirementVerb(input.featureLabel)} Pro. Upgrade to continue.`,
          code: 'payment_required',
          upgradeRequired: true,
          plan: 'free',
          checkoutUrl: checkout.url,
          sessionId: checkout.sessionId,
          retryable: true,
          verificationUrl: '/api/billing/activate',
        },
        { status: 402 },
      ),
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'payment_gate_failed';
    console.error(`[billing] ${input.featureKey} payment gate failed:`, message);
    kaizenObserve('billing', `${input.featureKey}_error`, message, {
      fix: 'verify_stripe_env',
    });
    return {
      ok: false,
      response: NextResponse.json(
        { error: 'payment_gate_failed', code: 'payment_gate_failed' },
        { status: 500 },
      ),
    };
  }
}
