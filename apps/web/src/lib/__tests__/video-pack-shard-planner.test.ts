import { describe, expect, it } from 'vitest';
import type { YouTubeMetadata } from '@/lib/youtube-metadata';
import { VIDEO_PACK_CHUNK_MAX_PARALLEL } from '@/lib/video-pack-extract-segments';
import {
  planShardManifest,
  validateShardManifest,
  VIDEO_PACK_VIDEO_MODEL,
  type ShardManifest,
} from '@/lib/video-pack-shard-planner';

const SOURCE_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag';

function metadataWithChapters(): YouTubeMetadata {
  return {
    videoId: 'auJzb1D-fag',
    title: 'Build a thing',
    channel: 'Test channel',
    description: '0:00 Intro\n10:00 Build\n20:00 Ship',
    chapters: [
      { time: '0:00', title: 'Intro' },
      { time: '10:00', title: 'Build' },
      { time: '20:00', title: 'Ship' },
    ],
    durationSeconds: 1800,
  };
}

describe('planShardManifest', () => {
  it('plans chapter shards for a 30-minute video and validates to 1', () => {
    const manifest = planShardManifest('auJzb1D-fag', SOURCE_URL, metadataWithChapters(), 1800);
    expect(manifest.model).toBe('gemini-3.8-flash');
    expect(manifest.shards).toHaveLength(3);
    expect(manifest.shards[0]).toMatchObject({ index: 0, start_s: 0, end_s: 600 });
    expect(manifest.parallelCap).toBeLessThanOrEqual(VIDEO_PACK_CHUNK_MAX_PARALLEL);
    expect(manifest.costUnits).toBeLessThanOrEqual(manifest.costBoundUnits);
    expect(validateShardManifest(manifest)).toEqual({ ok: 1, failures: [] });
  });

  it('plans fixed 180s windows without chapters and validates to 1', () => {
    const manifest = planShardManifest('auJzb1D-fag', SOURCE_URL, null, 3600);
    expect(manifest.shards).toHaveLength(20);
    expect(manifest.shards[19]).toMatchObject({ start_s: 3420, end_s: 3600 });
    expect(manifest.costUnits).toBe(3600);
    expect(manifest.costBoundUnits).toBe(3600);
    expect(validateShardManifest(manifest)).toEqual({ ok: 1, failures: [] });
  });

  it('emits a single full-range shard for short videos', () => {
    const manifest = planShardManifest('auJzb1D-fag', SOURCE_URL, null, 120);
    expect(manifest.shards).toHaveLength(1);
    expect(manifest.shards[0]).toMatchObject({ start_s: 0, end_s: 120 });
    expect(validateShardManifest(manifest)).toEqual({ ok: 1, failures: [] });
  });

  it('honors injected Jev decisions for cap and bound', () => {
    const manifest = planShardManifest('auJzb1D-fag', SOURCE_URL, null, 3600, {}, {
      maxWorkers: 2,
      costBoundUnits: 3600,
    });
    expect(manifest.parallelCap).toBe(2);
    expect(validateShardManifest(manifest).ok).toBe(1);
  });

  it('clamps an excessive worker ask to the parallel cap', () => {
    const manifest = planShardManifest('auJzb1D-fag', SOURCE_URL, null, 3600, {}, {
      maxWorkers: 99,
    });
    expect(manifest.parallelCap).toBe(VIDEO_PACK_CHUNK_MAX_PARALLEL);
  });
});

describe('validateShardManifest 0/1 predicate', () => {
  function validManifest(): ShardManifest {
    return planShardManifest('auJzb1D-fag', SOURCE_URL, null, 360);
  }

  it('returns 1 with no failures for a contiguous plan', () => {
    expect(validateShardManifest(validManifest())).toEqual({ ok: 1, failures: [] });
  });

  it('returns 0 naming a head coverage gap', () => {
    const manifest = validManifest();
    manifest.shards[0].start_s = 30;
    const result = validateShardManifest(manifest);
    expect(result.ok).toBe(0);
    expect(result.failures.join(' ')).toMatch(/head/);
  });

  it('returns 0 naming a tail coverage gap', () => {
    const manifest = validManifest();
    manifest.shards[manifest.shards.length - 1].end_s = 300;
    const result = validateShardManifest(manifest);
    expect(result.ok).toBe(0);
    expect(result.failures.join(' ')).toMatch(/tail/);
  });

  it('returns 0 naming an interior gap', () => {
    const manifest = validManifest();
    manifest.shards[1].start_s = 250;
    const result = validateShardManifest(manifest);
    expect(result.ok).toBe(0);
    expect(result.failures.join(' ')).toMatch(/gap/);
  });

  it('returns 0 naming an overlap beyond the 1s pad', () => {
    const manifest = validManifest();
    manifest.shards[1].start_s = 120;
    const result = validateShardManifest(manifest);
    expect(result.ok).toBe(0);
    expect(result.failures.join(' ')).toMatch(/overlap/);
  });

  it('returns 0 when cost exceeds the bound (N×full-video fan-out)', () => {
    const manifest = validManifest();
    manifest.costBoundUnits = 100;
    const result = validateShardManifest(manifest);
    expect(result.ok).toBe(0);
    expect(result.failures.join(' ')).toMatch(/forbidden/);
  });

  it('returns 0 when the model is not the pinned direct id', () => {
    const manifest = validManifest();
    manifest.model = 'google/gemini-3.8-flash';
    const result = validateShardManifest(manifest);
    expect(result.ok).toBe(0);
    expect(result.failures.join(' ')).toMatch(/pinned/);
  });

  it('returns 0 when parallelCap exceeds the max', () => {
    const manifest = validManifest();
    manifest.parallelCap = 99;
    const result = validateShardManifest(manifest);
    expect(result.ok).toBe(0);
    expect(result.failures.join(' ')).toMatch(/parallelCap/);
  });

  it('model const stays the bare direct-SDK id (no gateway prefix)', () => {
    expect(VIDEO_PACK_VIDEO_MODEL).toBe('gemini-3.8-flash');
  });
});
