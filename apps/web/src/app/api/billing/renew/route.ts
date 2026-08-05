import { NextRequest, NextResponse } from 'next/server';
import { createProCheckoutSession } from '@/lib/billing/stripe-checkout';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { getEntitlement } from '@/lib/billing/entitlement-store';
import { kaizenObserve } from '@/lib/billing/kaizen-trace';

export async function POST(req: NextRequest) {
  let body: { annual?: boolean };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'invalid_json' }, { status: 400 });
  }

  const email = await resolveTrustedBillingEmail(req);
  const entitlement = email ? await getEntitlement(email) : null;
  const customerId = entitlement?.stripeCustomerId;

  kaizenObserve('billing', 'renewal_start', 'Returning user renewal checkout requested', {
    decision: `annual=${Boolean(body.annual)} email=${email ?? 'anonymous'} customerId=${customerId ? 'stored' : 'none'}`,
  });

  try {
    const result = await createProCheckoutSession({
      annual: Boolean(body.annual),
      customerEmail: email ?? undefined,
      customerId,
      flow: 'renewal',
    });

    kaizenObserve('billing', 'renewal_session', `Renewal session ${result.sessionId} ready`, {
      decision: 'redirect_to_stripe',
    });

    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'renewal_failed';
    // Unauthenticated public route (PUBLIC_API_EXACT) — keep Stripe SDK text,
    // which can echo account identifiers and partial API keys, server-side.
    console.error('[billing] renewal failed:', message);
    kaizenObserve('billing', 'renewal_error', message, { fix: 'verify_stripe_env' });
    return NextResponse.json(
      { error: 'renewal_failed', code: 'renewal_failed' },
      { status: 500 },
    );
  }
}