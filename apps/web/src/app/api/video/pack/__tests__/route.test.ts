import { afterEach, describe, expect, it, vi } from 'vitest';
import { GOLDEN_IDENTITY_HASHES, identityHash } from '@/lib/video-pack';

const CANON_A = 'auJzb1D-fag';
const CANON_B = 'jNQXAC9IVRw';

afterEach(() => {
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
  });

  it('emits a v0 pack whose hash is stable for the same video ID', async () => {
    const { POST } = await import('../route');
    const first = await POST(postRequest({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }));
    const second = await POST(postRequest({ youtubeUrl: 'https://youtu.be/auJzb1D-fag?si=retry' }));
    expect(first.status).toBe(200);
    expect(second.status).toBe(200);

    const a = (await first.json()) as { status: string; data: Record<string, unknown> };
    const b = (await second.json()) as { status: string; data: Record<string, unknown> };
    const hashA = (a.data.provenance as { source_hash: string }).source_hash;
    const hashB = (b.data.provenance as { source_hash: string }).source_hash;

    expect(a.status).toBe('success');
    expect(a.data.version).toBe('v0');
    expect(a.data.video_id).toBe(CANON_A);
    expect(a.data.id).toBe(`vp:v0:${CANON_A}`);
    expect(hashA).toBe(GOLDEN_IDENTITY_HASHES[CANON_A]);
    expect(hashA).toBe(identityHash(CANON_A));
    expect(hashA).toBe(hashB);
    expect(a.data.id).toBe(b.data.id);
  });

  it('emits a different hash for a different video ID', async () => {
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
