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

function apiRequest(path: string, method = 'GET'): NextRequest {
  return new NextRequest(`http://localhost:3000${path}`, {
    method,
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

  it('fails CLOSED with 503 for AI routes (POST /api/chat) — denial-of-wallet protection', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/chat', 'POST'));

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe('rate_limit_unavailable');
  });

  it('fails CLOSED with 503 for POST /api/agents/actions (LLM route, not just dispatch)', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/agents/actions', 'POST'));

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe('rate_limit_unavailable');
  });

  it('fails CLOSED for paid AI GET endpoints (GET /api/video/search runs an embedding)', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    // A handful of AI GETs are themselves paid calls (Gemini embedding here),
    // so they fail closed even though they are reads — a blanket "GETs are
    // cheap" rule would leak these during a Redis outage.
    const res = await proxy(apiRequest('/api/video/search?videoId=x&q=y', 'GET'));

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe('rate_limit_unavailable');
  });

  it('fails CLOSED for GET /api/realtime/session (mints a paid OpenAI Realtime secret)', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    const res = await proxy(apiRequest('/api/realtime/session', 'GET'));

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe('rate_limit_unavailable');
  });

  it('fails OPEN for cheap AI status/health GETs so a Redis outage cannot 503 them', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    // These are AI-prefixed but incur NO paid AI call — pure status/health/info
    // reads (the full CHEAP_AI_GET_ROUTES allowlist) — so they must stay
    // available during a limiter outage.
    for (const path of [
      '/api/agents/actions',
      '/api/agents/dispatch',
      '/api/pipeline',
      '/api/training/status',
      '/api/video',
    ]) {
      const res = await proxy(apiRequest(path, 'GET'));
      expect(res.status, `${path} should fail open`).not.toBe(503);
      expect(res.status, `${path} should fail open`).not.toBe(429);
    }
  });

  it('fails CLOSED for an unclassified AI GET (safe default — not on the cheap allowlist)', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    clearRedisEnv();

    const proxy = await loadProxy();
    // An AI-prefixed GET that is NOT an explicitly verified cheap read must fail
    // closed by default, so a newly added billable AI read can't silently bypass
    // denial-of-wallet protection just because nobody updated an allowlist.
    // `/api/transcribe/status` sits under the AI `/api/transcribe` prefix and is
    // not in CHEAP_AI_GET_ROUTES.
    const res = await proxy(apiRequest('/api/transcribe/status', 'GET'));

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe('rate_limit_unavailable');
  });

  it('fails OPEN for non-AI GET routes (e.g. /api/agents/status)', async () => {
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
    const res = await proxy(apiRequest('/api/chat', 'POST'));

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
