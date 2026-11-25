import { createHash } from 'node:crypto';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';
import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';
import { getVideoPackRedisForServer } from '@/lib/video-pack-store';

/**
 * #2214: server-side admission for paid durable Video Pack extraction.
 *
 * Runs before a POST may claim a pack and start the direct-Gemini workflow.
 * Identity comes only from the trusted session / signed billing cookie
 * (never body or headers), entitlement only from the server entitlement
 * store, and spend is bounded by atomic per-requester and global daily
 * counters. In production the counters live in the same durable Redis as
 * the pack store, and a missing or failing store denies (fails closed).
 */

export type VideoPackPlan = 'anonymous' | 'free' | 'pro';

export type VideoPackQuotaCounts = {
  subject_used: number;
  subject_limit: number;
  global_used: number;
  global_limit: number;
};

export type VideoPackAdmission =
  | {
      allowed: true;
      plan: VideoPackPlan;
      /** sha256 prefix of the quota subject; never the raw email. */
      requester: string;
      day: string;
      quota: VideoPackQuotaCounts;
      /** Give the reserved unit back when no paid work starts. */
      release: () => Promise<void>;
    }
  | {
      allowed: false;
      plan: VideoPackPlan;
      requester: string;
      reason: 'subject_quota' | 'global_quota' | 'quota_store_unavailable';
      status: 402 | 429 | 503;
      quota?: VideoPackQuotaCounts;
    };

/** Defaults are conservative placeholders; production sets them by env. */
export const VIDEO_PACK_DAILY_LIMIT_DEFAULTS = {
  anonymous: 5,
  free: 3,
  pro: 50,
  global: 100,
} as const;

const LIMIT_ENV: Record<keyof typeof VIDEO_PACK_DAILY_LIMIT_DEFAULTS, string> = {
  anonymous: 'VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON',
  free: 'VIDEO_PACK_EXTRACT_DAILY_LIMIT_FREE',
  pro: 'VIDEO_PACK_EXTRACT_DAILY_LIMIT_PRO',
  global: 'VIDEO_PACK_EXTRACT_DAILY_LIMIT_GLOBAL',
};

/** Non-negative integer from env; anything else (NaN, negative, fractional) uses the default. */
export function resolveVideoPackDailyLimit(
  tier: keyof typeof VIDEO_PACK_DAILY_LIMIT_DEFAULTS,
): number {
  const raw = process.env[LIMIT_ENV[tier]]?.trim();
  if (raw && /^\d+$/.test(raw)) {
    const parsed = Number(raw);
    if (Number.isSafeInteger(parsed)) return parsed;
  }
  return VIDEO_PACK_DAILY_LIMIT_DEFAULTS[tier];
}

/**
 * Atomically reserve one unit on the subject and global counters.
 * Either both increment or neither does. Returns {code, subject_used, global_used}
 * where code is 'ok', 'subject' or 'global'.
 */
export const RESERVE_EXTRACTION_SCRIPT = `
local subject_limit = tonumber(ARGV[1])
local global_limit = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local subject_used = tonumber(redis.call('GET', KEYS[1]) or '0')
local global_used = tonumber(redis.call('GET', KEYS[2]) or '0')
if subject_used >= subject_limit then
  return {'subject', subject_used, global_used}
end
if global_used >= global_limit then
  return {'global', subject_used, global_used}
end
subject_used = redis.call('INCR', KEYS[1])
global_used = redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[1], ttl)
redis.call('EXPIRE', KEYS[2], ttl)
return {'ok', subject_used, global_used}
`;

export const RELEASE_EXTRACTION_SCRIPT = `
for i = 1, #KEYS do
  local v = tonumber(redis.call('GET', KEYS[i]) or '0')
  if v > 0 then redis.call('DECR', KEYS[i]) end
end
return 'ok'
`;

const QUOTA_TTL_SECONDS = 86_400 + 3_600;
const memoryCounts = new Map<string, number>();

function utcDay(now: Date): string {
  return now.toISOString().slice(0, 10);
}

function subjectDigest(subject: string): string {
  return createHash('sha256').update(subject).digest('hex').slice(0, 16);
}

function quotaKeys(subject: string, day: string): [string, string] {
  return [`er:videopack:quota:v1:${day}:${subjectDigest(subject)}`, `er:videopack:quota:v1:${day}:__global__`];
}

/** Seconds until the next UTC day, for Retry-After. */
export function secondsUntilUtcReset(now: Date = new Date()): number {
  const next = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1);
  return Math.max(1, Math.ceil((next - now.getTime()) / 1000));
}

