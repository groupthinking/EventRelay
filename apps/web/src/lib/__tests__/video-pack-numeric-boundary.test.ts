import { describe, expect, it } from 'vitest';
import { planShardManifest, validateShardManifest } from '../video-pack-shard-planner';
const ID = 'auJzb1D-fag';
const URL = `https://www.youtube.com/watch?v=${ID}`;
describe('shard numeric boundary', () => {
  it('rejects nonfinite duration before section planning can loop', () => {
    for (const duration of [NaN, Infinity, -Infinity, -1]) expect(() => planShardManifest(ID, URL, null, duration)).toThrow('duration');
  });
  it('rejects invalid injected workers and cost bounds before planning', () => {
    for (const workers of [NaN, Infinity, -1, 0, 1.5]) expect(() => planShardManifest(ID, URL, null, 60, { maxWorkers: workers })).toThrow('worker');
    for (const cost of [NaN, Infinity, -1, 0]) expect(() => planShardManifest(ID, URL, null, 60, {}, { costBoundUnits: cost })).toThrow('cost');
  });
  it('fails the checkpoint on corrupted numeric receipts', () => {
    for (const field of ['durationSeconds', 'parallelCap', 'costUnits', 'costBoundUnits'] as const) {
      for (const value of [NaN, Infinity, -Infinity]) {
        const manifest = planShardManifest(ID, URL, null, 60);
        manifest[field] = value;
        expect(validateShardManifest(manifest).ok).toBe(0);
      }
    }
    const manifest = planShardManifest(ID, URL, null, 60);
    manifest.shards[0].end_s = Infinity;
    expect(validateShardManifest(manifest).ok).toBe(0);
    manifest.shards[0].end_s = 60;
    manifest.parallelCap = 1.5;
    expect(validateShardManifest(manifest).ok).toBe(0);
  });
});
