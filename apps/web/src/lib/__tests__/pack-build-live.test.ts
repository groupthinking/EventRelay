import { describe, expect, it, vi, afterEach } from 'vitest';
import {
  packBuildLiveFailureDetails,
  packBuildLivePath,
  packBuildLiveUrl,
  resolvePackBuildLiveVideoId,
  studioPackBuildLiveSuccessReceiptForSelection,
  studioPackLiveReceiptForSelection,
  verifyPackBuildLive,
} from '@/lib/pack-build-live';
import { XYMC_VIDEO_ID, XYMC_SOURCE_HASH } from '@/lib/__fixtures__/xymcbrfsj4c-emit';

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

  it('resolves hosted video id from pack citation, not dashboard record uuid', () => {
    const dashboardRowId = 'f47ac10b-58cc-4372-a567-0e02b2c3d479';
    expect(
      resolvePackBuildLiveVideoId({
        packVideoId: XYMC_VIDEO_ID,
        watchUrl: `https://www.youtube.com/watch?v=${XYMC_VIDEO_ID}`,
      }),
    ).toBe(XYMC_VIDEO_ID);
    expect(
      resolvePackBuildLiveVideoId({
        packVideoId: XYMC_VIDEO_ID,
        watchUrl: `https://www.youtube.com/watch?v=${dashboardRowId}`,
      }),
    ).toBe(XYMC_VIDEO_ID);
  });

  it('opens Build live when sandbox confirms pack under source_hash after health miss', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          health: { ok: false, reason_code: 'HOSTED_PACK_NOT_FOUND' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'success',
          data: { videoId: XYMC_VIDEO_ID, sourceHash: XYMC_SOURCE_HASH },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          health: { ok: true, status: 200 },
          factory_deliver: { ready: true, reason_code: 'FACTORY_DELIVER_READY' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const result = await verifyPackBuildLive({
      videoId: XYMC_VIDEO_ID,
      sourceHash: XYMC_SOURCE_HASH,
      origin: 'https://uvai.io',
    });

    expect(result).toMatchObject({
      ok: true,
      liveUrl: `https://uvai.io/d/${XYMC_VIDEO_ID}`,
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(`/d/${XYMC_VIDEO_ID}/health`);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain(
      `source_hash=${encodeURIComponent(XYMC_SOURCE_HASH)}`,
    );
  });

  it('succeeds after sandbox confirm when health stays degraded but pack is stored', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          health: {
            ok: false,
            reason_code: 'HOSTED_PACK_EXTRACT_FAILED',
            detail: 'Vercel AI Gateway returned empty content',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'success',
          data: { videoId: XYMC_VIDEO_ID },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          health: {
            ok: false,
            reason_code: 'HOSTED_PACK_EXTRACT_FAILED',
          },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const result = await verifyPackBuildLive({
      videoId: XYMC_VIDEO_ID,
      sourceHash: XYMC_SOURCE_HASH,
      origin: 'https://uvai.io',
    });

    expect(result).toMatchObject({
      ok: true,
      liveUrl: `https://uvai.io/d/${XYMC_VIDEO_ID}`,
    });
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

  it('builds a Setup→Result success receipt scoped to the dashboard row', () => {
    const live = `https://uvai.io/d/${XYMC_VIDEO_ID}`;
    const receipt = studioPackBuildLiveSuccessReceiptForSelection({
      selectedVideoId: 'row-1',
      receiptVideoId: 'row-1',
      youtubeVideoId: XYMC_VIDEO_ID,
      liveUrl: live,
      reasonCode: 'FACTORY_DELIVER_READY',
    });
    expect(receipt).toMatchObject({
      jobTitle: 'Build live',
      youtubeVideoId: XYMC_VIDEO_ID,
      artifactPath: `/d/${XYMC_VIDEO_ID}`,
      reasonCode: 'FACTORY_DELIVER_READY',
    });
    expect(
      studioPackBuildLiveSuccessReceiptForSelection({
        selectedVideoId: 'other',
        receiptVideoId: 'row-1',
        youtubeVideoId: XYMC_VIDEO_ID,
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

  it('surfaces missing pack as a build failure without raw API copy', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          videoId: XYMC_VIDEO_ID,
          health: {
            ok: false,
            reason_code: 'HOSTED_PACK_NOT_FOUND',
            detail: 'Video pack not found. Generate /api/video/pack first.',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ status: 'error' }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const result = await verifyPackBuildLive({
      videoId: XYMC_VIDEO_ID,
      origin: 'https://uvai.io',
    });

    expect(result).toMatchObject({ ok: false, reasonCode: 'HOSTED_PACK_NOT_FOUND' });
    if (!result.ok) {
      expect(result.message).toMatch(/stored video pack/i);
      expect(result.message).not.toMatch(/\/api\//i);
    }
  });

  it('returns recovery actions for missing-pack Build live failures', () => {
    const failure = packBuildLiveFailureDetails({
      reasonCode: 'HOSTED_PACK_NOT_FOUND',
      videoId: XYMC_VIDEO_ID,
      origin: 'https://uvai.io',
    });
    expect(failure.title).toMatch(/no stored video pack/i);
    expect(failure.actions.map((a) => a.id)).toContain('rerun_analysis');
    expect(failure.message).not.toMatch(/\/api\//i);
  });

  it('offers hosted page recovery when extraction failed but /d is available', () => {
    const failure = packBuildLiveFailureDetails({
      reasonCode: 'HOSTED_PACK_EXTRACT_FAILED',
      videoId: XYMC_VIDEO_ID,
      origin: 'https://uvai.io',
    });
    const open = failure.actions.find((a) => a.id === 'open_hosted');
    expect(open).toMatchObject({ href: `https://uvai.io/d/${XYMC_VIDEO_ID}` });
  });

  it('retries hosted health after sandbox confirms a stored pack', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          health: { ok: false, reason_code: 'HOSTED_PACK_NOT_FOUND' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', data: {} }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          health: { ok: true, status: 200 },
          factory_deliver: { ready: true, reason_code: 'FACTORY_DELIVER_READY' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const result = await verifyPackBuildLive({
      videoId: XYMC_VIDEO_ID,
      sourceHash: 'a'.repeat(64),
      origin: 'https://uvai.io',
    });

    expect(result).toMatchObject({
      ok: true,
      liveUrl: `https://uvai.io/d/${XYMC_VIDEO_ID}`,
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('uses sandbox video id when an incorrect dashboard row id was probed on health', async () => {
    const dashboardRowId = 'f47ac10b-58cc-4372-a567-0e02b2c3d479';
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          health: { ok: false, reason_code: 'HOSTED_PACK_NOT_FOUND' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'success',
          data: { videoId: XYMC_VIDEO_ID },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          health: { ok: true, status: 200 },
          factory_deliver: { ready: true, reason_code: 'FACTORY_DELIVER_READY' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const result = await verifyPackBuildLive({
      videoId: dashboardRowId,
      sourceHash: XYMC_SOURCE_HASH,
      origin: 'https://uvai.io',
    });

    expect(result).toMatchObject({
      ok: true,
      liveUrl: `https://uvai.io/d/${XYMC_VIDEO_ID}`,
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(`/d/${dashboardRowId}/health`);
    expect(String(fetchMock.mock.calls[2]?.[0])).toContain(`/d/${XYMC_VIDEO_ID}/health`);
  });
});
