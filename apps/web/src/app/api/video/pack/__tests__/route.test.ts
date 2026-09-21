import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  GOLDEN_IDENTITY_HASHES,
  KEYFRAME_IMAGES_OK,
  KEYFRAME_IMAGES_OK_NOTE,
  KEYFRAME_IMAGES_PARTIAL,
  KEYFRAME_IMAGES_PARTIAL_NOTE,
  identityHash,
} from '@/lib/video-pack';
import { KEYFRAME_JPEG_CONTENT_TYPE } from '@/lib/keyframe-frame-capture';
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
    chapters: [{ start: 0, end: 4, topic: 'Intro', key_points: ['Main idea'] }],
    action_items: [
      {
        id: 'action-1',
        type: 'implementation',
        title: `Act on ${videoId}`,
        description: 'Structured ship step from extract.',
        difficulty: 'easy' as const,
      },
    ],
  };
}

afterEach(() => {
  extractVideoPackSpec.mockReset();
  vi.resetModules();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
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
  const capture = await import('@/lib/keyframe-frame-capture');
  capture.resetKeyframeFrameCaptureForTests();
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
    setKeyframeFrameCaptureForTests: capture.setKeyframeFrameCaptureForTests,
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

  it('does not return 202 in production when Redis durability is unavailable', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('UPSTASH_REDIS_REST_URL', '');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
    vi.stubEnv('KV_REST_API_URL', '');
    vi.stubEnv('KV_REST_API_TOKEN', '');

    const { POST, scheduled } = await loadPackRoute();
    const res = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' }));

    expect(res.status).toBe(503);
    const body = (await res.json()) as { status?: string; error?: string };
    expect(body.status).toBe('error');
    expect(body.error).toMatch(/durable video pack storage is not configured/i);
    expect(scheduled).toHaveLength(0);
    expect(extractVideoPackSpec).not.toHaveBeenCalled();
  });

  it('fails closed with a visible error when direct video extract is unavailable', async () => {
    extractVideoPackSpec.mockRejectedValue(
      new VideoPackExtractError(
        'Video pack spec extract requires direct Google video access and model gemini-3.8-flash.',
      ),
    );
    const { POST, GET, flush } = await loadPackRoute();
    const accepted = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }));
    expect(accepted.status).toBe(202);
    await flush();

    const res = await GET(getRequest(`video_id=${CANON_A}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      ok?: boolean;
      reason_code?: string;
      detail?: string;
      status?: string;
      error?: string;
      data?: unknown;
    };
    expect(body.ok).toBe(false);
    expect(body.reason_code).toBe('HOSTED_PACK_EXTRACT_FAILED');
    expect(body.detail).toMatch(/direct Google video access/i);
    expect(body.detail).toContain('gemini-3.8-flash');
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

  it('re-extracts a pre-B1 cached pack on Run (structured schema refresh)', async () => {
    extractVideoPackSpec.mockImplementation(async ({ videoId }: { videoId: string }) => specFor(videoId));
    const loaded = await loadPackRoute();
    const identity = loaded.buildIdentityPack(
      CANON_B,
      `https://www.youtube.com/watch?v=${CANON_B}`,
      '2026-09-11T00:00:00.000Z',
    );
    const stale = loaded.applyExtractedSpec(identity, {
      ...specFor(CANON_B),
      chapters: [],
      action_items: [],
    });
    delete stale.provenance.tool_versions.pack_structure;
    loaded.seedVideoPackRecordForTests({ state: 'ready', pack: stale });

    const res = await loaded.POST(postRequest({ url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' }));
    expect(res.status).toBe(202);
    expect(loaded.scheduled).toHaveLength(1);
    await loaded.flush();

    const ready = await loaded.GET(getRequest(`video_id=${CANON_B}`));
    expect(ready.status).toBe(200);
    const body = (await ready.json()) as {
      data?: {
        chapters?: Array<{ topic?: string }>;
        action_items?: Array<{ title?: string }>;
        provenance?: { tool_versions?: Record<string, string> };
      };
    };
    expect(body.data?.chapters?.[0]?.topic).toBe('Intro');
    expect(body.data?.action_items?.[0]?.title).toMatch(/Act on/);
    expect(body.data?.provenance?.tool_versions?.pack_structure).toBeDefined();
    expect(extractVideoPackSpec).toHaveBeenCalledTimes(1);
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

  it('annotates stored null image_path keyframes as PARTIAL without inventing URLs', async () => {
    const loaded = await loadPackRoute();
    const identity = loaded.buildIdentityPack(
      CANON_B,
      `https://www.youtube.com/watch?v=${CANON_B}`,
      '2026-09-12T16:39:08.716Z',
    );
    const pack = loaded.applyExtractedSpec(identity, specFor(CANON_B));
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: {
        ...pack,
        keyframes: [
          { t_s: 1, image_path: null, desc: `Keyframe from ${CANON_B}` },
          { t_s: 12, image_path: null, desc: 'Second described frame' },
        ],
        metrics: {},
        provenance: {
          ...pack.provenance,
          notes: 'Identity pack plus Gemini 3.8 Flash spec extract via AI Gateway.',
        },
      },
    });

    const res = await loaded.GET(getRequest(`video_id=${CANON_B}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status: string;
      data: {
        keyframes: Array<{ t_s: number; image_path?: string | null; desc?: string | null }>;
        metrics: Record<string, number | string>;
        provenance: { source_hash: string; notes: string };
      };
    };
    expect(body.status).toBe('success');
    expect(body.data.keyframes).toHaveLength(2);
    expect(body.data.keyframes.every((frame) => frame.image_path === null)).toBe(true);
    expect(body.data.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_PARTIAL);
    expect(body.data.provenance.notes).toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(body.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(JSON.stringify(body.data.keyframes)).not.toMatch(/https?:\/\//);
    expect(JSON.stringify(body.data.keyframes)).not.toMatch(/i\.ytimg\.com/);
  });

  it('hydrates stored null keyframes with captured app-served paths and seals ok', async () => {
    const loaded = await loadPackRoute();
    loaded.setKeyframeFrameCaptureForTests(async ({ videoId, t_s }) => ({
      bytes: Uint8Array.from([0xff, 0xd8, 0xff, 0xd9]),
      contentType: KEYFRAME_JPEG_CONTENT_TYPE,
      imagePath: `/api/video/pack/frames/${videoId}/${t_s}`,
    }));
    const identity = loaded.buildIdentityPack(
      CANON_B,
      `https://www.youtube.com/watch?v=${CANON_B}`,
      '2026-09-12T16:39:08.716Z',
    );
    const pack = loaded.applyExtractedSpec(identity, specFor(CANON_B));
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: {
        ...pack,
        keyframes: [
          { t_s: 1, image_path: null, desc: `Keyframe from ${CANON_B}` },
          { t_s: 12, image_path: null, desc: 'Second described frame' },
        ],
        metrics: { keyframes_images: KEYFRAME_IMAGES_PARTIAL },
        provenance: {
          ...pack.provenance,
          notes: `${pack.provenance.notes} ${KEYFRAME_IMAGES_PARTIAL_NOTE}`.trim(),
        },
      },
    });

    const res = await loaded.GET(getRequest(`video_id=${CANON_B}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status: string;
      data: {
        keyframes: Array<{ t_s: number; image_path?: string | null }>;
        metrics: Record<string, number | string>;
        provenance: { source_hash: string; notes: string };
      };
    };
    expect(body.status).toBe('success');
    expect(body.data.keyframes.map((frame) => frame.image_path)).toEqual([
      `/api/video/pack/frames/${CANON_B}/1`,
      `/api/video/pack/frames/${CANON_B}/12`,
    ]);
    expect(body.data.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_OK);
    expect(body.data.provenance.notes).toContain(KEYFRAME_IMAGES_OK_NOTE);
    expect(body.data.provenance.notes).not.toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(body.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(JSON.stringify(body.data.keyframes)).not.toMatch(/i\.ytimg\.com/);
  });

  it('hydrates cached null keyframes via stills bytes and seals stills-ok', async () => {
    const loaded = await loadPackRoute();
    loaded.setKeyframeFrameCaptureForTests(async ({ videoId, t_s }) => ({
      bytes: Uint8Array.from([0xff, 0xd8, 0xff, 0xd9]),
      contentType: KEYFRAME_JPEG_CONTENT_TYPE,
      imagePath: `/api/video/pack/frames/${videoId}/${t_s}`,
      source: 'stills' as const,
    }));
    const identity = loaded.buildIdentityPack(
      CANON_B,
      `https://www.youtube.com/watch?v=${CANON_B}`,
      '2026-09-12T16:39:08.716Z',
    );
    const pack = loaded.applyExtractedSpec(identity, specFor(CANON_B));
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: {
        ...pack,
        keyframes: [
          { t_s: 1, image_path: null, desc: `Keyframe from ${CANON_B}` },
          { t_s: 12, image_path: null, desc: 'Second described frame' },
        ],
        metrics: { keyframes_images: KEYFRAME_IMAGES_PARTIAL },
        provenance: {
          ...pack.provenance,
          notes: `${pack.provenance.notes} ${KEYFRAME_IMAGES_PARTIAL_NOTE}`.trim(),
        },
      },
    });

    const res = await loaded.GET(getRequest(`video_id=${CANON_B}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status: string;
      data: {
        keyframes: Array<{ t_s: number; image_path?: string | null }>;
        metrics: Record<string, number | string>;
        provenance: { source_hash: string; notes: string };
      };
    };
    expect(body.status).toBe('success');
    expect(body.data.keyframes.every((frame) => typeof frame.image_path === 'string')).toBe(true);
    expect(body.data.metrics.keyframes_images).toBe(KEYFRAME_IMAGES_OK);
    expect(body.data.metrics.keyframes_images_source).toBe('stills');
    expect(body.data.provenance.notes).toMatch(/stills captured as JPEG bytes/i);
    expect(body.data.provenance.notes).not.toContain(KEYFRAME_IMAGES_PARTIAL_NOTE);
    expect(JSON.stringify(body.data.keyframes)).not.toMatch(/i\.ytimg\.com|img\.youtube\.com|hqdefault/);
    expect(body.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
  });

  it('returns 200 after truncated auJzb1D-fag spec salvage (not GET 503)', async () => {
    const actual = await vi.importActual<typeof import('@/lib/video-pack-extractor')>(
      '@/lib/video-pack-extractor',
    );
    const bulky = {
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
      artifacts: [],
      stack: { tools: [] },
      visual_context: null,
      chapters: [{ start: 0, end: 5.2, topic: 'At the zoo', key_points: ['Elephants have long trunks'] }],
      action_items: [
        {
          id: 'action-1',
          type: 'implementation',
          title: 'Visit the elephant enclosure',
          description: 'Observe how the speaker describes the elephants.',
          difficulty: 'easy',
        },
      ],
      grounded_spec: {
        version: '1',
        outputClass: 'browser-interactive',
        sourceStatus: 'partial',
        confidence: 0.8,
        limitations: Array.from(
          { length: 400 },
          (_, index) => `Synthetic limitation line ${index} ${'detail '.repeat(30)}`,
        ),
        app: { name: 'Zoo visit', purpose: 'Watch elephants' },
        screens: [{ id: 'main', name: 'Main', purpose: 'View' }],
        state: [],
        requirements: [],
        acceptanceCriteria: [],
        unresolved: [],
        unsupported: [],
      },
    };
    const truncated = JSON.stringify(bulky).slice(0, 8050);

    extractVideoPackSpec.mockImplementation((input, deps) =>
      actual.extractVideoPackSpec(input, {
        runVideoInteraction: async () => ({ text: truncated, interactionId: 'int-test' }),
        hasDirectGoogleKey: () => true,
      }),
    );

    const { POST, GET, flush } = await loadPackRoute();
    const accepted = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }));
    expect(accepted.status).toBe(202);
    await flush();

    const res = await GET(getRequest(`video_id=${CANON_A}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status?: string;
      error?: string;
      data?: {
        transcript?: { full_text?: string };
        metrics?: Record<string, number | string>;
        chapters?: Array<{ topic?: string }>;
        action_items?: Array<{ title?: string }>;
      };
    };
    expect(body.status).toBe('success');
    expect(body.error).toBeUndefined();
    expect(body.data?.transcript?.full_text).toContain('elephants');
    expect(body.data?.metrics?.spec_json_salvaged).toBe(1);
    expect(body.data?.chapters?.[0]?.topic).toBe('At the zoo');
    expect(body.data?.action_items?.[0]?.title).toBe('Visit the elephant enclosure');
  });

  it('does not serve an identity-only pack as success after cite-only extract', async () => {
    extractVideoPackSpec.mockRejectedValue(new VideoPackExtractError('Gemini 3.8 Flash returned no extracted spec content.'));
    const { POST, GET, flush } = await loadPackRoute();
    await POST(postRequest({ video_id: CANON_B }));
    await flush();

    const res = await GET(getRequest(`video_id=${CANON_B}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      ok?: boolean;
      reason_code?: string;
      detail?: string;
      status?: string;
      error?: string;
      data?: { transcript?: { full_text?: string } };
    };
    expect(body.ok).toBe(false);
    expect(body.reason_code).toBe('HOSTED_PACK_GATEWAY_EMPTY');
    expect(body.detail).toMatch(/no extracted spec/i);
    expect(body.data?.transcript?.full_text).not.toBe(`cite:youtube:${CANON_B}`);
  });
});
