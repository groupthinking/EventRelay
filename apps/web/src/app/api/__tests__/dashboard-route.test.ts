import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { GET, POST } from '@/app/api/dashboard/route';

function jsonResponse(data: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as unknown as Response;
}

/**
 * These tests previously passed without configuring any backend URL at all.
 * That worked only because the route fell back to a hardcoded
 * `http://localhost:8000` placeholder, so "backend healthy" and "no backend
 * configured" were indistinguishable — the exact production bug (audit finding
 * F1/F2). The route now resolves per-request and reports `unconfigured`
 * honestly, so each test states which world it is in.
 */
const TEST_BACKEND = 'https://backend.test.internal';

beforeEach(() => {
  vi.stubEnv('BACKEND_URL', TEST_BACKEND);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('GET /api/dashboard', () => {
  it('reports operational status with mapped metrics when the backend is healthy', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ active_connections: 5, total_requests: 100 })),
    );
    const res = await GET();
    const body = await res.json();
    expect(body.status).toBe('operational');
    expect(body.metrics.activeWorkflows).toBe(5);
    expect(body.metrics.totalProcessed).toBe(100);
  });

  it('returns a degraded fallback when the backend is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')));
    const res = await GET();
    const body = await res.json();
    expect(body.status).toBe('degraded');
    expect(body.metrics.activeWorkflows).toBe(0);
  });

  it('reports "unconfigured" — not "degraded" — when no backend is set, without any fetch', async () => {
    // The regression guard for F2. A missing backend must be distinguishable
    // from an unhealthy one, and must never trigger a request to a placeholder
    // localhost URL.
    vi.stubEnv('BACKEND_URL', '');
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);

    const res = await GET();
    const body = await res.json();

    expect(body.status).toBe('unconfigured');
    expect(body.reason).toBeTruthy();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe('POST /api/dashboard', () => {
  it('proxies the backend embed payload on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ embed_url: 'https://looker/embed' })),
    );
    const req = new Request('http://localhost/api/dashboard', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ dashboard_id: 'custom' }),
    });
    const res = await POST(req);
    const body = await res.json();
    expect(body.embed_url).toBe('https://looker/embed');
  });

  it('returns a 500 when the backend embed call fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse('bad', false, 502)));
    const req = new Request('http://localhost/api/dashboard', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({}),
    });
    const res = await POST(req);
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/Failed to retrieve/);
  });

  it('returns 503 with a reason when no backend is configured', async () => {
    // Distinct from the 500 above: an unconfigured backend is a deployment
    // problem the operator can fix, not a backend failure.
    vi.stubEnv('BACKEND_URL', '');
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);

    const req = new Request('http://localhost/api/dashboard', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({}),
    });
    const res = await POST(req);

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toMatch(/NEXT_PUBLIC_BACKEND_URL/);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
