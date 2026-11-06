import { afterEach, describe, expect, it, vi } from 'vitest';
import { resolveUpstashRedisCredentials } from '../redis-credentials';

describe('Upstash credential family integrity', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('does not mix an Upstash URL with only a KV token', () => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://upstash.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
    vi.stubEnv('KV_REST_API_URL', '');
    vi.stubEnv('KV_REST_API_TOKEN', 'kv-token');
    expect(resolveUpstashRedisCredentials()).toBeNull();
  });

  it('selects a complete KV-only pair even with a partial Upstash configuration', () => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://partial.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
    vi.stubEnv('KV_REST_API_URL', 'https://kv.invalid');
    vi.stubEnv('KV_REST_API_TOKEN', 'kv-token');
    expect(resolveUpstashRedisCredentials()).toEqual({ url: 'https://kv.invalid', token: 'kv-token' });
  });

  it('prefers a complete Upstash pair when both families exist', () => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://upstash.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'upstash-token');
    vi.stubEnv('KV_REST_API_URL', 'https://kv.invalid');
    vi.stubEnv('KV_REST_API_TOKEN', 'kv-token');
    expect(resolveUpstashRedisCredentials()).toEqual({ url: 'https://upstash.invalid', token: 'upstash-token' });
  });
});
