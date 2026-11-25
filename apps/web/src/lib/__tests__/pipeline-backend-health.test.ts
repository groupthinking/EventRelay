import { describe, it, expect, afterEach, vi } from 'vitest';
import {
  checkBackendHealth,
  getBackendConfig,
  parseBackendJson,
} from '@/lib/pipeline-backend-health';

const BACKEND_ENV_KEYS = [
  'BACKEND_URL',
  'NEXT_PUBLIC_BACKEND_URL',
  'NEXT_PUBLIC_API_URL',
] as const;

function snapshotBackendEnv(): Record<(typeof BACKEND_ENV_KEYS)[number], string | undefined> {
  return {
    BACKEND_URL: process.env.BACKEND_URL,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  };
}

function restoreBackendEnv(
  snapshot: Record<(typeof BACKEND_ENV_KEYS)[number], string | undefined>,
): void {
  for (const key of BACKEND_ENV_KEYS) {
    if (snapshot[key] === undefined) delete process.env[key];
    else process.env[key] = snapshot[key];
  }
}

function clearBackendEnv(): void {
  for (const key of BACKEND_ENV_KEYS) {
    delete process.env[key];
  }
}

describe('getBackendConfig', () => {
  const original = snapshotBackendEnv();

  afterEach(() => {
    restoreBackendEnv(original);
    vi.unstubAllGlobals();
  });

  it('reports unconfigured when every documented backend env name is empty', () => {
    clearBackendEnv();
    expect(getBackendConfig()).toEqual({ configured: false, url: '' });
  });

  it('normalizes configured backend URL', () => {
    clearBackendEnv();
    process.env.BACKEND_URL = 'https://api.uvai.io/';
    expect(getBackendConfig()).toEqual({
      configured: true,
      url: 'https://api.uvai.io',
    });
  });

  it('falls back to NEXT_PUBLIC_BACKEND_URL when BACKEND_URL is unset', () => {
    clearBackendEnv();
    process.env.NEXT_PUBLIC_BACKEND_URL = 'https://api.uvai.io/';
    expect(getBackendConfig()).toEqual({
      configured: true,
      url: 'https://api.uvai.io',
    });
  });

  it('falls back to NEXT_PUBLIC_API_URL (prod .env.production name)', () => {
    clearBackendEnv();
    process.env.NEXT_PUBLIC_API_URL = 'https://api.uvai.io';
    expect(getBackendConfig()).toEqual({
      configured: true,
      url: 'https://api.uvai.io',
    });
  });

  it('prefers BACKEND_URL over public aliases', () => {
    clearBackendEnv();
    process.env.BACKEND_URL = 'https://api.uvai.io';
    process.env.NEXT_PUBLIC_API_URL = 'https://example.invalid';
    expect(getBackendConfig()).toEqual({
      configured: true,
      url: 'https://api.uvai.io',
    });
  });
});

describe('checkBackendHealth', () => {
  const original = snapshotBackendEnv();

  afterEach(() => {
    restoreBackendEnv(original);
    vi.unstubAllGlobals();
  });

  it('returns available when health probe succeeds', async () => {
    process.env.BACKEND_URL = 'https://api.uvai.io';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true }),
    );

    const health = await checkBackendHealth(1000);
    expect(health.available).toBe(true);
    expect(health.host).toBe('api.uvai.io');
  });

  it('returns unavailable when health probe fails', async () => {
    process.env.BACKEND_URL = 'https://api.uvai.io';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    );

    const health = await checkBackendHealth(1000);
    expect(health.available).toBe(false);
    expect(health.reason).toContain('503');
  });
});

describe('parseBackendJson', () => {
  it('returns null for HTML error pages', async () => {
    const response = new Response('<html><body>503</body></html>', { status: 503 });
    expect(await parseBackendJson(response)).toBeNull();
  });

  it('parses valid JSON bodies', async () => {
    const response = new Response(JSON.stringify({ data: { job_id: 'job_1' } }), {
      status: 200,
    });
    expect(await parseBackendJson<{ data: { job_id: string } }>(response)).toEqual({
      data: { job_id: 'job_1' },
    });
  });
});