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

afterEach(() => {
  vi.resetModules();
  vi.unstubAllGlobals();
});

function postRequest(body: unknown) {
  return new Request('http://localhost:3000/api/v1/video/pack', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('POST /api/v1/video/pack', () => {
  it('declares a literal runtime so Next can statically parse route-segment config', () => {
    // Re-exporting `runtime` from the sibling pack route is what failed
    // v0-uvai `next build` after #1612 (`25b4de455`):
    // "The exported configuration object in a source file needs to have a
    // very specific format from which some properties can be statically parsed"
    expect(V1_ROUTE_SOURCE).toMatch(/export const runtime = ['"]nodejs['"]/);
    expect(V1_ROUTE_SOURCE).not.toMatch(/export\s*\{[^}]*\bruntime\b/);
  });

  it('emits the same identity pack as /api/video/pack without a transcript', async () => {
    const { POST } = await import('../route');
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
        provenance: { source_hash: string };
      };
    };
    expect(body.status).toBe('success');
    expect(body.data.version).toBe('v0');
    expect(body.data.video_id).toBe(CANON_B);
    expect(body.data.source_url).toBe('https://www.youtube.com/watch?v=jNQXAC9IVRw');
    expect(body.data.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES[CANON_B]);
    expect(body.data.transcript.full_text).toBe(`cite:youtube:${CANON_B}`);
    expect(body.data.transcript.segments).toEqual([]);
  });
});
