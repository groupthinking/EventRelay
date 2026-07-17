import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { getStripeClient } from '@/lib/billing/stripe-checkout';
import { activateFromCheckoutSession, syncFromSubscription } from '@/lib/billing/subscription-events';
import { kaizenObserve } from '@/lib/billing/kaizen-trace';

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secret) {
    return NextResponse.json({ error: 'webhook_not_configured' }, { status: 503 });
  }

  const signature = req.headers.get('stripe-signature');
  if (!signature) {
    return NextResponse.json({ error: 'missing_signature' }, { status: 400 });
  }

  let event: Stripe.Event;
  try {
    const stripe = getStripeClient();
    const raw = await req.text();
    event = stripe.webhooks.constructEvent(raw, signature, secret);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'invalid_payload';
    kaizenObserve('billing', 'webhook_rejected', message, { fix: 'verify_stripe_signature' });
    return NextResponse.json({ error: message }, { status: 400 });
  }

  kaizenObserve('billing', 'webhook_received', `Stripe event ${event.type}`);

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;
        await activateFromCheckoutSession(session);
        break;
      }
      case 'customer.subscription.updated':
      case 'customer.subscription.deleted': {
        const sub = event.data.object as Stripe.Subscription;
        await syncFromSubscription(sub);
        break;
      }
      default:
        kaizenObserve('billing', 'webhook_ignored', `Unhandled type ${event.type}`);
    }
    return NextResponse.json({ received: true });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'webhook_handler_failed';
    kaizenObserve('billing', 'webhook_error', message, { fix: 'inspect_handler' });
    return NextResponse.json({ error: message }, { status: 500 });
  }
}