import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import {
  GOLDEN_IDENTITY_HASHES,
  VIDEO_PACK_EXTRACT_PIPELINE_VERSION,
  VIDEO_PACK_STRUCTURE_SCHEMA_VERSION,
  applyExtractedSpec,
  buildIdentityPack,
  identityHash,
  identityPayload,
  packNeedsExtractPipelineRefresh,
  packNeedsReextractOnPost,
  packNeedsStructuredRefresh,
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

  it('emits an identity pack without extracted speech', () => {
    const pack = buildIdentityPack(CANON_B);
    expect(pack.version).toBe('v0');
    expect(pack.video_id).toBe(CANON_B);
    expect(pack.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(pack.source_url).toBe(`https://www.youtube.com/watch?v=${CANON_B}`);
    expect(pack.transcript.full_text).toBe(`cite:youtube:${CANON_B}`);
    expect(pack.transcript.segments).toEqual([]);
  });
});

describe('pack structured refresh (B1c)', () => {
  const preB1Ready = () => {
    const identity = buildIdentityPack(CANON_B, undefined, '2026-09-11T00:00:00.000Z');
    const pack = applyExtractedSpec(identity, {
      transcript: {
        language: 'en',
        full_text: 'Cached speech before structured schema.',
        segments: [{ idx: 0, start_s: 0, end_s: 4, text: 'Cached speech.' }],
      },
      keyframes: [],
      concepts: ['cached'],
      requirements: [{ id: 'r1', title: 'Do something', detail: null, priority: 'normal', tags: [] }],
      code_snippets: [],
      artifacts: [],
      stack: { tools: [] },
      visual_context: null,
    });
    delete pack.provenance.tool_versions.pack_structure;
    pack.chapters = [];
    pack.action_items = [];
    return pack;
  };

  it('flags pre-B1 ready packs missing pack_structure marker', () => {
    expect(packNeedsStructuredRefresh(preB1Ready())).toBe(true);
  });

  it('does not refresh identity-only or current-schema packs', () => {
    expect(packNeedsStructuredRefresh(buildIdentityPack(CANON_A))).toBe(false);
    const current = preB1Ready();
    current.provenance.tool_versions.pack_structure = VIDEO_PACK_STRUCTURE_SCHEMA_VERSION;
    current.chapters = [{ start: 0, end: 10, topic: 'Intro', key_points: ['Point'] }];
    current.action_items = [
      {
        id: 'a1',
        type: 'implementation',
        title: 'Ship',
        description: 'Do the thing',
        difficulty: 'easy',
        priority: null,
      },
    ];
    expect(packNeedsStructuredRefresh(current)).toBe(false);
  });
});

describe('pack extract pipeline refresh (C1)', () => {
  it('flags ready packs missing extract_pipeline marker', () => {
    const identity = buildIdentityPack(CANON_A);
    const pack = applyExtractedSpec(identity, {
      transcript: {
        language: 'en',
        full_text: 'Cached speech before C1 retry pipeline.',
        segments: [{ idx: 0, start_s: 0, end_s: 4, text: 'Cached speech.' }],
      },
      keyframes: [],
      concepts: ['cached'],
      requirements: [],
      code_snippets: [],
      artifacts: [],
      stack: { tools: [] },
      visual_context: null,
    });
    delete pack.provenance.tool_versions.extract_pipeline;
    expect(packNeedsExtractPipelineRefresh(pack)).toBe(true);
    expect(packNeedsReextractOnPost(pack)).toBe(true);
  });

  it('does not refresh packs stamped with the current extract pipeline', () => {
    const identity = buildIdentityPack(CANON_A);
    const pack = applyExtractedSpec(identity, {
      transcript: {
        language: 'en',
        full_text: 'Current pipeline speech.',
        segments: [{ idx: 0, start_s: 0, end_s: 4, text: 'Current pipeline speech.' }],
      },
      keyframes: [],
      concepts: ['cached'],
      requirements: [],
      code_snippets: [],
      artifacts: [],
      stack: { tools: [] },
      visual_context: null,
    });
    expect(pack.provenance.tool_versions.extract_pipeline).toBe(VIDEO_PACK_EXTRACT_PIPELINE_VERSION);
    expect(packNeedsExtractPipelineRefresh(pack)).toBe(false);
  });
});
