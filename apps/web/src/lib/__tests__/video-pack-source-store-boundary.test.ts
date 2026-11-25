import { afterEach, expect, it, vi } from 'vitest';
import { getPackRecord, getPackRecordWithMeta, putPackRecord, resetVideoPackStoreForTests, seedVideoPackRecordForTests, setVideoPackRedisForTests, type VideoPackRecord } from '@/lib/video-pack-store';
const id = 'auJzb1D-fag';
const hash = 'a'.repeat(64);
const source = `https://www.youtube.com/watch?v=${id}`;
const processing = { state: 'processing' as const, id: `vp:v0:${id}`, video_id: id, source_url: source, source_hash: hash, started_at: new Date().toISOString() };
afterEach(() => { resetVideoPackStoreForTests(); vi.unstubAllEnvs(); });
it('rejects poisoned memory records at the shared read boundary', async () => {
  seedVideoPackRecordForTests({ ...processing, source_url: 'https://attacker.example/video' });
  expect(await getPackRecord(hash)).toBeNull();
});
it('rejects poisoned ready Redis records and never caches them', async () => {
  const poisoned = { state: 'ready', pack: { video_id: id, source_url: 'https://attacker.example/video', provenance: { source_hash: hash }, transcript: { full_text: 'hostile' } } } as VideoPackRecord;
  setVideoPackRedisForTests({ get: async <T>() => poisoned as T, set: async () => 'OK', eval: async <T>() => null as T });
  expect((await getPackRecordWithMeta(hash)).outcome).toBe('miss');
  setVideoPackRedisForTests(null);
  expect(await getPackRecord(hash)).toBeNull();
});
it('rejects poisoned writes without changing a valid memory record', async () => {
  setVideoPackRedisForTests(null);
  await putPackRecord(processing);
  await expect(putPackRecord({ ...processing, source_url: 'https://attacker.example/video' })).rejects.toThrow(/requires review/);
  expect(await getPackRecord(hash)).toEqual(processing);
});
