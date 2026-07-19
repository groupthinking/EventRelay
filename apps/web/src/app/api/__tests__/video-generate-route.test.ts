import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';

vi.mock('@/lib/billing/entitlement-store', () => ({
  isProSubscriber: vi.fn().mockResolvedValue(true),
}));

vi.mock('@/lib/billing/redis-credentials', () => ({
  resolveUpstashRedisCredentials: vi.fn().mockReturnValue(null),
}));

vi.mock('@/lib/ai-gateway', () => ({
  aiGateway: {
    videoModel: vi.fn().mockReturnValue('mocked-video-model'),
  },
  GATEWAY_VIDEO_MODEL: 'google/veo-3.1-generate-001',
}));

vi.mock('ai', () => ({
  experimental_generateVideo: vi.fn(),
}));

import { POST } from '@/app/api/video/generate/route';
import { experimental_generateVideo } from 'ai';

type VideoResult = Awaited<ReturnType<typeof experimental_generateVideo>>;

/** Build a POST request with a per-test client IP so the module-scoped rate
 *  limiter doesn't bleed between tests. Pass `raw` to send a non-JSON body. */
function postReq(body: unknown, ip = '10.0.0.1', raw = false) {
  return new Request('http://localhost:3000/api/video/generate', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-forwarded-for': ip },
    body: raw ? (body as string) : JSON.stringify(body),
  });
}

function makeVideoResult(base64 = 'AAAA') {
  const bytes = Buffer.from(base64, 'base64');
  return {
    video: {
      base64,
      uint8Array: new Uint8Array(bytes),
      mimeType: 'video/mp4',
    },
  };
}

const validBody = { prompt: 'a calm ocean at sunset', aspectRatio: '16:9', duration: 5 };

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('POST /api/video/generate', () => {
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
    vi.mocked(experimental_generateVideo).mockResolvedValue(makeVideoResult() as unknown as VideoResult);
    const ip = '10.9.9.9';
    for (let i = 0; i < 3; i++) {
      const ok = await POST(postReq(validBody, ip));
      expect(ok.status).toBe(200);
    }
    const limited = await POST(postReq(validBody, ip));
    expect(limited.status).toBe(429);
  });

  it('returns 200 with video bytes on success', async () => {
    // 'QkFTRTY0' is base64 for 'BASE64'
    vi.mocked(experimental_generateVideo).mockResolvedValue(makeVideoResult('QkFTRTY0') as unknown as VideoResult);
    const res = await POST(postReq(validBody, '10.0.0.10'));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toBe('video/mp4');
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.toString()).toBe('BASE64');
  });

  it('returns 500 when experimental_generateVideo throws', async () => {
    vi.mocked(experimental_generateVideo).mockRejectedValue(new Error('Model error'));
    const res = await POST(postReq(validBody, '10.0.0.11'));
    expect(res.status).toBe(500);
  });

  it('returns 504 on timeout', async () => {
    const timeoutErr = Object.assign(new Error('timeout'), { name: 'TimeoutError' });
    vi.mocked(experimental_generateVideo).mockRejectedValue(timeoutErr);
    const res = await POST(postReq(validBody, '10.0.0.12'));
    expect(res.status).toBe(504);
  });

  it('calls experimental_generateVideo with correct model and prompt', async () => {
    vi.mocked(experimental_generateVideo).mockResolvedValue(makeVideoResult() as unknown as VideoResult);
    await POST(postReq(validBody, '10.0.0.13'));
    expect(experimental_generateVideo).toHaveBeenCalledWith(
      expect.objectContaining({
        model: 'mocked-video-model',
        prompt: 'a calm ocean at sunset',
      })
    );
  });
});
