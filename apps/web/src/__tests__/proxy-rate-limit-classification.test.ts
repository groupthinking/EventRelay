import { afterEach, describe, expect, it, vi } from 'vitest';

/**
 * Rate-limit route classification (PR #1507 review — VADE "logic" finding).
 *
 * The durable video-to-actions workflow polls GET
 * /api/workflows/video-to-actions/:runId every ~1.5s (studio-workflow.ts).
 * When that poll is classified as an "AI route" it draws from the strict
 * 12/min AI budget, so the client poller is 429'd mid-run and the UI hangs on
 * "still running". Only the mutating start (POST /api/workflows/...) does real
 * AI work and should be AI-limited; the status poll belongs on the general
 * budget.
 *
 * proxy.ts reads limits + env into module-level constants, so each case
 * re-imports the module after stubbing env (mirrors proxy-auth-gate.test.ts).
 * The applied budget is read off the X-RateLimit-Limit response header.
 */

vi.mock('next-auth/jwt', () => ({
  getToken: vi.fn(async () => null),
}));

// NODE_ENV=development => auth gate disabled + in-memory limiter (emits headers).
// All limit/redis knobs are pinned so the result never depends on ambient env.
const ENV: Record<string, string | undefined> = {
  NODE_ENV: 'development',
  NEXTAUTH_SECRET: undefined,
  INTERNAL_REQUEST_TOKEN: undefined,
  UPSTASH_REDIS_REST_URL: undefined,
  UPSTASH_REDIS_REST_TOKEN: undefined,
  UVAI_RATE_LIMIT_DISABLED: undefined,
  UVAI_API_RATE_LIMIT_PER_MINUTE: undefined, // default GENERAL_LIMIT = 60
  UVAI_AI_RATE_LIMIT_PER_MINUTE: undefined, // default AI_LIMIT = 12
};

const GENERAL = '60';
const AI = '12';

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function loadProxy() {
  for (const [key, value] of Object.entries(ENV)) {
    vi.stubEnv(key, value);
  }
  vi.resetModules();
  const { NextRequest } = await import('next/server');
  const { proxy } = await import('@/proxy');
  return { proxy, NextRequest };
}

describe('rate-limit classification for /api/workflows (PR #1507)', () => {
  it('puts the workflow status poll (GET) on the general budget, not the AI budget', async () => {
    const { proxy, NextRequest } = await loadProxy();
    const res = await proxy(
      new NextRequest(
        'http://localhost:3000/api/workflows/video-to-actions/run_abc123',
        { method: 'GET' },
      ),
    );
    // The bug: before the fix this header reads "12" and the poller 429s mid-run.
    expect(res.headers.get('X-RateLimit-Limit')).toBe(GENERAL);
  });

  it('keeps the workflow start (POST) on the strict AI budget', async () => {
    const { proxy, NextRequest } = await loadProxy();
    const res = await proxy(
      new NextRequest('http://localhost:3000/api/workflows/video-to-actions', {
        method: 'POST',
      }),
    );
    expect(res.headers.get('X-RateLimit-Limit')).toBe(AI);
  });

  it('leaves other AI routes on the AI budget regardless of method', async () => {
    const { proxy, NextRequest } = await loadProxy();
    const res = await proxy(
      new NextRequest('http://localhost:3000/api/chat', { method: 'POST' }),
    );
    expect(res.headers.get('X-RateLimit-Limit')).toBe(AI);
  });

  it('keeps ordinary API routes on the general budget', async () => {
    const { proxy, NextRequest } = await loadProxy();
    const res = await proxy(
      new NextRequest('http://localhost:3000/api/health', { method: 'GET' }),
    );
    expect(res.headers.get('X-RateLimit-Limit')).toBe(GENERAL);
  });
});
