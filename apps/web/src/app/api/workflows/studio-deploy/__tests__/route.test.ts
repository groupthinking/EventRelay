import { NextRequest } from 'next/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { start, getToken, decide, assertPublicHttpUrl } = vi.hoisted(() => ({
  start: vi.fn(),
  getToken: vi.fn(),
  decide: vi.fn(),
  assertPublicHttpUrl: vi.fn(),
}));
vi.mock('workflow/api', () => ({ start }));
vi.mock('@/workflows/studio-deploy', () => ({ studioDeployWorkflow: async () => ({}) }));
vi.mock('next-auth/jwt', () => ({ getToken }));
vi.mock('@/lib/origin-gate-store', () => ({ decideOriginGate: decide }));
vi.mock('@/lib/ssrf-guard', () => ({ assertPublicHttpUrl }));
import { POST } from '../route';

function request(body: unknown, origin = 'https://uvai.io') {
  return new NextRequest('https://uvai.io/api/workflows/studio-deploy', { method: 'POST', headers: { 'content-type': 'application/json', origin }, body: JSON.stringify(body) });
}
const fixture = { url: 'https://www.youtube.com/watch?v=auJzb1D-fag' };

describe('Studio deployment preflight', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('NODE_ENV', 'test');
    vi.stubEnv('NEXTAUTH_URL', 'https://uvai.io');
    for (const key of ['V0_SANDBOX_URL', 'V0_RUNTIME_URL', 'V0_BUILD_URL']) vi.stubEnv(key, '');
    vi.stubEnv('NEXTAUTH_SECRET', 'unit-test-secret-with-at-least-32-characters');
    getToken.mockResolvedValue({ sub: 'owner-test' });
    assertPublicHttpUrl.mockImplementation(async (rawUrl: string) => {
      const hostname = new URL(rawUrl).hostname;
      if (hostname === '127.0.0.1' || hostname === '[::1]' || hostname === '169.254.169.254') {
        throw new Error('private host');
      }
    });
    decide.mockResolvedValue({ decision: 'HOLD', reason_code: 'GATE_HOLD_MISSING_EVIDENCE', reason: 'Artifact-bound receipts are missing.', receipt: { version: 'eventrelay.gate-receipt.v2' } });
  });
  afterEach(() => vi.unstubAllEnvs());

  function previewRequest() {
    vi.stubEnv('NODE_ENV', 'development');
    vi.stubEnv('V0_BUILD_URL', 'https://preview.example.test');
    return new NextRequest('http://localhost:3000/api/workflows/studio-deploy', {
      method: 'POST',
      headers: { origin: 'https://preview.example.test', 'content-type': 'application/json' },
      body: JSON.stringify(fixture),
    });
  }

  it('requires authentication for an approved development preview origin', async () => {
    getToken.mockResolvedValue(null);
    const res = await POST(previewRequest());
    expect(res.status).toBe(401);
    expect(await res.json()).toMatchObject({ code: 'authentication_required' });
    expect(decide).not.toHaveBeenCalled();
    expect(start).not.toHaveBeenCalled();
  });

  it('keeps the approved preview preflight held and never starts a deployment', async () => {
    const res = await POST(previewRequest());
    expect(res.status).toBe(409);
    expect(await res.json()).toMatchObject({ ok: false, gate: { decision: 'HOLD' } });
    expect(decide).toHaveBeenCalledWith(expect.objectContaining({ kind: 'studio.deploy' }), 'owner-test');
    expect(start).not.toHaveBeenCalled();
  });

  it('requires a real server session before any side effect', async () => {
    getToken.mockResolvedValue(null);
    expect((await POST(request(fixture))).status).toBe(401);
    expect(start).not.toHaveBeenCalled();
    expect(decide).not.toHaveBeenCalled();
  });

  it('denies cross-origin submissions', async () => {
    expect((await POST(request(fixture, 'https://untrusted.example'))).status).toBe(403);
    expect(start).not.toHaveBeenCalled();
  });

  it.each([{}, { url: 'http://127.0.0.1:3000/x' }, { url: 'http://[::1]:8000/x' }, { url: 'http://169.254.169.254/latest/meta-data/' }])('rejects invalid or private source URLs', async (body) => {
    expect((await POST(request(body))).status).toBe(400);
    expect(start).not.toHaveBeenCalled();
  });

  it('returns the server gate receipt, not a newly started deployment', async () => {
    const res = await POST(request({ ...fixture, authority: { actor: 'system' }, artifactHash: 'a'.repeat(64) }));
    expect(res.status).toBe(409);
    expect(await res.json()).toMatchObject({ ok: false, gate: { decision: 'HOLD', receipt: { version: 'eventrelay.gate-receipt.v2' } } });
    expect(decide).toHaveBeenCalledWith(expect.objectContaining({ kind: 'studio.deploy', fromState: 'proposed', toState: 'live' }), 'owner-test');
    expect(start).not.toHaveBeenCalled();
  });

  it('rejects an oversized body before invoking the gate', async () => {
    expect((await POST(request({ ...fixture, transcript: 'x'.repeat(33_000) }))).status).toBe(413);
    expect(start).not.toHaveBeenCalled();
    expect(decide).not.toHaveBeenCalled();
  });
});
