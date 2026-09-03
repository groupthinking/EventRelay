import { afterEach, describe, expect, it, vi } from 'vitest';
import { GOLDEN_IDENTITY_HASHES, identityHash } from '@/lib/video-pack';
import { VideoPackExtractError } from '@/lib/video-pack-extractor';

const CANON_A = 'auJzb1D-fag';
const CANON_B = 'jNQXAC9IVRw';

const { extractVideoPackSpec } = vi.hoisted(() => ({
  extractVideoPackSpec: vi.fn(),
}));

vi.mock('@/lib/video-pack-extractor', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/video-pack-extractor')>();
  return {
    ...actual,
    extractVideoPackSpec,
  };
});

function specFor(videoId: string) {
  return {
    transcript: {
      language: 'en',
      full_text: `Spoken content from ${videoId} with enough extracted speech.`,
      segments: [{ idx: 0, start_s: 0, end_s: 4, text: `Spoken content from ${videoId}.` }],
    },
    keyframes: [{ t_s: 1, desc: `Keyframe from ${videoId}` }],
    concepts: [`topic-${videoId}`],
    requirements: [{ id: 'req-1', title: 'Watch the clip', detail: null, priority: 'normal', tags: [] }],
    code_snippets: [],
    visual_context: {
      visual_elements: [
        { timestamp: 1, element_type: 'scene', content: `Visual from ${videoId}`, confidence: 0.9 },
      ],
      summary: `Spec extract for ${videoId}`,
      frame_analysis_count: 1,
    },
  };
}

afterEach(() => {
  extractVideoPackSpec.mockReset();
  vi.resetModules();
  vi.unstubAllGlobals();
});

function postRequest(body: unknown) {
  return new Request('http://localhost:3000/api/video/pack', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('POST /api/video/pack', () => {
  it('returns 400 when no YouTube URL or video id is provided', async () => {
    const { POST } = await import('../route');
    const res = await POST(postRequest({}));
    expect(res.status).toBe(400);
    const body = (await res.json()) as { error?: string };
    expect(body.error).toMatch(/video/i);
    expect(extractVideoPackSpec).not.toHaveBeenCalled();
  });

  it('fails closed with a visible error when Gateway extract is unavailable', async () => {
    extractVideoPackSpec.mockRejectedValueOnce(
      new VideoPackExtractError(
        'Video pack spec extract requires AI Gateway (AI_GATEWAY_API_KEY or VERCEL_AI_GATEWAY_API_KEY) and model google/gemini-3.8-flash.',
      ),
    );
    const { POST } = await import('../route');
    const res = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }));
    expect(res.status).toBe(503);
    const body = (await res.json()) as { status?: string; error?: string; data?: unknown };
    expect(body.status).toBe('error');
    expect(body.error).toMatch(/AI Gateway/i);
    expect(body.error).toContain('google/gemini-3.8-flash');
    expect(body.data).toBeUndefined();
  });

  it('emits a spec pack whose identity hash is stable for the same video ID', async () => {
    extractVideoPackSpec.mockImplementation(async ({ videoId }: { videoId: string }) => specFor(videoId));
    const { POST } = await import('../route');
    const first = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }));
    const second = await POST(postRequest({ youtubeUrl: 'https://youtu.be/auJzb1D-fag?si=retry' }));
    expect(first.status).toBe(200);
    expect(second.status).toBe(200);

    const a = (await first.json()) as { status: string; data: Record<string, unknown> };
    const b = (await second.json()) as { status: string; data: Record<string, unknown> };
    const hashA = (a.data.provenance as { source_hash: string }).source_hash;
    const hashB = (b.data.provenance as { source_hash: string }).source_hash;
    const transcript = a.data.transcript as { full_text: string };

    expect(a.status).toBe('success');
    expect(a.data.version).toBe('v0');
    expect(a.data.video_id).toBe(CANON_A);
    expect(a.data.id).toBe(`vp:v0:${CANON_A}`);
    expect(a.data.source_url).toBe('https://www.youtube.com/watch?v=auJzb1D-fag');
    expect(hashA).toBe(GOLDEN_IDENTITY_HASHES[CANON_A]);
    expect(hashA).toBe(identityHash(CANON_A));
    expect(hashA).toBe(hashB);
    expect(a.data.id).toBe(b.data.id);
    expect(transcript.full_text).not.toBe(`cite:youtube:${CANON_A}`);
    expect(a.data.concepts).toEqual([`topic-${CANON_A}`]);
    expect(extractVideoPackSpec).toHaveBeenCalledWith(
      expect.objectContaining({
        sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
        videoId: CANON_A,
      }),
    );
  });

  it('emits a different hash for a different video ID', async () => {
    extractVideoPackSpec.mockImplementation(async ({ videoId }: { videoId: string }) => specFor(videoId));
    const { POST } = await import('../route');
    const resA = await POST(postRequest({ video_url: `https://youtu.be/${CANON_A}` }));
    const resB = await POST(postRequest({ video_id: CANON_B }));
    const packA = (await resA.json()) as { data: { provenance: { source_hash: string }; video_id: string } };
    const packB = (await resB.json()) as { data: { provenance: { source_hash: string }; video_id: string } };

    expect(packA.data.video_id).toBe(CANON_A);
    expect(packB.data.video_id).toBe(CANON_B);
    expect(packA.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_A]);
    expect(packB.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(packA.data.provenance.source_hash).not.toBe(packB.data.provenance.source_hash);
  });
});
