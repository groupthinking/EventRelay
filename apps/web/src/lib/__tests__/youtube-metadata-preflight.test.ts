import { afterEach, describe, expect, it, vi } from 'vitest';
import { preflightYouTubeVideoSource } from '@/lib/youtube-metadata';

describe('preflightYouTubeVideoSource', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns not_found when oEmbed responds 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('Not Found', { status: 404 })),
    );

    const result = await preflightYouTubeVideoSource(
      'https://www.youtube.com/watch?v=j5-yXhJbFE4',
    );
    expect(result).toBe('not_found');
  });

  it('returns available when oEmbed succeeds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('{}', { status: 200 })),
    );

    const result = await preflightYouTubeVideoSource(
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );
    expect(result).toBe('available');
  });

  it('returns unknown for non-404 HTTP failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('upstream error', { status: 502 })),
    );

    const result = await preflightYouTubeVideoSource(
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );
    expect(result).toBe('unknown');
  });
});
