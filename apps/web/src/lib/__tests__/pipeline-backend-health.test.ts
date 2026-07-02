import { describe, it, expect, afterEach, vi } from 'vitest';
import {
  checkBackendHealth,
  getBackendConfig,
  parseBackendJson,
} from '@/lib/pipeline-backend-health';

describe('getBackendConfig', () => {
  const original = process.env.BACKEND_URL;

  afterEach(() => {
    if (original === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = original;
    vi.unstubAllGlobals();
  });

  it('reports unconfigured when BACKEND_URL is empty', () => {
    delete process.env.BACKEND_URL;
    expect(getBackendConfig()).toEqual({ configured: false, url: '' });
  });

  it('normalizes configured backend URL', () => {
    process.env.BACKEND_URL = 'https://api.uvai.io/';
    expect(getBackendConfig()).toEqual({
      configured: true,
      url: 'https://api.uvai.io',
    });
  });
});

describe('checkBackendHealth', () => {
  const original = process.env.BACKEND_URL;

  afterEach(() => {
    if (original === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = original;
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