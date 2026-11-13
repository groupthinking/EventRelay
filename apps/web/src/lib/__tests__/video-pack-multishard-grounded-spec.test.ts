import { describe, expect, it, vi } from 'vitest';
import type { GroundedSpecCandidate } from '@/lib/grounded-build-spec';
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

function sectionPayload(start_s: number, includeGroundedSpec: boolean) {
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

  const payload = {
    transcript: {
      language: 'en',
      full_text: rows.map((row) => row.text).join(' '),
      segments: rows.map((row, idx) => ({ ...row, idx })),
    },
    keyframes: [], concepts: [], requirements, code_snippets: [], architecture: null,
    artifacts: [], stack: { tools: [] },
    visual_context: visuals.length > 0 ? { visual_elements: visuals.map((row) => ({ ...row })), summary: null, frame_analysis_count: visuals.length } : null,
    chapters: [], action_items,
    grounded_spec: undefined as GroundedSpecCandidate | undefined,
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

async function extractFixture(
  transform: (payload: ReturnType<typeof sectionPayload>, start: number) => unknown = (payload) => payload,
) {
  const runVideo = vi.fn(async (call: { start_s: number; sectionPrompt: string }) => ({
    text: JSON.stringify(transform(
      sectionPayload(call.start_s, call.sectionPrompt.includes('Also emit grounded_spec as a partial')),
      call.start_s,
    )),
    interactionId: `int-${call.start_s}`,
  }));
  const extracted = await extractVideoPackSpec(
    { sourceUrl: REAL_AUJ_SOURCE_URL, videoId: REAL_AUJ_VIDEO_ID },
    { hasDirectGoogleKey: () => true, runVideoInteraction: runVideo },
  );
  expect(runVideo).toHaveBeenCalledTimes(3);
  return applyExtractedSpec(buildIdentityPack(REAL_AUJ_VIDEO_ID), extracted);
}

describe('multi-shard grounded specification preservation', () => {
  it('reports aggregate overflow without truncating 66 grounded requirements', async () => {
    const pack = await extractFixture((payload, start) => {
      if (start === 0) {
        payload = sectionPayload(180, true);
        Object.assign(payload.transcript.segments[0]!, { start_s: 10, end_s: 11 });
        payload.visual_context!.visual_elements[0]!.timestamp = 10;
        for (const ref of payload.grounded_spec!.requirements[0]!.citations) {
          ref.startSeconds = 10;
          ref.endSeconds = ref.kind === 'transcript' ? 11 : 10;
        }
      }
      const spec = payload.grounded_spec!;
      const requirement = spec.requirements[0]!;
      const criterion = spec.acceptanceCriteria[0]!;
      spec.requirements = Array.from({ length: 22 }, (_, index) => ({ ...requirement, id: `req-${index}` }));
      spec.acceptanceCriteria = spec.requirements.map((row, index) => ({ ...criterion, id: `ac-${index}`, requirementId: row.id }));
      spec.unresolved = [];
      spec.unsupported = [];
      return payload;
    });
    expect(pack.grounded_spec).toMatchObject({ status: 'invalid', issues: expect.arrayContaining([
      expect.objectContaining({ code: 'aggregate-limit', path: 'requirements', message: expect.stringContaining('66') }),
    ]) });
  });

  it('uses complete application metadata from a later available shard', async () => {
    const pack = await extractFixture((payload, start) => {
      if (payload.grounded_spec && start === 180) payload.grounded_spec.app = { name: '', purpose: '' };
      return payload;
    });
    expect(pack.grounded_spec).toMatchObject({ status: 'available', spec: { app: REAL_AUJ_GROUNDED_SPEC.app } });
  });

  it('keeps real auJzb1D-fag requirements, citations, digest input, and proposed work through consolidation', async () => {
    const pack = await extractFixture();
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

  it('keeps colliding shard IDs distinct and rewrites every grounded reference', async () => {
    const sharedId = 'a'.repeat(64);
    const pack = await extractFixture((payload, start) => {
      const spec = payload.grounded_spec;
      if (!spec) return payload;
      const req = spec.requirements[0]!;
      const criterion = spec.acceptanceCriteria[0]!;
      req.id = sharedId;
      req.screenId = sharedId;
      criterion.id = sharedId;
      criterion.requirementId = sharedId;
      criterion.then = `Expected outcome in shard ${start}`;
      spec.screens[0] = { id: sharedId, name: `Screen in shard ${start}`, purpose: '' };
      spec.state[0] = { ...spec.state[0]!, id: sharedId, name: `State in shard ${start}` };
      spec.unresolved = [{ id: sharedId, requirementIds: [sharedId], question: `Question in shard ${start}`, required: start === 360 }];
      spec.unsupported = [{ id: sharedId, requirementIds: [sharedId], capability: 'server', reason: `Limit in shard ${start}`, required: true }];
      return payload;
    });

    expect(pack.grounded_spec?.status).toBe('available');
    if (pack.grounded_spec?.status !== 'available') throw new Error('Grounded spec unavailable');
    const spec = pack.grounded_spec.spec;
    expect(spec.requirements).toHaveLength(3);
    for (const [start, title] of [[180, REAL_AUJ_GROUNDED_SPEC.requirements[0]!.title], [360, REAL_AUJ_GROUNDED_SPEC.requirements[1]!.title]] as const) {
      const req = spec.requirements.find((row) => row.title === title);
      expect(req?.id).toMatch(/^[\w-]{1,64}$/);
      expect(spec.screens.find((row) => row.id === req?.screenId)?.name).toBe(`Screen in shard ${start}`);
      expect(spec.state.some((row) => row.name === `State in shard ${start}`)).toBe(true);
      expect(spec.acceptanceCriteria.find((row) => row.then === `Expected outcome in shard ${start}`)?.requirementId).toBe(req?.id);
      expect(spec.unresolved.find((row) => row.question === `Question in shard ${start}`)).toMatchObject({ requirementIds: [req?.id], required: start === 360 });
      expect(spec.unsupported.find((row) => row.reason === `Limit in shard ${start}`)?.requirementIds).toEqual([req?.id]);
    }
  });

  it('rebases raw transcript and visual indices when the parser filters preceding rows', async () => {
    const pack = await extractFixture((payload, start) => {
      if (start !== 360 || !payload.grounded_spec || !payload.visual_context) return payload;
      for (const req of payload.grounded_spec.requirements) {
        for (const ref of req.citations) ref.index += 2;
      }
      return {
        ...payload,
        transcript: { ...payload.transcript, segments: [null, { text: '' }, ...payload.transcript.segments] },
        visual_context: { ...payload.visual_context, visual_elements: [null, { content: '' }, ...payload.visual_context.visual_elements] },
      };
    });
    expect(pack.grounded_spec).toMatchObject({
      status: 'available',
      spec: { requirements: expect.arrayContaining([expect.objectContaining({
        title: REAL_AUJ_GROUNDED_SPEC.requirements[2]!.title,
        citations: [expect.objectContaining({ index: 2, startSeconds: 438 }), expect.objectContaining({ index: 2, startSeconds: 455 })],
      })]) },
    });
  });

  it('keeps exact transcript and visual evidence when same-time rows differ only in case', async () => {
    const pack = await extractFixture((payload, start) => {
      if (!payload.grounded_spec || !payload.visual_context) return payload;
      const text = start === 180 ? 'Click Save' : 'Click save';
      const content = start === 180 ? 'Save button' : 'save button';
      Object.assign(payload.transcript.segments[0]!, { start_s: 360, end_s: 360, text });
      Object.assign(payload.visual_context.visual_elements[0]!, { timestamp: 360, content });
      const [transcript, visual] = payload.grounded_spec.requirements[0]!.citations;
      Object.assign(transcript!, { startSeconds: 360, endSeconds: 360, quote: text });
      Object.assign(visual!, { startSeconds: 360, endSeconds: 360, quote: content });
      return payload;
    });
    expect(pack.grounded_spec?.status).toBe('available');
    expect(pack.transcript.segments.map((row) => row.text)).toEqual(expect.arrayContaining(['Click Save', 'Click save']));
    expect(pack.visual_context?.visual_elements.map((row) => row.content)).toEqual(expect.arrayContaining(['Save button', 'save button']));
  });

  it.each([
    ['transcript before the shard', 'transcript', 179, 353],
    ['transcript past the shard end', 'transcript', 344, 361],
    ['visual before the shard', 'visual', 179, 179],
    ['visual past the shard end', 'visual', 361, 361],
  ] as const)('rejects cited %s even when it matches a response row', async (_, kind, startSeconds, endSeconds) => {
    const pack = await extractFixture((payload, start) => {
      if (start !== 180) return { ...payload, grounded_spec: undefined };
      const ref = payload.grounded_spec!.requirements[0]!.citations.find((row) => row.kind === kind)!;
      Object.assign(ref, { startSeconds, endSeconds });
      if (kind === 'transcript') {
        Object.assign(payload.transcript.segments[ref.index]!, { start_s: startSeconds, end_s: endSeconds });
      } else {
        payload.visual_context!.visual_elements[ref.index]!.timestamp = startSeconds;
      }
      return payload;
    });
    expect(pack.grounded_spec).toMatchObject({
      status: 'invalid',
      issues: expect.arrayContaining([expect.objectContaining({ code: 'out-of-range-citation' })]),
    });
  });
});
