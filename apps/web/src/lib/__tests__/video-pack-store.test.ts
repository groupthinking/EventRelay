import { afterEach, describe, expect, it } from 'vitest';
import { GOLDEN_IDENTITY_HASHES, applyExtractedSpec, buildIdentityPack } from '@/lib/video-pack';
import {
  claimPackProcessing,
  getPackRecord,
  putPackRecord,
  resetVideoPackStoreForTests,
} from '@/lib/video-pack-store';

const CANON = 'jNQXAC9IVRw';
const HASH = GOLDEN_IDENTITY_HASHES[CANON];
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;

function readyPack() {
  const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
  return applyExtractedSpec(identity, {
    transcript: {
      language: 'en',
      full_text: 'Me at the zoo.',
      segments: [{ idx: 0, start_s: 0, end_s: 5, text: 'Me at the zoo.' }],
    },
    keyframes: [{ t_s: 1, desc: 'Elephants' }],
    concepts: ['zoo'],
    requirements: [],
    code_snippets: [],
    artifacts: [],
    stack: { tools: [] },
    visual_context: null,
  });
}

afterEach(() => {
  resetVideoPackStoreForTests();
});

describe('video-pack store', () => {
  it('returns null for an unknown source_hash', async () => {
    expect(await getPackRecord(HASH)).toBeNull();
  });

  it('round-trips a ready spec pack keyed by source_hash', async () => {
    const pack = readyPack();
    expect(pack.provenance.source_hash).toBe(HASH);
    await putPackRecord({ state: 'ready', pack });
    const loaded = await getPackRecord(HASH);
    expect(loaded?.state).toBe('ready');
    if (loaded?.state !== 'ready') {
      throw new Error('expected ready pack');
    }
    expect(loaded.pack.provenance.source_hash).toBe(HASH);
    expect(loaded.pack.transcript.full_text).toBe('Me at the zoo.');
    expect(loaded.pack.concepts).toEqual(['zoo']);
  });

  it('claims processing once for the same hash', async () => {
    const first = await claimPackProcessing({
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
    });
    expect(first).toBe('claimed');
    const second = await claimPackProcessing({
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
    });
    expect(second).not.toBe('claimed');
    if (second === 'claimed') {
      throw new Error('second claim should see the in-flight record');
    }
    expect(second.state).toBe('processing');
  });

  it('reclaims after a stored extract error so a later POST can retry', async () => {
    await putPackRecord({
      state: 'error',
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
      error: 'Gemini 3.8 Flash returned no extracted spec content.',
      failed_at: '2026-09-03T00:00:00.000Z',
    });
    const claimed = await claimPackProcessing({
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
    });
    expect(claimed).toBe('claimed');
    const next = await getPackRecord(HASH);
    expect(next?.state).toBe('processing');
  });
});
