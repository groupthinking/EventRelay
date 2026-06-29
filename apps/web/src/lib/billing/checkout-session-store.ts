import type { EntitlementRecord } from './entitlement-store';
import { normalizeBillingEmail } from './entitlement-store';

export type CheckoutActivationLink = {
  sessionId: string;
  email: string;
  plan: EntitlementRecord['plan'];
  status: EntitlementRecord['status'];
  stripeCustomerId?: string;
  stripeSubscriptionId?: string;
  leadModel: string;
  fulfilledAt: string;
};

const memoryLinks = new Map<string, CheckoutActivationLink>();

function sessionKey(sessionId: string): string {
  return `er:checkout:${sessionId.trim()}`;
}

async function getRedis() {
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return null;
  }
  try {
    const { Redis } = await import('@upstash/redis');
    return new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL,
      token: process.env.UPSTASH_REDIS_REST_TOKEN,
    });
  } catch {
    return null;
  }
}

function linkFromEntitlement(
  sessionId: string,
  record: EntitlementRecord,
): CheckoutActivationLink {
  return {
    sessionId: sessionId.trim(),
    email: normalizeBillingEmail(record.email),
    plan: record.plan,
    status: record.status,
    stripeCustomerId: record.stripeCustomerId,
    stripeSubscriptionId: record.stripeSubscriptionId,
    leadModel: record.leadModel,
    fulfilledAt: new Date().toISOString(),
  };
}

export async function linkCheckoutActivation(
  sessionId: string,
  record: EntitlementRecord,
): Promise<CheckoutActivationLink> {
  const link = linkFromEntitlement(sessionId, record);
  memoryLinks.set(link.sessionId, link);

  const redis = await getRedis();
  if (redis) {
    try {
      await redis.set(sessionKey(link.sessionId), link);
    } catch {
      // memory link remains for this instance
    }
  }

  return link;
}

export async function getCheckoutActivation(
  sessionId: string,
): Promise<CheckoutActivationLink | null> {
  const id = sessionId.trim();
  const redis = await getRedis();
  if (redis) {
    try {
      const raw = await redis.get<CheckoutActivationLink>(sessionKey(id));
      if (raw) {
        memoryLinks.set(id, raw);
        return raw;
      }
    } catch {
      // fall through
    }
  }
  return memoryLinks.get(id) ?? null;
}

export function resetCheckoutSessionStoreForTests(): void {
  memoryLinks.clear();
}