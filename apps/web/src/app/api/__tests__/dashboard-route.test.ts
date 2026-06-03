import { describe, it, expect, afterEach, vi } from 'vitest';
import { GET, POST } from '@/app/api/dashboard/route';

function jsonResponse(data: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as unknown as Response;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
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
});
