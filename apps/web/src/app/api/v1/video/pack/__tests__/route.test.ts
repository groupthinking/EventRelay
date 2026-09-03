import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { GOLDEN_IDENTITY_HASHES } from '@/lib/video-pack';

const CANON_B = 'jNQXAC9IVRw';
const V1_ROUTE_SOURCE = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../route.ts'),
  'utf8',
);

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

afterEach(() => {
  extractVideoPackSpec.mockReset();
  vi.resetModules();
  vi.unstubAllGlobals();
});

async function loadV1Route() {
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
    flush: async () => {
      await Promise.all(scheduled.splice(0));
    },
  };
}

function postRequest(body: unknown) {
  return new Request('http://localhost:3000/api/v1/video/pack', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('POST /api/v1/video/pack', () => {
  it('declares a literal runtime so Next can statically parse route-segment config', () => {
    expect(V1_ROUTE_SOURCE).toMatch(/export const runtime = ['"]nodejs['"]/);
    expect(V1_ROUTE_SOURCE).not.toMatch(/export\s*\{[^}]*\bruntime\b/);
  });

  it('emits the same spec pack as /api/video/pack while keeping the identity hash', async () => {
    extractVideoPackSpec.mockResolvedValue({
      transcript: {
        language: 'en',
        full_text: 'Elephants at the zoo, extracted from the video.',
        segments: [{ idx: 0, start_s: 0, end_s: 5, text: 'Elephants at the zoo.' }],
      },
      keyframes: [{ t_s: 1, desc: 'Elephants' }],
      concepts: ['zoo'],
      requirements: [],
      code_snippets: [],
      visual_context: null,
    });
    const { POST, GET, flush } = await loadV1Route();
    const accepted = await POST(
      postRequest({ url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' }),
    );
    expect(accepted.status).toBe(202);
    await flush();
    const byHash = await GET(
      new Request(
        `http://localhost:3000/api/v1/video/pack?source_hash=${GOLDEN_IDENTITY_HASHES[CANON_B]}`,
      ),
    );
    expect(byHash.status).toBe(200);
    const res = await POST(
      postRequest({ url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' }),
    );
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status: string;
      data: {
        version: string;
        video_id: string;
        source_url: string;
        transcript: { full_text: string; segments: unknown[] };
        concepts: string[];
        provenance: { source_hash: string };
      };
    };
    expect(body.status).toBe('success');
    expect(body.data.version).toBe('v0');
    expect(body.data.video_id).toBe(CANON_B);
    expect(body.data.source_url).toBe('https://www.youtube.com/watch?v=jNQXAC9IVRw');
    expect(body.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(body.data.transcript.full_text).not.toBe(`cite:youtube:${CANON_B}`);
    expect(body.data.concepts).toEqual(['zoo']);
  });
});
