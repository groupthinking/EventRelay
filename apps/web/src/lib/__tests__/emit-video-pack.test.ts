import { describe, expect, it } from 'vitest';
import { GOLDEN_IDENTITY_HASHES } from '@/lib/video-pack';
import { identityPackJson, verifyIdentityPack } from '@/lib/emit-video-pack';

const CANON = 'jNQXAC9IVRw';
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;
const HASH = GOLDEN_IDENTITY_HASHES[CANON];

const VALID = {
  status: 'success',
  data: {
    version: 'v0',
    id: `vp:v0:${CANON}`,
    video_id: CANON,
    source_url: SOURCE_URL,
    transcript: { full_text: `cite:youtube:${CANON}`, segments: [] },
    provenance: { source_hash: HASH },
  },
};

describe('verifyIdentityPack (CoS: fail closed)', () => {
  it('accepts a v0 pack with source_url and source_hash', () => {
    const citation = verifyIdentityPack(VALID);
    expect(citation.sourceUrl).toBe(SOURCE_URL);
    expect(citation.sourceHash).toBe(HASH);
    expect(citation.videoId).toBe(CANON);
    expect(citation.pack.source_url).toBe(SOURCE_URL);
    expect(citation.pack.provenance.source_hash).toBe(HASH);
    expect(identityPackJson(citation)).toContain(SOURCE_URL);
    expect(identityPackJson(citation)).toContain(HASH);
  });

  it('fails closed when source_url is missing', () => {
    const { source_url: _omit, ...data } = VALID.data;
    expect(() => verifyIdentityPack({ status: 'success', data })).toThrow(/source_url/i);
  });

  it('fails closed when source_hash is missing', () => {
    expect(() =>
      verifyIdentityPack({
        status: 'success',
        data: { ...VALID.data, provenance: {} },
      }),
    ).toThrow(/source_hash/i);
  });

  it('fails closed on an empty or 401 payload', () => {
    expect(() => verifyIdentityPack({ error: 'Authentication required' })).toThrow(/verif/i);
    expect(() => verifyIdentityPack(null)).toThrow(/verif/i);
  });
});
