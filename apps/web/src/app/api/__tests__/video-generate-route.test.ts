import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { POST } from '@/app/api/video/generate/route';

// Mock billing modules
vi.mock('@/lib/billing/billing-context', () => ({
  resolveTrustedBillingEmail: vi.fn(async () => 'pro@example.com'),
}));

vi.mock('@/lib/billing/entitlement-store', () => ({
  isProSubscriber: vi.fn(async (email: string) => email === 'pro@example.com'),
}));

// Mock redis-credentials
vi.mock('@/lib/billing/redis-credentials', () => ({
  resolveUpstashRedisCredentials: vi.fn(() => ({ url: 'https://test.upstash.io', token: 'test-token' })),
}));

// Mock @upstash/redis
const redisIncrMock = vi.fn();
const redisExpireMock = vi.fn();
vi.mock('@upstash/redis', () => ({
  Redis: function() {
    return {
      incr: redisIncrMock,
      expire: redisExpireMock,
    };
  },
}));

// Mock aiGateway
vi.mock('@/lib/ai-gateway', () => ({
  aiGateway: {
    videoModel: vi.fn(() => 'mock-model'),
  },
  GATEWAY_VIDEO_MODEL: 'google/veo-3.1-generate-001',
}));

// Mock ai
const generateVideoMock = vi.fn();
vi.mock('ai', () => ({
  experimental_generateVideo: (...args: any[]) => generateVideoMock(...args),
}));

/** Build a POST request with a per-test client IP */
function postReq(body: unknown, ip = '10.0.0.1', raw = false) {
  return new Request('http://localhost:3000/api/video/generate', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-forwarded-for': ip },
    body: raw ? (body as string) : JSON.stringify(body),
  });
}

const validBody = { prompt: 'a calm ocean at sunset', aspectRatio: '16:9', duration: 5 };

beforeEach(() => {
  vi.clearAllMocks();
  redisIncrMock.mockResolvedValue(1);
  generateVideoMock.mockResolvedValue({
    video: {
      uint8Array: new Uint8Array([1, 2, 3, 4]),
      mediaType: 'video/mp4',
    },
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('POST /api/video/generate', () => {
  it('returns 402 when user is not a Pro subscriber', async () => {
    const { resolveTrustedBillingEmail } = await import('@/lib/billing/billing-context');
    (resolveTrustedBillingEmail as any).mockResolvedValueOnce('free@example.com');

    const res = await POST(postReq(validBody, '10.0.0.1'));
    expect(res.status).toBe(402);
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

  it('enforces the Redis rate limit (4th request within window → 429)', async () => {
    redisIncrMock.mockResolvedValue(4);
    const res = await POST(postReq(validBody, '10.9.9.9'));
    expect(res.status).toBe(429);
    expect(redisIncrMock).toHaveBeenCalledWith('ratelimit:video-generate:10.9.9.9');
  });

  it('sets expiration on the first request for an IP', async () => {
    redisIncrMock.mockResolvedValue(1);
    await POST(postReq(validBody, '10.1.1.1'));
    expect(redisExpireMock).toHaveBeenCalledWith('ratelimit:video-generate:10.1.1.1', 600);
  });

  it('fails closed with 503 when Redis credentials are missing in production', async () => {
    const { resolveUpstashRedisCredentials } = await import('@/lib/billing/redis-credentials');
    (resolveUpstashRedisCredentials as any).mockReturnValueOnce(null);
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');

    try {
      const res = await POST(postReq(validBody, '10.8.8.8'));
      expect(res.status).toBe(503);
      const body = await res.json();
      expect(body.code).toBe('rate_limit_unavailable');
      expect(generateVideoMock).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it('fails closed with 503 when Redis throws in production', async () => {
    redisIncrMock.mockRejectedValueOnce(new Error('redis down'));
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UVAI_RATE_LIMIT_FAIL_OPEN', '');
    try {
      const res = await POST(postReq(validBody, '10.7.7.7'));
      expect(res.status).toBe(503);
      const body = await res.json();
      expect(body.code).toBe('rate_limit_error');
      expect(generateVideoMock).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it('streams the bytes when generation is successful', async () => {
    const fakeVideoData = new Uint8Array([1, 2, 3, 4]);
    generateVideoMock.mockResolvedValue({
      video: {
        uint8Array: fakeVideoData,
        mediaType: 'video/mp4',
      },
    });

    const res = await POST(postReq(validBody, '10.0.0.10'));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toBe('video/mp4');
    expect(res.headers.get('x-video-model')).toBe('google/veo-3.1-generate-001');

    const buf = await res.arrayBuffer();
    expect(new Uint8Array(buf)).toEqual(fakeVideoData);
  });

  it('propagates TimeoutError as 504', async () => {
    const timeoutErr = new Error('Timeout');
    timeoutErr.name = 'TimeoutError';
    generateVideoMock.mockRejectedValue(timeoutErr);

    const res = await POST(postReq(validBody, '10.0.0.11'));
    expect(res.status).toBe(504);
  });

  it('returns 500 on other generation errors', async () => {
    generateVideoMock.mockRejectedValue(new Error('Gateway failed'));

    const res = await POST(postReq(validBody, '10.0.0.12'));
    expect(res.status).toBe(500);
  });
});
