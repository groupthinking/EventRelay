import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  resetEntitlementStoreForTests,
  saveEntitlement,
  type EntitlementRecord,
} from '../entitlement-store';

const redisSet = vi.hoisted(() => vi.fn(async (_key: string, _value: unknown) => 'OK'));

vi.mock('@upstash/redis', () => ({
  Redis: function Redis() {
    return {
      set: redisSet,
      get: vi.fn(async () => null),
    };
  },
}));

const record: EntitlementRecord = {
  email: 'Pro@Example.com',
  plan: 'pro',
  status: 'active',
  leadModel: 'grok-4-1-fast',
  updatedAt: '2026-01-01T00:00:00.000Z',
};

let tempDir = '';

beforeEach(async () => {
  resetEntitlementStoreForTests();
  redisSet.mockReset();
  redisSet.mockResolvedValue('OK');
  tempDir = await mkdtemp(path.join(tmpdir(), 'er-entitlement-store-'));
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://example.upstash.io');
  vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'test-token');
  vi.stubEnv('KV_REST_API_URL', '');
  vi.stubEnv('KV_REST_API_TOKEN', '');
  vi.stubEnv('ENTITLEMENT_STORE_PATH', path.join(tempDir, 'entitlements.json'));
});

afterEach(async () => {
  vi.unstubAllEnvs();
  resetEntitlementStoreForTests();
  if (tempDir) await rm(tempDir, { recursive: true, force: true });
});

describe('saveEntitlement', () => {
  it('calls redis.set when the file write throws', async () => {
    const blocker = path.join(tempDir, 'not-a-directory');
    await writeFile(blocker, 'blocked');
    vi.stubEnv('ENTITLEMENT_STORE_PATH', path.join(blocker, 'entitlements.json'));

    await saveEntitlement(record);

    expect(redisSet).toHaveBeenCalledTimes(1);
    expect(redisSet.mock.calls[0]?.[0]).toBe('er:entitlement:pro@example.com');
  });

  it('surfaces redis.set failures', async () => {
    redisSet.mockRejectedValue(new Error('upstash unavailable'));

    await expect(saveEntitlement(record)).rejects.toThrow('upstash unavailable');
  });
});
