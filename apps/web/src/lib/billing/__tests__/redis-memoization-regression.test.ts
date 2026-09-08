import { afterEach, describe, expect, it, vi } from 'vitest';
import { checkFreeChatQuota, resetChatQuotaForTests } from '../chat-quota';

const redisCtor = vi.fn();
const incrMock = vi.fn(async () => 1);
const expireMock = vi.fn(async () => 1);

vi.mock('@upstash/redis', () => ({
  Redis: class {
    constructor(config: unknown) {
      redisCtor(config);
    }

    async incr() {
      return incrMock();
    }

    async expire() {
      return expireMock();
    }
  },
}));

afterEach(() => {
  vi.unstubAllEnvs();
  vi.clearAllMocks();
  resetChatQuotaForTests();
});

describe('redis lazy memoization', () => {
  it('creates only one Redis client while concurrent quota checks share the same promise', async () => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://example.upstash.io');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'test-token');

    const [first, second] = await Promise.all([
      checkFreeChatQuota('demo', 10),
      checkFreeChatQuota('demo', 10),
    ]);

    expect(redisCtor).toHaveBeenCalledTimes(1);
    expect(first.allowed).toBe(true);
    expect(second.allowed).toBe(true);
    expect(incrMock).toHaveBeenCalledTimes(2);
  });
});
