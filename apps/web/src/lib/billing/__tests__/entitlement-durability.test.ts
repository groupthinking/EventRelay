import { beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * Regression suite for audit finding **F5**.
 *
 * `saveEntitlement()` awaited `writeEntitlementToFile()` *before* writing to
 * Redis, and that await was not wrapped. On Vercel the deployment bundle is
 * mounted read-only, so `mkdir(process.cwd()/.data)` rejects with EROFS —
 * which means the function threw before ever reaching the durable Redis write.
 *
 * The blast radius is billing: the Stripe webhook calls `saveEntitlement()` to
 * record a successful subscription. A throw there means the customer is charged
 * by Stripe while the app never records them as Pro.
 *
 * The local JSON file is a dev convenience. Redis is the durable store, so a
 * filesystem failure must never prevent the Redis write.
 */

const setSpy = vi.fn().mockResolvedValue('OK');
const getSpy = vi.fn().mockResolvedValue(null);

vi.mock('@upstash/redis', () => ({
  Redis: class {
    get = getSpy;
    set = setSpy;
  },
}));

// Simulates Vercel's read-only filesystem.
const EROFS = Object.assign(new Error("EROFS: read-only file system, mkdir '/var/task/.data'"), {
  code: 'EROFS',
});

vi.mock('../entitlement-file-store', () => ({
  readEntitlementFromFile: vi.fn().mockResolvedValue(null),
  writeEntitlementToFile: vi.fn().mockRejectedValue(EROFS),
  resetEntitlementFileStoreForTests: vi.fn(),
}));

describe('saveEntitlement — F5 durability regression', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    getSpy.mockResolvedValue(null);
    setSpy.mockResolvedValue('OK');
    // Credentials for the durable store. KV_REST_API_* is what the Vercel
    // Upstash integration provides, and what this project actually sets.
    vi.stubEnv('KV_REST_API_URL', 'https://kv.test.upstash.io');
    vi.stubEnv('KV_REST_API_TOKEN', 'test-token');
    const { resetEntitlementStoreForTests } = await import('../entitlement-store');
    resetEntitlementStoreForTests();
  });

  it('persists to Redis even when the filesystem write fails', async () => {
    const { saveEntitlement } = await import('../entitlement-store');

    const record = await saveEntitlement({
      email: 'Customer@Example.com',
      plan: 'pro',
      status: 'active',
      stripeCustomerId: 'cus_123',
      stripeSubscriptionId: 'sub_123',
      leadModel: 'grok-4',
      updatedAt: new Date().toISOString(),
    });

    // The durable write is the whole point: a read-only filesystem must not
    // stop a paying customer from being recorded as Pro.
    expect(setSpy).toHaveBeenCalledTimes(1);
    expect(setSpy.mock.calls[0][0]).toBe('er:entitlement:customer@example.com');
    expect(record.plan).toBe('pro');
    expect(record.email).toBe('customer@example.com');
  });

  it('reports the subscriber as Pro after a filesystem failure', async () => {
    const { saveEntitlement, isProSubscriber } = await import('../entitlement-store');

    await saveEntitlement({
      email: 'paid@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4',
      updatedAt: new Date().toISOString(),
    });

    // Redis returns what was stored; the in-memory fallback also holds it.
    getSpy.mockResolvedValue({
      email: 'paid@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4',
      updatedAt: new Date().toISOString(),
    });

    await expect(isProSubscriber('paid@example.com')).resolves.toBe(true);
  });

  it('still surfaces a hard failure when the durable store itself fails', async () => {
    // The inverse guard: filesystem errors are tolerable, but losing the
    // durable write must not be silent.
    setSpy.mockRejectedValue(new Error('upstash unavailable'));
    const { saveEntitlement } = await import('../entitlement-store');

    await expect(
      saveEntitlement({
        email: 'unlucky@example.com',
        plan: 'pro',
        status: 'active',
        leadModel: 'grok-4',
        updatedAt: new Date().toISOString(),
      }),
    ).rejects.toThrow(/durable|upstash/i);
  });
});
