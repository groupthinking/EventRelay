import type { EntitlementRecord } from './entitlement-store';
import { normalizeBillingEmail } from './entitlement-store';
import { createUpstashRedisClient } from './upstash-client';

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

export const CHECKOUT_ACTIVATION_TTL_SECONDS = 60 * 60 * 24;

const memoryLinks = new Map<string, CheckoutActivationLink>();

function isExpired(link: CheckoutActivationLink): boolean {
  const fulfilledAtMs = Date.parse(link.fulfilledAt);
  if (!Number.isFinite(fulfilledAtMs)) return true;
  return Date.now() - fulfilledAtMs > CHECKOUT_ACTIVATION_TTL_SECONDS * 1000;
}

function sessionKey(sessionId: string): string {
  return `er:checkout:${sessionId.trim()}`;
}

async function getRedis() {
  return createUpstashRedisClient();
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
      await redis.set(sessionKey(link.sessionId), link, {
        ex: CHECKOUT_ACTIVATION_TTL_SECONDS,
      });
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
        if (isExpired(raw)) {
          memoryLinks.delete(id);
          return null;
        }
        memoryLinks.set(id, raw);
        return raw;
      }
    } catch {
      // fall through
    }
  }
  const cached = memoryLinks.get(id);
  if (!cached) return null;
  if (isExpired(cached)) {
    memoryLinks.delete(id);
    return null;
  }
  return cached;
}

export function resetCheckoutSessionStoreForTests(): void {
  memoryLinks.clear();
}