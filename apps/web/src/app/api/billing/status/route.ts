import { NextRequest, NextResponse } from 'next/server';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { getEntitlement, isProSubscriber } from '@/lib/billing/entitlement-store';
import { isChatPaywallBypassed } from '@/lib/billing/paywall-bypass';
import { resolvePaidTierRouting, PRO_FEATURES, FREE_CHAT_DAILY_LIMIT } from '@/lib/billing/paid-tier-model';

const FREE_FEATURES = {
  unlimitedChat: false,
  agentDispatch: false,
  apiAccess: false,
  chatDailyLimit: FREE_CHAT_DAILY_LIMIT,
  workspaceZipExport: false,
  refineryDatasetAccess: false,
} as const;

export async function GET(req: NextRequest) {
  const email = await resolveTrustedBillingEmail(req);

  if (!email) {
    return NextResponse.json({
      plan: 'free',
      status: 'inactive',
      email: null,
      features: FREE_FEATURES,
      routing: resolvePaidTierRouting(false),
      renewalEligible: false,
      paywallBypass: false,
    });
  }

  const entitlement = await getEntitlement(email);
  const storedPro = await isProSubscriber(email);
  const paywallBypass = !storedPro && isChatPaywallBypassed(email);
  const chatUnlocked = storedPro || paywallBypass;
  const routing = resolvePaidTierRouting(chatUnlocked);
  const storedStatus = entitlement?.status;
  const reportedStatus = chatUnlocked
    ? (storedStatus === 'active' || storedStatus === 'trialing' ? storedStatus : 'active')
    : (storedStatus ?? 'inactive');

  return NextResponse.json({
    plan: chatUnlocked ? 'pro' : (entitlement?.plan ?? 'free'),
    status: reportedStatus,
    email,
    stripeCustomerId: entitlement?.stripeCustomerId ?? null,
    stripeSubscriptionId: entitlement?.stripeSubscriptionId ?? null,
    features: storedPro
      ? { ...PRO_FEATURES, chatDailyLimit: null, leadModel: routing.model }
      : paywallBypass
        ? {
            unlimitedChat: true,
            agentDispatch: false,
            apiAccess: false,
            chatDailyLimit: null,
            workspaceZipExport: false,
            refineryDatasetAccess: false,
            leadModel: routing.model,
          }
        : FREE_FEATURES,
    routing,
    renewalEligible: Boolean(entitlement?.stripeCustomerId || email),
    paywallBypass,
  });
}