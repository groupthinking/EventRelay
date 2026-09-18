import { describe, expect, it, vi, afterEach } from 'vitest';
import {
  packBuildLivePath,
  packBuildLiveUrl,
  studioPackLiveReceiptForSelection,
  verifyPackBuildLive,
} from '@/lib/pack-build-live';
import { XYMC_VIDEO_ID } from '@/lib/__fixtures__/xymcbrfsj4c-emit';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('pack-build-live', () => {
  it('maps a video id to the hosted compiled spec path', () => {
    expect(packBuildLivePath(XYMC_VIDEO_ID)).toBe(`/d/${XYMC_VIDEO_ID}`);
  });

  it('builds an absolute https live URL on the current origin', () => {
    expect(packBuildLiveUrl('https://uvai.io', XYMC_VIDEO_ID)).toBe(
      `https://uvai.io/d/${XYMC_VIDEO_ID}`,
    );
  });

  it('scopes pack live receipts to the selected video', () => {
    const live = `https://uvai.io/d/${XYMC_VIDEO_ID}`;
    expect(
      studioPackLiveReceiptForSelection({
        selectedVideoId: XYMC_VIDEO_ID,
        receiptVideoId: XYMC_VIDEO_ID,
        liveUrl: live,
      }),
    ).toBe(live);
    expect(
      studioPackLiveReceiptForSelection({
        selectedVideoId: 'other',
        receiptVideoId: XYMC_VIDEO_ID,
        liveUrl: live,
      }),
    ).toBeNull();
  });

  it('verifies hosted health before returning a live URL', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        videoId: XYMC_VIDEO_ID,
        live_url: `/d/${XYMC_VIDEO_ID}`,
        health: { ok: true, status: 200 },
        factory_deliver: { ready: true, reason_code: 'FACTORY_DELIVER_READY' },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await verifyPackBuildLive({
      videoId: XYMC_VIDEO_ID,
      origin: 'https://uvai.io',
    });

    expect(result).toMatchObject({
      ok: true,
      liveUrl: `https://uvai.io/d/${XYMC_VIDEO_ID}`,
      reasonCode: 'FACTORY_DELIVER_READY',
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(`/d/${XYMC_VIDEO_ID}/health`);
  });

  it('surfaces missing pack as a build failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: 'Video pack not found. Generate /api/video/pack first.' }),
      }),
    );

    const result = await verifyPackBuildLive({
      videoId: XYMC_VIDEO_ID,
      origin: 'https://uvai.io',
    });

    expect(result).toMatchObject({ ok: false });
    if (!result.ok) {
      expect(result.message).toMatch(/pack not found/i);
    }
  });
});
