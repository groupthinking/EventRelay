import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import {
  GOLDEN_IDENTITY_HASHES,
  identityHash,
  identityPayload,
  resolveYouTubeVideoId,
} from '@/lib/video-pack';

const CANON_A = 'auJzb1D-fag';
const CANON_B = 'jNQXAC9IVRw';

describe('video-pack identity', () => {
  it('encodes compact sorted JSON matching the Python contract', () => {
    expect(JSON.stringify(identityPayload(CANON_A), Object.keys(identityPayload(CANON_A)).sort())).toBe(
      '{"version":"v0","video_id":"auJzb1D-fag"}',
    );
  });

  it('returns the same hash for the same video ID', () => {
    expect(identityHash(CANON_A)).toBe(identityHash(CANON_A));
    expect(identityHash(CANON_A)).toBe(GOLDEN_IDENTITY_HASHES[CANON_A]);
  });

  it('returns a different hash for a different video ID', () => {
    expect(identityHash(CANON_A)).not.toBe(identityHash(CANON_B));
    expect(identityHash(CANON_B)).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
  });

  it('is SHA-256 of the compact canonical payload', () => {
    const digest = createHash('sha256')
      .update('{"version":"v0","video_id":"auJzb1D-fag"}')
      .digest('hex');
    expect(identityHash(CANON_A)).toBe(digest);
  });

  it('collapses URL variants to one video ID', () => {
    expect(resolveYouTubeVideoId('https://www.youtube.com/watch?v=auJzb1D-fag')).toBe(CANON_A);
    expect(resolveYouTubeVideoId('https://youtu.be/auJzb1D-fag?si=abc')).toBe(CANON_A);
    expect(resolveYouTubeVideoId('https://www.youtube.com/shorts/auJzb1D-fag')).toBe(CANON_A);
    expect(resolveYouTubeVideoId(CANON_A)).toBe(CANON_A);
  });

  it('rejects a non-YouTube URL', () => {
    expect(resolveYouTubeVideoId('https://example.com/watch')).toBeNull();
  });
});
