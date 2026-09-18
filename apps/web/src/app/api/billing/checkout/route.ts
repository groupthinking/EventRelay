import { NextRequest, NextResponse } from 'next/server';
import { createProCheckoutSession } from '@/lib/billing/stripe-checkout';
import { verifyTurnstileToken } from '@/lib/billing/turnstile';
import { kaizenObserve } from '@/lib/billing/kaizen-trace';

export async function POST(req: NextRequest) {
  let body: { annual?: boolean; email?: string; turnstileToken?: string }; // email → Stripe customer_email only
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'invalid_json', code: 'invalid_json' }, { status: 400 });
  }

  const turnstile = await verifyTurnstileToken(
    body.turnstileToken ?? '',
    req.headers.get('x-forwarded-for')?.split(',')[0]?.trim(),
  );

  if (!turnstile.ok) {
    kaizenObserve('billing', 'acquisition_blocked', 'Turnstile rejected acquisition checkout', {
      decision: turnstile.error ?? 'unknown',
    });
    // `turnstile.error` is always one of our own literals (`turnstile_not_configured`,
    // `turnstile_token_missing`, `siteverify_http_<status>`, `turnstile_verification_failed`,
    // `turnstile_verification_unavailable`)
    // — never Cloudflare response text — so it is safe to return. It is kept verbatim
    // for client compatibility; `code` is the stable machine-readable key, and the
    // fallback covers the `ok: false` shape that carries no `error`.
    return NextResponse.json(
      { error: turnstile.error ?? 'turnstile_rejected', code: 'turnstile_rejected' },
      { status: 403 },
    );
  }

  kaizenObserve('billing', 'acquisition_allowed', 'Turnstile passed for new Pro checkout');

  try {
    const result = await createProCheckoutSession({
      annual: Boolean(body.annual),
      customerEmail: body.email,
      flow: 'acquisition',
    });
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'checkout_failed';
    // This route is on the unauthenticated public allowlist (PUBLIC_API_EXACT),
    // so anything returned here is readable by any internet caller. Stripe SDK
    // messages can contain price/account identifiers and partial API keys, so
    // the raw text stays server-side only.
    console.error('[billing] checkout failed:', message);
    kaizenObserve('billing', 'checkout_error', message, { fix: 'verify_stripe_env' });
    return NextResponse.json(
      { error: 'checkout_failed', code: 'checkout_failed' },
      { status: 500 },
    );
  }
}