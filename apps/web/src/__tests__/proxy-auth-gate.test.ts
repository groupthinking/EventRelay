import { afterEach, describe, expect, it, vi } from 'vitest';

/**
 * Regression guard for issue #1058 — the login gate must not fail *open*.
 *
 * `proxy.ts` reads NEXTAUTH_SECRET into a module-level constant, so every case
 * here re-imports the module with `vi.resetModules()` after mutating the env.
 *
 * getToken() is stubbed to return null (= "no valid session"). That is the
 * interesting case: an anonymous request. What we assert is what the middleware
 * does with it under each configuration.
 */

vi.mock('next-auth/jwt', () => ({
  getToken: vi.fn(async () => null),
}));

vi.mock('redis', () => ({
  createClient: vi.fn(() => ({
    on: vi.fn(),
    connect: vi.fn(async () => undefined),
    incr: vi.fn(async () => 1),
    expire: vi.fn(async () => 1),
  })),
}));

const ENV_KEYS = [
  'NEXTAUTH_SECRET',
  'NODE_ENV',
  'INTERNAL_REQUEST_TOKEN',
  'AUTH_ALLOW_UNAUTHENTICATED',
  'UPSTASH_REDIS_REST_URL',
  'UPSTASH_REDIS_REST_TOKEN',
  'STORAGE_REDIS_URL',
  'UVAI_RATE_LIMIT_DISABLED',
] as const;

type EnvKey = (typeof ENV_KEYS)[number];

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function loadProxy(env: Partial<Record<EnvKey, string | undefined>>) {
  // Every key is stubbed on every call — including the ones a case does not
  // name — so the result never depends on the developer's ambient shell env.
  // vi.stubEnv is used instead of direct assignment because Next.js augments
  // NODE_ENV as a read-only property.
  for (const key of ENV_KEYS) {
    vi.stubEnv(key, env[key]);
  }
  vi.resetModules();
  const { NextRequest } = await import('next/server');
  const { proxy } = await import('@/proxy');
  return { proxy, NextRequest };
}

describe('login gate must fail closed (issue #1058)', () => {
  it('folds /dashboard into the public studio when NEXTAUTH_SECRET is missing in production', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: undefined,
      NODE_ENV: 'production',
      AUTH_ALLOW_UNAUTHENTICATED: undefined,
    });

    const response = await proxy(new NextRequest('https://app.example.com/dashboard'));

    // Retired skin: fold into the public studio instead of 503 or login.
    expect(response.status).toBe(308);
    expect(response.headers.get('location')).toBe('https://app.example.com/');
  });

  it('does not serve a protected API route unauthenticated when NEXTAUTH_SECRET is missing in production', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: undefined,
      NODE_ENV: 'production',
      AUTH_ALLOW_UNAUTHENTICATED: undefined,
    });

    const response = await proxy(new NextRequest('https://app.example.com/api/agents/dispatch'));

    expect(response.headers.get('x-middleware-next')).not.toBe('1');
    expect(response.status).toBe(503);
  });

  it('still enforces the normal 401/redirect gate when the secret IS configured', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: 'test-secret',
      NODE_ENV: 'production',
      AUTH_ALLOW_UNAUTHENTICATED: undefined,
    });

    const api = await proxy(new NextRequest('https://app.example.com/api/agents/dispatch'));
    expect(api.status).toBe(401);

    const page = await proxy(new NextRequest('https://app.example.com/dashboard?video=https://www.youtube.com/watch?v=auJzb1D-fag'));
    expect(page.status).toBe(308);
    expect(page.headers.get('location')).toBe(
      'https://app.example.com/?video=https://www.youtube.com/watch?v=auJzb1D-fag',
    );
  });

  it('keeps public auth routes reachable while the app is misconfigured', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: undefined,
      NODE_ENV: 'production',
      AUTH_ALLOW_UNAUTHENTICATED: undefined,
    });

    // NextAuth's own endpoints must stay reachable, otherwise an operator can
    // never complete the OAuth setup that fixes the misconfiguration.
    const response = await proxy(new NextRequest('https://app.example.com/api/auth/session'));
    expect(response.status).not.toBe(503);
  });

  it('allows an explicit, deliberate opt-out to keep the app public', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: undefined,
      NODE_ENV: 'production',
      AUTH_ALLOW_UNAUTHENTICATED: '1',
    });

    const response = await proxy(new NextRequest('https://app.example.com/dashboard'));
    expect(response.status).toBe(308);
    expect(response.headers.get('location')).toBe('https://app.example.com/');
  });

  it('lets public Studio Act on findings through when the secret IS configured', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: 'test-secret',
      NODE_ENV: 'development',
      AUTH_ALLOW_UNAUTHENTICATED: undefined,
    });

    const start = await proxy(
      new NextRequest('https://app.example.com/api/workflows/video-to-actions', {
        method: 'POST',
      }),
    );
    expect(start.status).not.toBe(401);
    expect(start.status).not.toBe(503);

    const poll = await proxy(
      new NextRequest('https://app.example.com/api/workflows/video-to-actions/run_1'),
    );
    expect(poll.status).not.toBe(401);
    expect(poll.status).not.toBe(503);

    // Sibling workflow surfaces stay gated — WDK C deploy must not inherit this.
    const other = await proxy(
      new NextRequest('https://app.example.com/api/workflows/studio-deploy', {
        method: 'POST',
      }),
    );
    expect(other.status).toBe(401);
  });

  it('fails paid AI starts closed in production when distributed limiting is unavailable', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: undefined,
      NODE_ENV: 'production',
      AUTH_ALLOW_UNAUTHENTICATED: '1',
      UPSTASH_REDIS_REST_URL: undefined,
      UPSTASH_REDIS_REST_TOKEN: undefined,
      STORAGE_REDIS_URL: undefined,
    });

    const response = await proxy(
      new NextRequest('https://app.example.com/api/workflows/video-to-actions', {
        method: 'POST',
      }),
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual(
      expect.objectContaining({ error: expect.stringContaining('rate limiting') }),
    );
  });

  it('uses the Vercel Storage Redis binding for paid AI starts', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: undefined,
      NODE_ENV: 'production',
      AUTH_ALLOW_UNAUTHENTICATED: '1',
      UPSTASH_REDIS_REST_URL: undefined,
      UPSTASH_REDIS_REST_TOKEN: undefined,
      STORAGE_REDIS_URL: 'redis://example.test:6379',
    });

    const response = await proxy(
      new NextRequest('https://app.example.com/api/workflows/video-to-actions', {
        method: 'POST',
      }),
    );

    expect(response.status).not.toBe(503);
    expect(response.headers.get('x-ratelimit-limit')).toBe('12');
  });

  it('leaves local development unchanged (no secret, no 503)', async () => {
    const { proxy, NextRequest } = await loadProxy({
      NEXTAUTH_SECRET: undefined,
      NODE_ENV: 'development',
      AUTH_ALLOW_UNAUTHENTICATED: undefined,
    });

    const response = await proxy(new NextRequest('http://localhost:3000/dashboard'));
    expect(response.status).toBe(308);
    expect(response.headers.get('location')).toBe('http://localhost:3000/');
  });
});
