import type { Redis } from '@upstash/redis';
import {
  readEntitlementFromFile,
  writeEntitlementToFile,
  resetEntitlementFileStoreForTests,
} from './entitlement-file-store';
import { resolveUpstashRedisCredentials } from './redis-credentials';

export type PlanTier = 'free' | 'pro';

export type EntitlementRecord = {
  email: string;
  plan: PlanTier;
  status: 'active' | 'trialing' | 'canceled' | 'past_due' | 'inactive';
  stripeCustomerId?: string;
  stripeSubscriptionId?: string;
  leadModel: string;
  updatedAt: string;
};

const memoryStore = new Map<string, EntitlementRecord>();

let redisPromise: Promise<Redis | null> | null = null;

export function assertEntitlementDurability(): void {
  if (process.env.NODE_ENV !== 'production') return;
  if (resolveUpstashRedisCredentials()) {
    return;
  }
  throw new Error(
    'Durable entitlement storage is not configured in production. Set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN (or the KV_REST_API_URL + KV_REST_API_TOKEN provided by the Vercel Upstash integration) for cross-instance entitlement durability',
  );
}

async function getRedis(): Promise<Redis | null> {
  if (redisPromise) return redisPromise;
  redisPromise = (async () => {
    const creds = resolveUpstashRedisCredentials();
    if (!creds) {
      return null;
    }
    try {
      const { Redis } = await import('@upstash/redis');
      return new Redis({
        url: creds.url,
        token: creds.token,
      });
    } catch {
      return null;
    }
  })();
  return redisPromise;
}

export function normalizeBillingEmail(email: string): string {
  return email.trim().toLowerCase();
}

function entitlementKey(email: string): string {
  return `er:entitlement:${normalizeBillingEmail(email)}`;
}

export async function getEntitlement(email: string): Promise<EntitlementRecord | null> {
  const normalized = normalizeBillingEmail(email);
  const redis = await getRedis();
  if (redis) {
    try {
      const raw = await redis.get<EntitlementRecord>(entitlementKey(normalized));
      if (raw) return raw;
    } catch {
      // fall through
    }
  }

  const fromFile = await readEntitlementFromFile(normalized);
  if (fromFile) {
    memoryStore.set(normalized, fromFile);
    return fromFile;
  }

  return memoryStore.get(normalized) ?? null;
}

export async function saveEntitlement(record: EntitlementRecord): Promise<EntitlementRecord> {
  assertEntitlementDurability();
  const normalized = normalizeBillingEmail(record.email);
  const stored: EntitlementRecord = {
    ...record,
    email: normalized,
    updatedAt: new Date().toISOString(),
  };
  memoryStore.set(normalized, stored);

  await writeEntitlementToFile(stored);

  const redis = await getRedis();
  if (redis) {
    try {
      await redis.set(entitlementKey(normalized), stored);
    } catch {
      // file + memory remain durable for this host
    }
  }
  return stored;
}

export async function isProSubscriber(email: string | undefined | null): Promise<boolean> {
  if (!email?.trim()) return false;
  const ent = await getEntitlement(email);
  return ent?.plan === 'pro' && (ent.status === 'active' || ent.status === 'trialing');
}

export function resetEntitlementStoreForTests(): void {
  memoryStore.clear();
  redisPromise = null;
  resetEntitlementFileStoreForTests();
}
