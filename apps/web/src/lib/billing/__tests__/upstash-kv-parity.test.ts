import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { checkFreeChatQuota, resetChatQuotaForTests } from '../chat-quota';
import {
  getCheckoutActivation,
  linkCheckoutActivation,
  resetCheckoutSessionStoreForTests,
} from '../checkout-session-store';
import type { EntitlementRecord } from '../entitlement-store';
import { kaizenObserve, resetKaizenTracesForTests } from '../kaizen-trace';

const redisMocks = vi.hoisted(() => ({
  ctorArgs: [] as Array<{ url: string; token: string }>,
  incr: vi.fn(async () => 1),
  expire: vi.fn(async () => 1),
  set: vi.fn(async () => 'OK'),
  get: vi.fn(async () => null),
  rpush: vi.fn(async () => 1),
  ltrim: vi.fn(async () => 'OK'),
}));

vi.mock('@upstash/redis', () => ({
  Redis: function Redis(opts: { url: string; token: string }) {
    redisMocks.ctorArgs.push(opts);
    return {
      incr: redisMocks.incr,
      expire: redisMocks.expire,
      set: redisMocks.set,
      get: redisMocks.get,
      rpush: redisMocks.rpush,
      ltrim: redisMocks.ltrim,
    };
  },
}));

const sampleEntitlement: EntitlementRecord = {
  email: 'kv-user@example.com',
  plan: 'pro',
  status: 'active',
  leadModel: 'grok-4-1-fast',
  updatedAt: '2026-11-16T00:00:00.000Z',
};

describe('Upstash / Vercel KV credential parity', () => {
  beforeEach(() => {
    redisMocks.ctorArgs.length = 0;
    vi.clearAllMocks();
    resetChatQuotaForTests();
    resetCheckoutSessionStoreForTests();
    resetKaizenTracesForTests();
    vi.stubEnv('UPSTASH_REDIS_REST_URL', '');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
    vi.stubEnv('KV_REST_API_URL', 'https://kv.example.upstash.io');
    vi.stubEnv('KV_REST_API_TOKEN', 'kv-rest-token');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    resetChatQuotaForTests();
    resetCheckoutSessionStoreForTests();
    resetKaizenTracesForTests();
  });

  it('routes chat-quota through KV_REST_API_* when UPSTASH_REDIS_REST_* are unset', async () => {
    const result = await checkFreeChatQuota('subject-1', 5);
    expect(result.allowed).toBe(true);
    expect(redisMocks.incr).toHaveBeenCalledTimes(1);
    expect(redisMocks.ctorArgs).toContainEqual({
      url: 'https://kv.example.upstash.io',
      token: 'kv-rest-token',
    });
  });

  it('routes checkout-session-store through KV_REST_API_* when UPSTASH_REDIS_REST_* are unset', async () => {
    await linkCheckoutActivation('cs_kv_1', sampleEntitlement);
    await getCheckoutActivation('cs_kv_1');
    expect(redisMocks.set).toHaveBeenCalledTimes(1);
    expect(redisMocks.get).toHaveBeenCalledTimes(1);
    expect(redisMocks.ctorArgs[0]).toEqual({
      url: 'https://kv.example.upstash.io',
      token: 'kv-rest-token',
    });
  });

  it('routes kaizen-trace through KV_REST_API_* when UPSTASH_REDIS_REST_* are unset', async () => {
    vi.stubEnv('KAIZEN_TRACE_LOG', '0');
    kaizenObserve('video_pack', 'probe', 'kv parity check');
    await vi.waitFor(() => {
      expect(redisMocks.rpush).toHaveBeenCalledTimes(1);
    });
    expect(redisMocks.ltrim).toHaveBeenCalledTimes(1);
    expect(redisMocks.ctorArgs[0]).toEqual({
      url: 'https://kv.example.upstash.io',
      token: 'kv-rest-token',
    });
  });
});
