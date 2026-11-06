import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  restConstructor: vi.fn(),
  tcpConstructor: vi.fn(),
  incr: vi.fn(),
  expire: vi.fn(),
  connect: vi.fn(),
}));

vi.mock('@upstash/redis', () => ({
  Redis: class {
    constructor(options: unknown) { mocks.restConstructor(options); }
    incr = mocks.incr;
    expire = mocks.expire;
  },
}));
vi.mock('redis', () => ({
  createClient: (options: unknown) => {
    mocks.tcpConstructor(options);
    return { on: vi.fn(), connect: mocks.connect, incr: mocks.incr, expire: mocks.expire };
  },
}));
vi.mock('@/lib/auth-jwt', () => ({ getNextAuthJwtFromRequest: vi.fn() }));

const kv = { KV_REST_API_URL: 'https://kv.example.test', KV_REST_API_TOKEN: 'offline-kv-token' };
const upstash = { UPSTASH_REDIS_REST_URL: 'https://upstash.example.test', UPSTASH_REDIS_REST_TOKEN: 'offline-upstash-token' };

async function loadProxy(env: Record<string, string | undefined> = {}) {
  for (const [key, value] of Object.entries(env)) vi.stubEnv(key, value);
  const { proxy } = await import('@/proxy');
  const { NextRequest } = await import('next/server');
  return (path = '/api/workflows/video-to-actions') => proxy(new NextRequest(`https://app.example.test${path}`, {
    method: 'POST', headers: { 'x-real-ip': '192.0.2.1' },
  }));
}

describe('production distributed AI rate limiting', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.resetAllMocks();
    for (const key of [
      ...Object.keys(kv), ...Object.keys(upstash), 'STORAGE_REDIS_URL',
      'NEXTAUTH_SECRET', 'INTERNAL_REQUEST_TOKEN', 'UVAI_RATE_LIMIT_DISABLED',
    ]) vi.stubEnv(key, '');
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('AUTH_ALLOW_UNAUTHENTICATED', '1');
    vi.stubEnv('UVAI_AI_RATE_LIMIT_PER_MINUTE', '12');
    vi.stubEnv('UVAI_API_RATE_LIMIT_PER_MINUTE', '60');
    mocks.incr.mockResolvedValue(1);
    mocks.expire.mockResolvedValue(1);
    mocks.connect.mockResolvedValue(undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it.each([
    ['KV', kv, { url: kv.KV_REST_API_URL, token: kv.KV_REST_API_TOKEN }],
    ['Upstash', upstash, { url: upstash.UPSTASH_REDIS_REST_URL, token: upstash.UPSTASH_REDIS_REST_TOKEN }],
  ])('admits and limits AI starts using %s REST credentials', async (_name, env, credentials) => {
    const request = await loadProxy(env);
    const admitted = await request();
    expect(admitted.status).toBe(200);
    expect(admitted.headers.get('x-middleware-next')).toBe('1');
    expect(admitted.headers.get('x-ratelimit-remaining')).toBe('11');
    expect(mocks.restConstructor).toHaveBeenCalledWith(credentials);
    expect(mocks.incr).toHaveBeenCalledWith(expect.stringMatching(/^uvai:ratelimit:ai:192\.0\.2\.1:\d+$/));
    expect(mocks.expire).toHaveBeenCalledWith(mocks.incr.mock.calls[0][0], 65);
    mocks.incr.mockResolvedValue(13);
    const limited = await request();
    expect(limited.status).toBe(429);
    expect(limited.headers.get('x-ratelimit-remaining')).toBe('0');
    expect(mocks.restConstructor).toHaveBeenCalledTimes(1);
    expect(mocks.tcpConstructor).not.toHaveBeenCalled();
  });

  it('retains Upstash precedence when both REST bindings are configured', async () => {
    const request = await loadProxy({ ...kv, ...upstash });
    expect((await request()).status).toBe(200);
    expect(mocks.restConstructor).toHaveBeenCalledWith({ url: upstash.UPSTASH_REDIS_REST_URL, token: upstash.UPSTASH_REDIS_REST_TOKEN });
  });

  it('retains TCP support when REST credentials are unavailable', async () => {
    const request = await loadProxy({ STORAGE_REDIS_URL: 'redis://redis.example.test:6379' });
    expect((await request()).status).toBe(200);
    expect(mocks.tcpConstructor).toHaveBeenCalledWith({ url: 'redis://redis.example.test:6379' });
    expect(mocks.connect).toHaveBeenCalledTimes(1);
    expect(mocks.restConstructor).not.toHaveBeenCalled();
  });

  it.each(['incr', 'expire', 'construction'] as const)('fails closed when KV %s fails', async operation => {
    const request = await loadProxy(kv);
    if (operation === 'construction') mocks.restConstructor.mockImplementation(() => { throw new Error('offline construction failure'); });
    else mocks[operation].mockRejectedValue(new Error('offline service failure'));
    const response = await request();
    expect(response.status).toBe(503);
    expect(response.headers.get('x-middleware-next')).toBeNull();
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(response.headers.get('retry-after')).toBe('60');
    expect(mocks.restConstructor).toHaveBeenCalledTimes(1);
  });

  it.each([{}, { KV_REST_API_URL: kv.KV_REST_API_URL }, { KV_REST_API_TOKEN: kv.KV_REST_API_TOKEN }])('fails closed without complete distributed credentials: %j', async env => {
    const request = await loadProxy(env);
    expect((await request()).status).toBe(503);
    expect(mocks.restConstructor).not.toHaveBeenCalled();
    expect(mocks.incr).not.toHaveBeenCalled();
  });

  it('does not allow disabling production AI enforcement', async () => {
    const request = await loadProxy({ UVAI_RATE_LIMIT_DISABLED: '1' });
    expect((await request()).status).toBe(503);
  });

  it('keeps non-AI routes available without distributed Redis', async () => {
    const request = await loadProxy();
    expect((await request('/api/example')).status).toBe(200);
  });
});
