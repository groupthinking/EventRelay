import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';

vi.mock('@/lib/billing/entitlement-store', () => ({
  isProSubscriber: vi.fn().mockResolvedValue(true),
}));

vi.mock('@/lib/billing/redis-credentials', () => ({
  resolveUpstashRedisCredentials: vi.fn().mockReturnValue(null),
}));

vi.mock('ai', () => ({
  experimental_generateVideo: vi.fn(),
}));

vi.mock('@/lib/ai-gateway', () => ({
  aiGateway: {
    videoModel: vi.fn().mockReturnValue('mocked-model'),
  },
  GATEWAY_VIDEO_MODEL: 'google/veo-3.1-generate-001',
}));

import { POST } from '@/app/api/video/generate/route';
import { experimental_generateVideo } from 'ai';
import { isProSubscriber } from '@/lib/billing/entitlement-store';

const mockGenerateVideo = experimental_generateVideo as ReturnType<typeof vi.fn>;
const mockIsProSubscriber = isProSubscriber as ReturnType<typeof vi.fn>;

/** Build a POST request with a per-test client IP so the rate limiter
 *  doesn't bleed between tests. Pass `raw` to send a non-JSON body. */
function postReq(body: unknown, ip = '10.0.0.1', raw = false) {
  return new Request('http://localhost:3000/api/video/generate', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-forwarded-for': ip },
    body: raw ? (body as string) : JSON.stringify(body),
  });
}

/** A synthetic video object returned by experimental_generateVideo. */
function fakeVideo(bytes = new Uint8Array([1, 2, 3, 4])) {
  return {
    video: {
      uint8Array: bytes,
      mediaType: 'video/mp4',
    },
  };
}

const validBody = { prompt: 'a calm ocean at sunset', aspectRatio: '16:9', duration: 5 };

beforeEach(() => {
  mockGenerateVideo.mockResolvedValue(fakeVideo());
  mockIsProSubscriber.mockResolvedValue(true);
});

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('POST /api/video/generate', () => {
  it('returns 402 for non-Pro subscribers', async () => {
    mockIsProSubscriber.mockResolvedValueOnce(false);
    const res = await POST(postReq(validBody, '10.1.0.1'));
    expect(res.status).toBe(402);
    const body = await res.json();
    expect(body.upgradeRequired).toBe(true);
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

  it('streams video bytes on success', async () => {
    const bytes = new Uint8Array([0x46, 0x41, 0x4b, 0x45]); // 'FAKE'
    mockGenerateVideo.mockResolvedValueOnce(fakeVideo(bytes));

    const res = await POST(postReq(validBody, '10.0.0.10'));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toBe('video/mp4');
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.toString()).toBe('FAKE');
  });

  it('returns 504 on timeout', async () => {
    const err = new Error('timeout');
    err.name = 'TimeoutError';
    mockGenerateVideo.mockRejectedValueOnce(err);

    const res = await POST(postReq(validBody, '10.0.0.11'));
    expect(res.status).toBe(504);
  });

  it('returns 500 on generation error', async () => {
    mockGenerateVideo.mockRejectedValueOnce(new Error('generation failed'));

    const res = await POST(postReq(validBody, '10.0.0.12'));
    expect(res.status).toBe(500);
  });

  it('calls experimental_generateVideo with correct parameters', async () => {
    const res = await POST(postReq({ ...validBody, aspectRatio: '9:16', duration: 10 }, '10.0.0.13'));
    expect(res.status).toBe(200);
    expect(mockGenerateVideo).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: validBody.prompt,
        aspectRatio: '9:16',
        duration: 10,
      })
    );
  });
});
