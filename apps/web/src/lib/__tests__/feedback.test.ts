import { afterEach, describe, expect, it, vi } from 'vitest';

import { flushPendingFeedback, submitFeedback } from '@/lib/feedback';

describe('feedback persistence', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('resolves only when the feedback API accepts the entry', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      submitFeedback({ videoId: 'video-1', tab: 'summary', rating: 5 }),
    ).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/feedback',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('rejects HTTP failures instead of reporting an in-memory success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    await expect(
      submitFeedback({ videoId: 'video-1', tab: 'summary', rating: 2 }),
    ).rejects.toThrow('Feedback API returned 503');
    await expect(flushPendingFeedback()).resolves.toBe(0);
  });

  it('rejects network failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));

    await expect(
      submitFeedback({ videoId: 'video-1', tab: 'summary', rating: 3 }),
    ).rejects.toThrow('offline');
  });
});
