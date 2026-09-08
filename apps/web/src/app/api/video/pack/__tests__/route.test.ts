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
    artifacts: [],
    stack: { tools: [] },
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

function getRequest(query: string) {
  return new Request(`http://localhost:3000/api/video/pack?${query}`, {
    method: 'GET',
  });
}

async function loadPackRoute() {
  const scheduled: Promise<unknown>[] = [];
  const videoPack = await import('@/lib/video-pack');
  const store = await import('@/lib/video-pack-store');
  store.resetVideoPackStoreForTests();
  videoPack.setVideoPackSchedulerForTests((work) => {
    scheduled.push(work);
  });
  const route = await import('../route');
  return {
    POST: route.POST,
    GET: route.GET,
    scheduled,
    flush: async () => {
      await Promise.all(scheduled.splice(0));
    },
    seedVideoPackRecordForTests: store.seedVideoPackRecordForTests,
    buildIdentityPack: videoPack.buildIdentityPack,
    applyExtractedSpec: videoPack.applyExtractedSpec,
  };
}

describe('POST /api/video/pack', () => {
  it('returns 400 when no YouTube URL or video id is provided', async () => {
    const { POST } = await loadPackRoute();
    const res = await POST(postRequest({}));
    expect(res.status).toBe(400);
    const body = (await res.json()) as { error?: string };
    expect(body.error).toMatch(/video/i);
    expect(extractVideoPackSpec).not.toHaveBeenCalled();
  });

  it('returns processing immediately and does not block on extract', async () => {
    let finish: ((spec: ReturnType<typeof specFor>) => void) | undefined;
    extractVideoPackSpec.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const { POST, GET, scheduled } = await loadPackRoute();
    const res = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' }));
    expect(res.status).toBe(202);
    const body = (await res.json()) as {
      status?: string;
      data?: { video_id?: string; provenance?: { source_hash?: string }; transcript?: { full_text?: string } };
    };
    expect(body.status).toBe('processing');
    expect(body.data?.video_id).toBe(CANON_B);
    expect(body.data?.provenance?.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(body.data?.transcript).toBeUndefined();
    expect(scheduled).toHaveLength(1);

    const peek = await GET(getRequest(`source_hash=${GOLDEN_IDENTITY_HASHES[CANON_B]}`));
    expect(peek.status).toBe(202);

    finish?.(specFor(CANON_B));
  });

  it('fails closed with a visible error when Gateway extract is unavailable', async () => {
    extractVideoPackSpec.mockRejectedValue(
      new VideoPackExtractError(
        'Video pack spec extract requires AI Gateway (AI_GATEWAY_API_KEY or VERCEL_AI_GATEWAY_API_KEY) and model google/gemini-3.8-flash.',
      ),
    );
    const { POST, GET, flush } = await loadPackRoute();
    const accepted = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }));
    expect(accepted.status).toBe(202);
    await flush();

    const res = await GET(getRequest(`video_id=${CANON_A}`));
    expect(res.status).toBe(503);
    const body = (await res.json()) as { status?: string; error?: string; data?: unknown };
    expect(body.status).toBe('error');
    expect(body.error).toMatch(/AI Gateway/i);
    expect(body.error).toContain('google/gemini-3.8-flash');
    expect(body.data).toBeUndefined();
  });

  it('returns a cached spec pack without calling the model', async () => {
    const loaded = await loadPackRoute();
    const identity = loaded.buildIdentityPack(CANON_B, `https://www.youtube.com/watch?v=${CANON_B}`, '2026-09-03T00:00:00.000Z');
    const pack = loaded.applyExtractedSpec(identity, specFor(CANON_B));
    loaded.seedVideoPackRecordForTests({ state: 'ready', pack });

    const res = await loaded.POST(postRequest({ url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' }));
    expect(res.status).toBe(200);
    const body = (await res.json()) as { status: string; data: { concepts: string[]; provenance: { source_hash: string } } };
    expect(body.status).toBe('success');
    expect(body.data.concepts).toEqual([`topic-${CANON_B}`]);
    expect(body.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(extractVideoPackSpec).not.toHaveBeenCalled();
    expect(loaded.scheduled).toHaveLength(0);
  });

  it('emits a spec pack whose identity hash is stable for the same video ID', async () => {
    extractVideoPackSpec.mockImplementation(async ({ videoId }: { videoId: string }) => specFor(videoId));
    const { POST, flush } = await loadPackRoute();
    const first = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }));
    expect(first.status).toBe(202);
    await flush();

    const ready = await POST(postRequest({ youtubeUrl: 'https://youtu.be/auJzb1D-fag?si=retry' }));
    expect(ready.status).toBe(200);
    const a = (await first.json()) as { status: string; data: { provenance: { source_hash: string } } };
    const b = (await ready.json()) as {
      status: string;
      data: Record<string, unknown> & { provenance: { source_hash: string }; transcript: { full_text: string } };
    };

    expect(a.status).toBe('processing');
    expect(a.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_A]);
    expect(b.status).toBe('success');
    expect(b.data.version).toBe('v0');
    expect(b.data.video_id).toBe(CANON_A);
    expect(b.data.id).toBe(`vp:v0:${CANON_A}`);
    expect(b.data.source_url).toBe('https://www.youtube.com/watch?v=auJzb1D-fag');
    expect(b.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_A]);
    expect(b.data.provenance.source_hash).toBe(identityHash(CANON_A));
    expect(b.data.transcript.full_text).not.toBe(`cite:youtube:${CANON_A}`);
    expect(b.data.concepts).toEqual([`topic-${CANON_A}`]);
    expect(extractVideoPackSpec).toHaveBeenCalledTimes(1);
    expect(extractVideoPackSpec).toHaveBeenCalledWith(
      expect.objectContaining({
        sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
        videoId: CANON_A,
      }),
    );
  });

  it('emits a different hash for a different video ID', async () => {
    extractVideoPackSpec.mockImplementation(async ({ videoId }: { videoId: string }) => specFor(videoId));
    const { POST, flush } = await loadPackRoute();
    const acceptedA = await POST(postRequest({ video_url: `https://youtu.be/${CANON_A}` }));
    const acceptedB = await POST(postRequest({ video_id: CANON_B }));
    expect(acceptedA.status).toBe(202);
    expect(acceptedB.status).toBe(202);
    await flush();

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

describe('GET /api/video/pack (anonymous read)', () => {
  it('returns the finished spec pack by source_hash without auth', async () => {
    extractVideoPackSpec.mockImplementation(async ({ videoId }: { videoId: string }) => specFor(videoId));
    const { POST, GET, flush } = await loadPackRoute();
    await POST(postRequest({ url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' }));
    await flush();

    const res = await GET(getRequest(`source_hash=${GOLDEN_IDENTITY_HASHES[CANON_B]}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status: string;
      data: { video_id: string; concepts: string[]; provenance: { source_hash: string }; transcript: { full_text: string } };
    };
    expect(body.status).toBe('success');
    expect(body.data.video_id).toBe(CANON_B);
    expect(body.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(body.data.transcript.full_text).not.toBe(`cite:youtube:${CANON_B}`);
    expect(body.data.concepts).toEqual([`topic-${CANON_B}`]);
  });

  it('does not serve an identity-only pack as success after cite-only extract', async () => {
    extractVideoPackSpec.mockRejectedValue(new VideoPackExtractError('Gemini 3.8 Flash returned no extracted spec content.'));
    const { POST, GET, flush } = await loadPackRoute();
    await POST(postRequest({ video_id: CANON_B }));
    await flush();

    const res = await GET(getRequest(`video_id=${CANON_B}`));
    expect(res.status).toBe(503);
    const body = (await res.json()) as { status?: string; error?: string; data?: { transcript?: { full_text?: string } } };
    expect(body.status).toBe('error');
    expect(body.error).toMatch(/no extracted spec/i);
    expect(body.data?.transcript?.full_text).not.toBe(`cite:youtube:${CANON_B}`);
  });
});
