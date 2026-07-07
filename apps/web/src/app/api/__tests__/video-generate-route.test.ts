import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { experimentalGenerateVideo, videoModel } = vi.hoisted(() => ({
  experimentalGenerateVideo: vi.fn(),
  videoModel: vi.fn(() => 'mock-video-model'),
}));

vi.mock('ai', () => ({
  experimental_generateVideo: experimentalGenerateVideo,
}));

vi.mock('@/lib/ai-gateway', () => ({
  aiGateway: {
    video: videoModel,
  },
  GATEWAY_VIDEO_MODEL: 'google/veo-3.1-generate-001',
}));

import { POST } from '@/app/api/video/generate/route';

function postRequest(
  body: unknown,
  headers: Record<string, string> = {},
) {
  return new Request('http://localhost:3000/api/video/generate', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      ...headers,
    },
    body: JSON.stringify(body),
  });
}

describe('POST /api/video/generate', () => {
  beforeEach(() => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    experimentalGenerateVideo.mockResolvedValue({
      videos: [
        {
          base64: 'ZmFrZQ==',
          mediaType: 'video/mp4',
          uint8Array: new Uint8Array([1, 2, 3]),
        },
      ],
    });
  });

  afterEach(() => {
    delete process.env.AI_GATEWAY_API_KEY;
    vi.clearAllMocks();
  });

  it('rejects requests without a prompt', async () => {
    const response = await POST(postRequest({}));
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body.error).toMatch(/prompt/i);
  });

  it('returns generated video data for a valid prompt', async () => {
    const response = await POST(
      postRequest(
        { prompt: 'A sunrise over snowy mountains', aspectRatio: '16:9', duration: 5 },
        { 'x-forwarded-for': '198.51.100.10' },
      ),
    );
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(videoModel).toHaveBeenCalledWith('google/veo-3.1-generate-001');
    expect(experimentalGenerateVideo).toHaveBeenCalledWith(
      expect.objectContaining({
        model: 'mock-video-model',
        prompt: 'A sunrise over snowy mountains',
        aspectRatio: '16:9',
        duration: 5,
      }),
    );
    expect(body.videoBase64).toBe('ZmFrZQ==');
  });

  it('rate limits repeated requests from the same IP', async () => {
    const headers = { 'x-forwarded-for': '198.51.100.44' };

    for (let attempt = 0; attempt < 3; attempt++) {
      const response = await POST(postRequest({ prompt: `clip ${attempt}` }, headers));
      expect(response.status).toBe(200);
    }

    const limited = await POST(postRequest({ prompt: 'clip 4' }, headers));
    const body = await limited.json();

    expect(limited.status).toBe(429);
    expect(body.error).toMatch(/rate limit/i);
  });

  it('rejects oversized generated video payloads instead of returning huge inline data', async () => {
    experimentalGenerateVideo.mockResolvedValueOnce({
      videos: [
        {
          base64: 'a'.repeat(2_000_001),
          mediaType: 'video/mp4',
          uint8Array: new Uint8Array([1, 2, 3]),
        },
      ],
    });

    const response = await POST(
      postRequest(
        { prompt: 'A very long cinematic flyover' },
        { 'x-forwarded-for': '198.51.100.77' },
      ),
    );
    const body = await response.json();

    expect(response.status).toBe(413);
    expect(body.error).toMatch(/too large/i);
  });
});
