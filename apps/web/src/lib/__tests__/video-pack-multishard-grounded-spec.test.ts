import { describe, expect, it, vi } from 'vitest';
import { applyExtractedSpec, buildIdentityPack } from '@/lib/video-pack';
import { extractVideoPackSpec } from '@/lib/video-pack-extractor';
import {
  REAL_AUJ_GROUNDED_SPEC,
  REAL_AUJ_SOURCE_HASH,
  REAL_AUJ_SOURCE_URL,
  REAL_AUJ_TRANSCRIPT_ROWS,
  REAL_AUJ_VIDEO_ID,
  REAL_AUJ_VISUAL_ROWS,
} from '@/test/real-aujzb1d-fag-evidence';

vi.mock('@/lib/youtube-metadata', () => ({
  preflightYouTubeVideoSource: vi.fn(async () => 'available'),
  fetchYouTubeMetadata: vi.fn(async () => ({
    videoId: REAL_AUJ_VIDEO_ID,
    title: 'Google AI Studio: multimodal capabilities',
    channel: 'Google Cloud',
    description: '',
    chapters: [],
    durationSeconds: 481,
  })),
}));

vi.mock('@/lib/youtube-captions', () => ({
  fetchYouTubeCaptions: vi.fn(async () => null),
}));

function sectionPayload(start_s: number, includeGroundedSpec: boolean): Record<string, unknown> {
  const rows = start_s === 180 ? [REAL_AUJ_TRANSCRIPT_ROWS[0]!] : start_s === 360 ? REAL_AUJ_TRANSCRIPT_ROWS.slice(1) : [];
  const visuals = start_s === 180 ? [REAL_AUJ_VISUAL_ROWS[0]!] : start_s === 360 ? REAL_AUJ_VISUAL_ROWS.slice(1) : [];
  const requirements = start_s === 180
    ? [{ id: 'sec2-req-1', title: 'Attach a YouTube video', detail: 'Attach the source video in the prompt.', priority: 'high', tags: ['video'] }]
    : start_s === 360
      ? [{ id: 'sec3-req-1', title: 'Render a detailed summary', detail: 'Show the structured result.', priority: 'high', tags: ['summary'] }]
      : [];
  const action_items = start_s === 180
    ? [{ id: 'ACT-01', type: 'explore', title: 'Open Google AI Studio and attach video URL', description: 'Attach the video and inspect the token count.', difficulty: 'easy' }]
    : start_s === 360
      ? [{ id: 'ACT-02', type: 'prompt', title: 'Query long video context with structured prompt', description: 'Ask for key sections and evidence.', difficulty: 'easy' }, { id: 'ACT-03', type: 'prototype', title: 'Test Spatial Understanding demo app in Build tab', description: 'Review the generated bounding boxes and code.', difficulty: 'medium' }]
      : [];

  const payload: Record<string, unknown> = {
    transcript: {
      language: 'en',
      full_text: rows.map((row) => row.text).join(' '),
      segments: rows.map((row, idx) => ({ ...row, idx })),
    },
    keyframes: [], concepts: [], requirements, code_snippets: [], architecture: null,
    artifacts: [], stack: { tools: [] },
    visual_context: visuals.length > 0 ? { visual_elements: visuals, summary: null, frame_analysis_count: visuals.length } : null,
    chapters: [], action_items,
  };

  if (!includeGroundedSpec || start_s === 0) return payload;

  const requirementIndexes = start_s === 180 ? [0] : [1, 2];
  const grounded = structuredClone(REAL_AUJ_GROUNDED_SPEC);
  grounded.sourceStatus = 'partial';
  grounded.requirements = requirementIndexes.map((index) => {
    const requirement = grounded.requirements[index]!;
    return {
      ...requirement,
      citations: requirement.citations.map((citation) => ({
        ...citation,
        index: citation.kind === 'transcript'
          ? rows.findIndex((row) => row.start_s === citation.startSeconds)
          : visuals.findIndex((row) => row.timestamp === citation.startSeconds),
      })),
    };
  });
  grounded.acceptanceCriteria = grounded.acceptanceCriteria.filter((criterion) => requirementIndexes.includes(Number(criterion.requirementId.slice(-2)) - 1));
  grounded.unresolved = start_s === 180
    ? grounded.unresolved.map((row) => ({ ...row, requirementIds: ['G-REQ-01'] }))
    : [];
  grounded.unsupported = start_s === 180 ? grounded.unsupported : [];
  payload.grounded_spec = grounded;
  return payload;
}

describe('multi-shard grounded specification preservation', () => {
  it('keeps real auJzb1D-fag requirements, citations, digest input, and proposed work through consolidation', async () => {
    const runVideo = vi.fn(async (call: { start_s: number; sectionPrompt: string }) => ({
      text: JSON.stringify(sectionPayload(call.start_s, call.sectionPrompt.includes('Also emit grounded_spec as a partial'))),
      interactionId: `int-${call.start_s}`,
    }));

    const extracted = await extractVideoPackSpec(
      { sourceUrl: REAL_AUJ_SOURCE_URL, videoId: REAL_AUJ_VIDEO_ID },
      { hasDirectGoogleKey: () => true, runVideoInteraction: runVideo },
    );
    const pack = applyExtractedSpec(buildIdentityPack(REAL_AUJ_VIDEO_ID), extracted);

    expect(runVideo).toHaveBeenCalledTimes(3);
    expect(pack.provenance.source_hash).toBe(REAL_AUJ_SOURCE_HASH);
    expect(pack).toHaveProperty('grounded_spec.status', 'available');
    expect(pack.grounded_spec).toHaveProperty('contentHash', expect.stringMatching(/^[a-f0-9]{64}$/));
    expect(pack.grounded_spec?.status === 'available' ? pack.grounded_spec.spec.requirements : []).toHaveLength(3);
    expect(pack.grounded_spec?.status === 'available' ? pack.grounded_spec.spec.requirements.flatMap((req) => req.citations) : []).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ videoId: REAL_AUJ_VIDEO_ID, startSeconds: 344, endSeconds: 353 }),
        expect.objectContaining({ videoId: REAL_AUJ_VIDEO_ID, startSeconds: 379, endSeconds: 395 }),
      ]),
    );
    expect(pack.grounded_spec?.status === 'available' ? pack.grounded_spec.spec.acceptanceCriteria : []).toHaveLength(3);
    expect(pack.action_items).toHaveLength(3);
  });
});
