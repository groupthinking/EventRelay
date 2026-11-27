import { describe, expect, it } from 'vitest';
import { loadSamplePack } from '@/lib/sample-pack';
import {
  studioPackTimelineCanSeek,
  studioPackTimelineDuration,
  studioPackTimelineHasSurface,
  studioPackTimelineMarkers,
} from '@/lib/studio-pack-timeline';
import type { EmittedVideoPack } from '@/lib/emit-video-pack';

describe('studio-pack-timeline', () => {
  it('builds chapter + keyframe + moment markers from the auJzb1D-fag fixture pack', () => {
    const { pack } = loadSamplePack();
    expect(pack.video_id).toBe('auJzb1D-fag');
    expect(studioPackTimelineHasSurface(pack)).toBe(true);

    const markers = studioPackTimelineMarkers(pack);
    const chapters = markers.filter((m) => m.kind === 'chapter');
    const keyframes = markers.filter((m) => m.kind === 'keyframe');
    const moments = markers.filter((m) => m.kind === 'moment');

    expect(chapters).toHaveLength(9);
    expect(chapters[0]).toMatchObject({
      start: 0,
      end: 27,
      label: 'Welcome to the Multimodal Era',
    });
    expect(keyframes.length).toBeGreaterThanOrEqual(12);
    expect(moments.length).toBeGreaterThanOrEqual(1);
    expect(markers.every((m) => Number.isFinite(m.start))).toBe(true);
  });

  it('returns no markers and no surface for empty / missing pack (no mocks)', () => {
    expect(studioPackTimelineMarkers(undefined)).toEqual([]);
    expect(studioPackTimelineMarkers(null)).toEqual([]);
    expect(studioPackTimelineHasSurface(undefined)).toBe(false);

    const empty: EmittedVideoPack = {
      version: 'v0',
      id: 'vp:v0:auJzb1D-fag',
      video_id: 'auJzb1D-fag',
      source_url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      provenance: { source_hash: 'a'.repeat(64) },
    };
    expect(studioPackTimelineMarkers(empty)).toEqual([]);
    expect(studioPackTimelineHasSurface(empty)).toBe(false);
  });

  it('includes optional pack events[] when present without inventing them', () => {
    const { pack } = loadSamplePack();
    const withEvents: EmittedVideoPack = {
      ...pack,
      events: [{ id: 'e1', title: 'Demo beat', timestamp: 340 }],
    };
    const events = studioPackTimelineMarkers(withEvents).filter((m) => m.kind === 'event');
    expect(events).toEqual([
      expect.objectContaining({ id: 'e1', start: 340, label: 'Demo beat' }),
    ]);
  });

  it('derives duration from pack evidence and prefers a longer player duration', () => {
    const { pack } = loadSamplePack();
    const packSpan = studioPackTimelineDuration(pack);
    expect(packSpan).toBeGreaterThanOrEqual(481);
    expect(studioPackTimelineDuration(pack, 520)).toBe(520);
    expect(studioPackTimelineDuration(pack, 10)).toBe(packSpan);
  });

  it('gates seek to the selected pack video id', () => {
    expect(
      studioPackTimelineCanSeek({ videoId: 'auJzb1D-fag', packVideoId: 'auJzb1D-fag' }),
    ).toBe(true);
    expect(
      studioPackTimelineCanSeek({ videoId: '9PICEmtfpWU', packVideoId: 'auJzb1D-fag' }),
    ).toBe(false);
    expect(studioPackTimelineCanSeek({ videoId: 'auJzb1D-fag', packVideoId: null })).toBe(true);
    expect(studioPackTimelineCanSeek({ videoId: null, packVideoId: 'auJzb1D-fag' })).toBe(false);
  });
});
