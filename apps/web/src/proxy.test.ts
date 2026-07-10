import { describe, it, expect, afterEach, vi } from 'vitest';
import { NextRequest } from 'next/server';

// A minimal Upstash Redis stand-in; only exercised by the "credentials picked
// up" scenario. `incr` returns 1 so the first request is always under the limit.
const incrMock = vi.fn().mockResolvedValue(1);
const expireMock = vi.fn().mockResolvedValue(1);
const redisArgs: Array<{ url: string; token: string }> = [];
vi.mock('@upstash/redis', () => ({
  Redis: class {
    incr = incrMock;
    expire = expireMock;
    constructor(cfg: { url: string; token: string }) {
      redisArgs.push(cfg);
    }
  },
}));

function apiRequest(path: string): NextRequest {
  return new NextRequest(`http://localhost:3000${path}`, {
    method: 'GET',
    headers: { 'x-real-ip': '203.0.113.5' },
  });
}

// The proxy memoizes its Redis client at module scope, so each scenario loads a
// fresh module instance (after env is stubbed) to defeat that memoization.
async function loadProxy() {
  vi.resetModules();
  return (await import('./proxy')).proxy;
}

const REDIS_ENV_KEYS = [
  'UPSTASH_REDIS_REST_URL',
  'UPSTASH_REDIS_REST_TOKEN',
  'KV_REST_API_URL',
  'KV_REST_API_TOKEN',
];

function clearRedisEnv() {
  for (const k of REDIS_ENV_KEYS) vi.stubEnv(k, '');
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.clearAllMocks();
  redisArgs.length = 0;
});

describe('proxy rate limiting — production without a working Redis limiter', () => {
  it('fails OPEN for non-AI routes so a limiter outage cannot take down the API', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/health'));

    expect(res.status).not.toBe(429);
    expect(res.status).not.toBe(503);
    // Request passed through with limiter headers attached.
    expect(res.headers.get('X-RateLimit-Limit')).toBeTruthy();
  });

  it('fails CLOSED with 503 for AI routes (denial-of-wallet protection)', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/chat'));

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe('rate_limit_unavailable');
  });

  it('fails CLOSED with 503 for /api/agents/actions (LLM route, not just dispatch)', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/agents/actions'));

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe('rate_limit_unavailable');
  });

  it('fails OPEN for the cheap /api/agents/status route', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/agents/status'));

    expect(res.status).not.toBe(503);
    expect(res.status).not.toBe(429);
  });

  it('honours UVAI_RATE_LIMIT_FAIL_OPEN=1 to fail open even for AI routes', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '1');
    clearRedisEnv();

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/chat'));

    expect(res.status).not.toBe(503);
    expect(res.status).not.toBe(429);
  });

  it('resolves KV_REST_API_* credentials (Vercel KV) for the limiter', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    clearRedisEnv();
    vi.stubEnv('KV_REST_API_URL', 'https://kv.example.upstash.io');
    vi.stubEnv('KV_REST_API_TOKEN', 'kv-token');

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/chat'));

    expect(redisArgs).toContainEqual({
      url: 'https://kv.example.upstash.io',
      token: 'kv-token',
    });
    expect(incrMock).toHaveBeenCalled();
    expect(res.status).not.toBe(503);
  });
});
