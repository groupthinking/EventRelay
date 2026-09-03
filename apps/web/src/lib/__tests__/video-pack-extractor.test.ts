import { afterEach, describe, expect, it, vi } from 'vitest';
import { GOLDEN_IDENTITY_HASHES, applyExtractedSpec, buildIdentityPack } from '@/lib/video-pack';
import {
  VIDEO_PACK_EXTRACTOR_MODEL,
  VideoPackExtractError,
  extractVideoPackSpec,
  type VideoPackGenerateText,
} from '@/lib/video-pack-extractor';

const CANON = 'auJzb1D-fag';
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;

const SPEC_JSON = {
  transcript: {
    language: 'en',
    full_text: 'Me at the zoo. The elephants have really long trunks.',
    segments: [{ idx: 0, start_s: 0, end_s: 5.2, text: 'Me at the zoo.' }],
  },
  keyframes: [{ t_s: 1.2, desc: 'Elephants at the enclosure' }],
  concepts: ['zoo', 'elephants'],
  requirements: [
    {
      id: 'req-1',
      title: 'Show the enclosure',
      detail: 'The speaker points at the elephants.',
      priority: 'normal',
      tags: ['visual'],
    },
  ],
  code_snippets: [],
  visual_context: {
    visual_elements: [
      {
        timestamp: 1.2,
        element_type: 'scene',
        content: 'Elephants behind a fence',
        confidence: 0.9,
      },
    ],
    summary: 'Short zoo clip with elephants',
    frame_analysis_count: 1,
  },
};

afterEach(() => {
  delete process.env.AI_GATEWAY_API_KEY;
  delete process.env.VERCEL_AI_GATEWAY_API_KEY;
  vi.restoreAllMocks();
});

describe('VIDEO_PACK_EXTRACTOR_MODEL', () => {
  it('pins google/gemini-3.8-flash and does not default to 2.5-flash', () => {
    expect(VIDEO_PACK_EXTRACTOR_MODEL).toBe('google/gemini-3.8-flash');
    expect(VIDEO_PACK_EXTRACTOR_MODEL).not.toContain('2.5-flash');
  });
});

describe('extractVideoPackSpec', () => {
  it('fails closed when AI Gateway is not configured', async () => {
    delete process.env.AI_GATEWAY_API_KEY;
    delete process.env.VERCEL_AI_GATEWAY_API_KEY;
    const generateText = vi.fn();

    await expect(
      extractVideoPackSpec({ sourceUrl: SOURCE_URL, videoId: CANON }, { generateText }),
    ).rejects.toThrow(/AI Gateway/i);
    expect(generateText).not.toHaveBeenCalled();
  });

  it('calls generateText with google/gemini-3.8-flash and the YouTube video file', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const generateText = vi.fn<VideoPackGenerateText>(async () => ({
      text: JSON.stringify(SPEC_JSON),
    }));

    const spec = await extractVideoPackSpec(
      { sourceUrl: SOURCE_URL, videoId: CANON },
      { generateText },
    );

    expect(spec.transcript.full_text).toContain('elephants');
    expect(spec.concepts).toEqual(['zoo', 'elephants']);
    expect(generateText).toHaveBeenCalledTimes(1);
    const args = generateText.mock.calls[0]?.[0];
    expect(args).toBeDefined();
    if (!args) {
      throw new Error('generateText was not called');
    }
    expect(args.model).toBe('google/gemini-3.8-flash');
    const parts = args.messages[0]?.content ?? [];
    const filePart = parts.find((part) => part.type === 'file');
    expect(filePart && filePart.type === 'file' ? filePart.mediaType : undefined).toMatch(/^video\//);
    expect(filePart && filePart.type === 'file' ? String(filePart.data) : undefined).toBe(SOURCE_URL);
  });

  it('fails closed when Gateway returns empty or identity-only cite text', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    const generateText = vi.fn(async () => ({
      text: JSON.stringify({
        transcript: { language: null, full_text: `cite:youtube:${CANON}`, segments: [] },
        keyframes: [],
        concepts: [],
        requirements: [],
        code_snippets: [],
        visual_context: null,
      }),
    }));

    await expect(
      extractVideoPackSpec({ sourceUrl: SOURCE_URL, videoId: CANON }, { generateText }),
    ).rejects.toBeInstanceOf(VideoPackExtractError);
  });
});

describe('applyExtractedSpec', () => {
  it('keeps the identity hash contract and fills spec fields', () => {
    const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
    const merged = applyExtractedSpec(identity, SPEC_JSON);

    expect(merged.version).toBe('v0');
    expect(merged.video_id).toBe(CANON);
    expect(merged.source_url).toBe(SOURCE_URL);
    expect(merged.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON]);
    expect(merged.provenance.source_hash).toBe(identity.provenance.source_hash);
    expect(merged.transcript.full_text).not.toBe(`cite:youtube:${CANON}`);
    expect(merged.concepts).toEqual(['zoo', 'elephants']);
    expect(merged.requirements[0]?.title).toBe('Show the enclosure');
    expect(merged.keyframes[0]?.desc).toBe('Elephants at the enclosure');
    expect(merged.provenance.tool_versions.extractor).toBe('google/gemini-3.8-flash');
  });
});
