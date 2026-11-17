import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { resolveTrustedBillingEmail, isProSubscriber } = vi.hoisted(() => ({
  resolveTrustedBillingEmail: vi.fn(async (_req: Request): Promise<string | null> => null),
  isProSubscriber: vi.fn(async (_email: string | null | undefined): Promise<boolean> => false),
}));

vi.mock('@/lib/billing/billing-context', () => ({ resolveTrustedBillingEmail }));
vi.mock('@/lib/billing/entitlement-store', () => ({ isProSubscriber }));

function req(init: RequestInit = {}) {
  return new Request('http://localhost:3000/api/video/pack', { method: 'POST', ...init });
}

async function load() {
  const store = await import('@/lib/video-pack-store');
  store.resetVideoPackStoreForTests();
  const mod = await import('@/lib/billing/video-pack-admission');
  mod.resetVideoPackAdmissionForTests();
  return { mod, store };
}

beforeEach(() => {
  resolveTrustedBillingEmail.mockReset();
  resolveTrustedBillingEmail.mockResolvedValue(null);
  isProSubscriber.mockReset();
  isProSubscriber.mockResolvedValue(false);
});

afterEach(() => {
  vi.resetModules();
  vi.unstubAllEnvs();
});

describe('admitVideoPackExtraction (#2214)', () => {
  it('meters all anonymous requests in one shared bucket and denies past the cap with 402', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '2');
    const { mod } = await load();
    const a = await mod.admitVideoPackExtraction(req({ headers: { 'x-forwarded-for': '1.1.1.1' } }));
    const b = await mod.admitVideoPackExtraction(req({ headers: { 'x-forwarded-for': '2.2.2.2' } }));
    const c = await mod.admitVideoPackExtraction(req({ headers: { 'x-forwarded-for': '3.3.3.3' } }));
    expect(a.allowed).toBe(true);
    expect(b.allowed).toBe(true);
    expect(c).toMatchObject({ allowed: false, plan: 'anonymous', reason: 'subject_quota', status: 402 });
  });

  it('never trusts a client-supplied email or plan in headers or body', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '0');
    const { mod } = await load();
    const res = await mod.admitVideoPackExtraction(
      req({
        headers: {
          'x-billing-email': 'pro@example.com',
          'x-user-plan': 'pro',
          cookie: 'er_billing_email=pro@example.com',
        },
        body: JSON.stringify({ email: 'pro@example.com', plan: 'pro' }),
      }),
    );
    expect(res).toMatchObject({ allowed: false, plan: 'anonymous' });
    expect(isProSubscriber).not.toHaveBeenCalled();
  });

  it('gives a signed-in free user a per-email quota, separate from anonymous', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_FREE', '1');
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '0');
    const { mod } = await load();
    resolveTrustedBillingEmail.mockResolvedValue('a@example.com');
    expect((await mod.admitVideoPackExtraction(req())).allowed).toBe(true);
    expect(await mod.admitVideoPackExtraction(req())).toMatchObject({ allowed: false, plan: 'free', status: 402 });
    resolveTrustedBillingEmail.mockResolvedValue('b@example.com');
    expect((await mod.admitVideoPackExtraction(req())).allowed).toBe(true);
  });

  it('uses the pro limit only when the server entitlement store says pro, and returns 429 past it', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_PRO', '1');
    const { mod } = await load();
    resolveTrustedBillingEmail.mockResolvedValue('pro@example.com');
    isProSubscriber.mockResolvedValue(true);
    expect(await mod.admitVideoPackExtraction(req())).toMatchObject({ allowed: true, plan: 'pro' });
    expect(await mod.admitVideoPackExtraction(req())).toMatchObject({ allowed: false, plan: 'pro', status: 429 });
  });

  it('treats an entitlement lookup failure as not pro', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_FREE', '0');
    const { mod } = await load();
    resolveTrustedBillingEmail.mockResolvedValue('x@example.com');
    isProSubscriber.mockRejectedValue(new Error('store down'));
    expect(await mod.admitVideoPackExtraction(req())).toMatchObject({ allowed: false, plan: 'free' });
  });

  it('enforces a global daily cap across every requester', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_GLOBAL', '2');
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_PRO', '100');
    const { mod } = await load();
    resolveTrustedBillingEmail.mockResolvedValue('pro@example.com');
    isProSubscriber.mockResolvedValue(true);
    await mod.admitVideoPackExtraction(req());
    await mod.admitVideoPackExtraction(req());
    expect(await mod.admitVideoPackExtraction(req())).toMatchObject({ allowed: false, reason: 'global_quota', status: 429 });
  });

  it('does not consume the subject quota when the global cap denies', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_GLOBAL', '1');
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_FREE', '1');
    const { mod } = await load();
    expect((await mod.admitVideoPackExtraction(req())).allowed).toBe(true); // anonymous takes the global unit
    resolveTrustedBillingEmail.mockResolvedValue('f@example.com');
    const denied = await mod.admitVideoPackExtraction(req());
    expect(denied).toMatchObject({ allowed: false, reason: 'global_quota' });
    if (!denied.allowed) expect(denied.quota?.subject_used).toBe(0);
  });

  it('release() returns the reserved unit exactly once', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '1');
    const { mod } = await load();
    const first = await mod.admitVideoPackExtraction(req());
    expect(first.allowed).toBe(true);
    if (first.allowed) {
      await first.release();
      await first.release();
    }
    expect((await mod.admitVideoPackExtraction(req())).allowed).toBe(true);
    expect((await mod.admitVideoPackExtraction(req())).allowed).toBe(false);
  });

  it.each(['NaN', '-1', '1.5', 'Infinity', 'abc', ''])('falls back to the default for invalid limit %j', async (raw) => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', raw);
    const { mod } = await load();
    expect(mod.resolveVideoPackDailyLimit('anonymous')).toBe(mod.VIDEO_PACK_DAILY_LIMIT_DEFAULTS.anonymous);
  });

  it('fails closed in production when no durable quota store exists (no memory fallback)', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UPSTASH_REDIS_REST_URL', '');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
    vi.stubEnv('KV_REST_API_URL', '');
    vi.stubEnv('KV_REST_API_TOKEN', '');
    const { mod } = await load();
    expect(await mod.admitVideoPackExtraction(req())).toMatchObject({
      allowed: false,
      reason: 'quota_store_unavailable',
      status: 503,
    });
  });

  it('fails closed when the Redis quota script errors', async () => {
    const { mod, store } = await load();
    store.setVideoPackRedisForTests({
      get: async () => null,
      set: async () => 'OK',
      eval: async () => {
        throw new Error('redis down');
      },
    });
    expect(await mod.admitVideoPackExtraction(req())).toMatchObject({ allowed: false, reason: 'quota_store_unavailable' });
  });

  it('passes subject + global keys and limits to the atomic Redis script', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '7');
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_GLOBAL', '9');
    const { mod, store } = await load();
    const calls: Array<{ keys: string[]; args: Array<string | number> }> = [];
    store.setVideoPackRedisForTests({
      get: async () => null,
      set: async () => 'OK',
      eval: async <T>(_script: string, keys: string[], args: Array<string | number>) => {
        calls.push({ keys, args });
        return ['ok', 1, 1] as unknown as T;
      },
    });
    const res = await mod.admitVideoPackExtraction(req(), new Date('2026-11-09T05:00:00Z'));
    expect(res.allowed).toBe(true);
    expect(calls[0].keys).toHaveLength(2);
    expect(calls[0].keys[0]).toMatch(/^er:videopack:quota:v1:2026-11-09:[a-f0-9]{16}$/);
    expect(calls[0].keys[1]).toBe('er:videopack:quota:v1:2026-11-09:__global__');
    expect(calls[0].args.slice(0, 2)).toEqual([7, 9]);
    expect(JSON.stringify(calls)).not.toContain('@');
  });
});
