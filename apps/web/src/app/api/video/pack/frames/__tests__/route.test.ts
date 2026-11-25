import { afterEach, describe, expect, it, vi } from 'vitest';
import { KEYFRAME_JPEG_CONTENT_TYPE } from '@/lib/keyframe-frame-capture';

afterEach(() => {
  vi.resetModules();
});

const JPEG = Uint8Array.from([0xff, 0xd8, 0xff, 0xd9]);

describe('GET /api/video/pack/frames/:videoId/:t', () => {
  it('serves a captured JPEG for a durable app-served path', async () => {
    const capture = await import('@/lib/keyframe-frame-capture');
    capture.resetKeyframeFrameCaptureForTests();
    capture.setKeyframeFrameCaptureForTests(async ({ videoId, t_s }) => ({
      bytes: JPEG,
      contentType: KEYFRAME_JPEG_CONTENT_TYPE,
      imagePath: `/api/video/pack/frames/${videoId}/${t_s}`,
    }));
    const { GET } = await import('../[videoId]/[t]/route');
    const res = await GET(new Request('http://localhost/api/video/pack/frames/QjZ5ohr7sGA/8'), {
      params: Promise.resolve({ videoId: 'QjZ5ohr7sGA', t: '8' }),
    });
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toBe(KEYFRAME_JPEG_CONTENT_TYPE);
    const body = new Uint8Array(await res.arrayBuffer());
    expect(body[0]).toBe(0xff);
    expect(body[1]).toBe(0xd8);
    expect(body[body.length - 1]).toBe(0xd9);
  });

  it('returns 404 when capture cannot obtain a real frame', async () => {
    const capture = await import('@/lib/keyframe-frame-capture');
    capture.resetKeyframeFrameCaptureForTests();
    capture.setKeyframeFrameCaptureForTests(async () => null);
    const { GET } = await import('../[videoId]/[t]/route');
    const res = await GET(new Request('http://localhost/api/video/pack/frames/QjZ5ohr7sGA/8'), {
      params: Promise.resolve({ videoId: 'QjZ5ohr7sGA', t: '8' }),
    });
    expect(res.status).toBe(404);
  });
});
