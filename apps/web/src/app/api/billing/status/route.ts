import { NextRequest, NextResponse } from 'next/server';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { getEntitlement, isProSubscriber } from '@/lib/billing/entitlement-store';
import { resolvePaidTierRouting, PRO_FEATURES, FREE_CHAT_DAILY_LIMIT } from '@/lib/billing/paid-tier-model';

export async function GET(req: NextRequest) {
  const email = await resolveTrustedBillingEmail(req);

  if (!email) {
    return NextResponse.json({
      plan: 'free',
      status: 'inactive',
      email: null,
      features: {
        unlimitedChat: false,
        agentDispatch: false,
        apiAccess: false,
        chatDailyLimit: FREE_CHAT_DAILY_LIMIT,
      },
      routing: resolvePaidTierRouting(false),
      renewalEligible: false,
    });
  }

  const entitlement = await getEntitlement(email);
  const isPro = await isProSubscriber(email);
  const routing = resolvePaidTierRouting(isPro);

  return NextResponse.json({
    plan: entitlement?.plan ?? 'free',
    status: entitlement?.status ?? 'inactive',
    email,
    stripeCustomerId: entitlement?.stripeCustomerId ?? null,
    stripeSubscriptionId: entitlement?.stripeSubscriptionId ?? null,
    features: isPro
      ? { ...PRO_FEATURES, chatDailyLimit: null, leadModel: routing.model }
      : {
          unlimitedChat: false,
          agentDispatch: false,
          apiAccess: false,
          chatDailyLimit: FREE_CHAT_DAILY_LIMIT,
        },
    routing,
    renewalEligible: Boolean(entitlement?.stripeCustomerId || email),
  });
}