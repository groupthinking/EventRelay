import { describe, expect, it } from 'vitest';
import {
  planVideoPackExtractSections,
  shouldUseChunkedVideoPackExtract,
  VIDEO_PACK_CHUNKED_EXTRACT_MIN_DURATION_SECONDS,
  VIDEO_PACK_CHUNK_DURATION_SECONDS,
} from '@/lib/video-pack-extract-segments';
import type { YouTubeMetadata } from '@/lib/youtube-metadata';

function meta(partial: Partial<YouTubeMetadata> & Pick<YouTubeMetadata, 'videoId'>): YouTubeMetadata {
  return {
    title: 'title',
    channel: 'channel',
    description: '',
    chapters: [],
    durationSeconds: null,
    ...partial,
  };
}

describe('planVideoPackExtractSections', () => {
  it('returns a single full span for short videos without chapters', () => {
    const sections = planVideoPackExtractSections(meta({ videoId: 'auJzb1D-fag', durationSeconds: 120 }), 120);
    expect(sections).toHaveLength(1);
    expect(sections[0]?.start_s).toBe(0);
    expect(sections[0]?.end_s).toBe(120);
  });

  it('splits long videos into fixed-duration windows', () => {
    const duration = VIDEO_PACK_CHUNKED_EXTRACT_MIN_DURATION_SECONDS + VIDEO_PACK_CHUNK_DURATION_SECONDS;
    const sections = planVideoPackExtractSections(meta({ videoId: 'QjZ5ohr7sGA', durationSeconds: duration }), duration);
    expect(sections.length).toBeGreaterThanOrEqual(2);
    expect(sections[0]?.start_s).toBe(0);
    expect(sections[1]?.start_s).toBe(VIDEO_PACK_CHUNK_DURATION_SECONDS);
  });

  it('prefers YouTube description chapters when at least two markers exist', () => {
    const metadata = meta({
      videoId: 'QjZ5ohr7sGA',
      durationSeconds: 600,
      chapters: [
        { time: '0:00', title: 'Intro' },
        { time: '2:30', title: 'Jack placement' },
        { time: '5:00', title: 'Tighten lugs' },
      ],
    });
    const sections = planVideoPackExtractSections(metadata, 600);
    expect(sections).toHaveLength(3);
    expect(sections[0]?.topic).toBe('Intro');
    expect(sections[1]?.start_s).toBe(150);
    expect(sections[2]?.end_s).toBe(600);
  });
});

describe('shouldUseChunkedVideoPackExtract', () => {
  it('enables chunked mode when multiple sections are planned', () => {
    const metadata = meta({
      videoId: 'QjZ5ohr7sGA',
      durationSeconds: 900,
      chapters: [
        { time: '0:00', title: 'A' },
        { time: '3:00', title: 'B' },
      ],
    });
    expect(shouldUseChunkedVideoPackExtract(metadata, 900)).toBe(true);
    expect(shouldUseChunkedVideoPackExtract(meta({ videoId: 'auJzb1D-fag', durationSeconds: 60 }), 60)).toBe(
      false,
    );
  });
});
