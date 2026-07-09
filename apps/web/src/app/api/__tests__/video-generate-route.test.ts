import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';

vi.mock('@/lib/billing/entitlement-store', () => ({
  isProSubscriber: vi.fn().mockResolvedValue(true),
}));

import { POST } from '@/app/api/video/generate/route';

const GATEWAY_URL = 'https://ai-gateway.vercel.sh/v1/video/generations';

/** Build a POST request with a per-test client IP so the module-scoped rate
 *  limiter doesn't bleed between tests. Pass `raw` to send a non-JSON body. */
function postReq(body: unknown, ip = '10.0.0.1', raw = false) {
  return new Request('http://localhost:3000/api/video/generate', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-forwarded-for': ip },
    body: raw ? (body as string) : JSON.stringify(body),
  });
}

function gatewayOk(json: unknown) {
  return { ok: true, status: 200, json: async () => json, text: async () => JSON.stringify(json) };
}
function gatewayErr(status: number) {
  return { ok: false, status, json: async () => ({}), text: async () => 'gateway error' };
}
function streamOf(text: string) {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
}
function videoBytesOk(text = 'FAKEVIDEO') {
  return {
    ok: true,
    status: 200,
    body: streamOf(text),
    headers: new Headers({ 'content-type': 'video/mp4', 'content-length': String(text.length) }),
  };
}

const validBody = { prompt: 'a calm ocean at sunset', aspectRatio: '16:9', duration: 5 };

beforeEach(() => {
  process.env.AI_GATEWAY_API_KEY = 'test-key';
  global.fetch = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
  delete process.env.AI_GATEWAY_API_KEY;
});

describe('POST /api/video/generate', () => {
  it('returns 503 when AI_GATEWAY_API_KEY is not configured', async () => {
    delete process.env.AI_GATEWAY_API_KEY;
    const res = await POST(postReq(validBody, '10.0.0.2'));
    expect(res.status).toBe(503);
  });

  it('returns 400 on invalid JSON body', async () => {
    const res = await POST(postReq('{not json', '10.0.0.3', true));
    expect(res.status).toBe(400);
  });

  it('returns 400 when prompt is missing/empty', async () => {
    const res = await POST(postReq({ prompt: '   ' }, '10.0.0.4'));
    expect(res.status).toBe(400);
  });

  it('returns 400 when prompt exceeds 1000 chars', async () => {
    const res = await POST(postReq({ prompt: 'x'.repeat(1001) }, '10.0.0.5'));
    expect(res.status).toBe(400);
  });

  it('returns 400 on invalid aspectRatio', async () => {
    const res = await POST(postReq({ ...validBody, aspectRatio: '3:2' }, '10.0.0.6'));
    expect(res.status).toBe(400);
  });

  it('returns 400 on out-of-range duration', async () => {
    const res = await POST(postReq({ ...validBody, duration: 999 }, '10.0.0.7'));
    expect(res.status).toBe(400);
  });

  it('enforces the per-IP rate limit (4th request within window → 429)', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      gatewayOk({ data: [{ b64_json: 'AAAA' }] }) as unknown as Response
    );
    const ip = '10.9.9.9';
    for (let i = 0; i < 3; i++) {
      const ok = await POST(postReq(validBody, ip));
      expect(ok.status).toBe(200);
    }
    const limited = await POST(postReq(validBody, ip));
    expect(limited.status).toBe(429);
  });

  it('propagates a gateway error status', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(gatewayErr(500) as unknown as Response);
    const res = await POST(postReq(validBody, '10.0.0.8'));
    expect(res.status).toBe(500);
  });

  it('returns 502 when the gateway response has no video', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      gatewayOk({ data: [{}] }) as unknown as Response
    );
    const res = await POST(postReq(validBody, '10.0.0.9'));
    expect(res.status).toBe(502);
  });

  it('streams the decoded bytes when the gateway provides base64 inline', async () => {
    // 'QkFTRTY0' is base64 for 'BASE64'
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      gatewayOk({ data: [{ b64_json: 'QkFTRTY0' }] }) as unknown as Response
    );
    const res = await POST(postReq(validBody, '10.0.0.10'));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toBe('video/mp4');
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.toString()).toBe('BASE64');
  });

  it('streams a remote signed URL through without base64-in-JSON (CSP-safe, no client proxy)', async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(gatewayOk({ data: [{ url: 'https://cdn.example/signed.mp4' }] }) as unknown as Response)
      .mockResolvedValueOnce(videoBytesOk() as unknown as Response);

    const res = await POST(postReq(validBody, '10.0.0.11'));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toBe('video/mp4');
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.toString()).toBe('FAKEVIDEO');
    // second fetch was the server-side retrieval of the gateway-provided URL
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe(GATEWAY_URL);
    expect(fetchMock.mock.calls[1][0]).toBe('https://cdn.example/signed.mp4');
  });

  it('returns 502 when the signed URL cannot be retrieved', async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(gatewayOk({ data: [{ url: 'https://cdn.example/signed.mp4' }] }) as unknown as Response)
      .mockResolvedValueOnce({ ok: false, status: 404, body: null, headers: new Headers() } as unknown as Response);

    const res = await POST(postReq(validBody, '10.0.0.12'));
    expect(res.status).toBe(502);
  });
});
