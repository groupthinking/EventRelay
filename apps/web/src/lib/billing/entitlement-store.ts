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

  // Durable write FIRST, and never swallowed.
  //
  // This used to run *after* an unguarded `await writeEntitlementToFile()`.
  // On Vercel the bundle is mounted read-only, so that filesystem write
  // rejected with EROFS and threw straight out of this function — before the
  // Redis write ran. The Stripe webhook calls this to record a completed
  // subscription, so the customer was charged while the app never recorded
  // them as Pro (audit finding F5).
  //
  // A failure of the durable store is also no longer swallowed:
  // `assertEntitlementDurability()` above promises durability in production,
  // so silently dropping the write would break that promise and leave the
  // record only in this instance's memory.
  const redis = await getRedis();
  if (redis) {
    try {
      await redis.set(entitlementKey(normalized), stored);
    } catch (error) {
      throw new Error(
        `Failed to persist entitlement for ${normalized} to the durable store: ${
          error instanceof Error ? error.message : String(error)
        }`,
        { cause: error },
      );
    }
  }

  // Local JSON mirror — a development convenience for hosts without Redis.
  // Best-effort by design: on a read-only filesystem this always fails, and
  // that must not undo the durable write above.
  try {
    await writeEntitlementToFile(stored);
  } catch (error) {
    const code = (error as { code?: string } | null)?.code;
    // EROFS/EACCES on serverless hosts is expected, not actionable.
    if (code !== 'EROFS' && code !== 'EACCES' && code !== 'EPERM') {
      console.warn('[Billing] Local entitlement mirror write failed (non-fatal):', error);
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