type ReserveResult = { code: 'ok' | 'subject' | 'global'; subject_used: number; global_used: number };

async function reserve(
  keys: [string, string],
  subjectLimit: number,
  globalLimit: number,
): Promise<ReserveResult | 'unavailable'> {
  const redis = await getVideoPackRedisForServer();
  if (redis) {
    try {
      const out = await redis.eval<unknown>(RESERVE_EXTRACTION_SCRIPT, keys, [
        subjectLimit,
        globalLimit,
        QUOTA_TTL_SECONDS,
      ]);
      if (Array.isArray(out) && out.length >= 3 && ['ok', 'subject', 'global'].includes(String(out[0]))) {
        return {
          code: String(out[0]) as ReserveResult['code'],
          subject_used: Number(out[1]),
          global_used: Number(out[2]),
        };
      }
      console.error('[video-pack-admission] quota script returned an invalid result');
    } catch (error) {
      console.error('[video-pack-admission] quota reserve failed:', error instanceof Error ? error.message : error);
    }
    return 'unavailable';
  }
  if (process.env.NODE_ENV === 'production' || resolveUpstashRedisCredentials()) {
    // Production (or a configured-but-unreachable store) must not fall back to
    // per-instance memory: that would multiply the cap by instance count.
    return 'unavailable';
  }
  const subjectUsed = memoryCounts.get(keys[0]) ?? 0;
  const globalUsed = memoryCounts.get(keys[1]) ?? 0;
  if (subjectUsed >= subjectLimit) return { code: 'subject', subject_used: subjectUsed, global_used: globalUsed };
  if (globalUsed >= globalLimit) return { code: 'global', subject_used: subjectUsed, global_used: globalUsed };
  memoryCounts.set(keys[0], subjectUsed + 1);
  memoryCounts.set(keys[1], globalUsed + 1);
  return { code: 'ok', subject_used: subjectUsed + 1, global_used: globalUsed + 1 };
}

async function release(keys: [string, string]): Promise<void> {
  const redis = await getVideoPackRedisForServer();
  if (redis) {
    try {
      await redis.eval(RELEASE_EXTRACTION_SCRIPT, keys, []);
    } catch (error) {
      console.error('[video-pack-admission] quota release failed:', error instanceof Error ? error.message : error);
    }
    return;
  }
  for (const key of keys) {
    const v = memoryCounts.get(key) ?? 0;
    if (v > 0) memoryCounts.set(key, v - 1);
  }
}

/**
 * Decide whether this request may start one paid durable extraction.
 * Call only when the POST would actually claim work (cache hits stay free).
 */
export async function admitVideoPackExtraction(
  request: Request,
  now: Date = new Date(),
): Promise<VideoPackAdmission> {
  const email = await resolveTrustedBillingEmail(request);
  let isPro = false;
  if (email) {
    try {
      isPro = await isProSubscriber(email);
    } catch {
      isPro = false; // entitlement lookup failure never upgrades a requester
    }
  }
  const plan: VideoPackPlan = isPro ? 'pro' : email ? 'free' : 'anonymous';
  // Anonymous requests share one bucket: a hard cap on anonymous spend that
  // no client-controlled header (IP, forwarded-for) can multiply.
  const subject = email ? `email:${email}` : 'anonymous';
  const requester = subjectDigest(subject);
  const subjectLimit = resolveVideoPackDailyLimit(plan);
  const globalLimit = resolveVideoPackDailyLimit('global');
  const day = utcDay(now);
  const keys = quotaKeys(subject, day);

  const result = await reserve(keys, subjectLimit, globalLimit);
  if (result === 'unavailable') {
    return { allowed: false, plan, requester, reason: 'quota_store_unavailable', status: 503 };
  }
  const quota: VideoPackQuotaCounts = {
    subject_used: result.subject_used,
    subject_limit: subjectLimit,
    global_used: result.global_used,
    global_limit: globalLimit,
  };
  if (result.code === 'subject') {
    return { allowed: false, plan, requester, reason: 'subject_quota', status: plan === 'pro' ? 429 : 402, quota };
  }
  if (result.code === 'global') {
    return { allowed: false, plan, requester, reason: 'global_quota', status: 429, quota };
  }
  let released = false;
  return {
    allowed: true,
    plan,
    requester,
    day,
    quota,
    release: async () => {
      if (released) return;
      released = true;
      await release(keys);
    },
  };
}

export function resetVideoPackAdmissionForTests(): void {
  memoryCounts.clear();
}
