import { NextRequest } from 'next/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
const { getToken, decide } = vi.hoisted(() => ({ getToken: vi.fn(), decide: vi.fn() }));
vi.mock('next-auth/jwt', () => ({ getToken }));
vi.mock('@/lib/origin-gate-store', () => ({ decideOriginGate: decide }));
import { POST } from '../route';

function request(body: unknown = {}, origin = 'https://uvai.io') {
  return new NextRequest('https://uvai.io/api/gate/transitions', { method: 'POST', headers: { origin, 'content-type': 'application/json' }, body: JSON.stringify(body) });
}
describe('POST /api/gate/transitions', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubEnv('NODE_ENV', 'test');
    vi.stubEnv('NEXTAUTH_URL', 'https://uvai.io');
    for (const key of ['V0_SANDBOX_URL', 'V0_RUNTIME_URL', 'V0_BUILD_URL']) vi.stubEnv(key, '');
    vi.stubEnv('NEXTAUTH_SECRET', 'unit-test-secret-with-at-least-32-characters');
    getToken.mockResolvedValue({ sub: 'session-owner' });
  });
  afterEach(() => vi.unstubAllEnvs());

  function previewRequest(body: unknown = {}, cookie?: string) {
    return new NextRequest('http://localhost:3000/api/gate/transitions', {
      method: 'POST',
      headers: { origin: 'https://preview.example.test', 'content-type': 'application/json', ...(cookie ? { cookie } : {}) },
      body: JSON.stringify(body),
    });
  }

  it('reaches authentication for an approved proxied development origin without evaluating anonymous requests', async () => {
    vi.stubEnv('NODE_ENV', 'development');
    vi.stubEnv('V0_SANDBOX_URL', 'https://preview.example.test/studio');
    getToken.mockResolvedValue(null);
    const res = await POST(previewRequest());
    expect(res.status).toBe(401);
    expect(await res.json()).toMatchObject({ code: 'authentication_required' });
    expect(getToken).toHaveBeenCalledTimes(1);
    expect(decide).not.toHaveBeenCalled();
  });

  it('uses the verified offline session subject, never the preview body identity', async () => {
    vi.stubEnv('NODE_ENV', 'development');
    vi.stubEnv('V0_RUNTIME_URL', 'https://preview.example.test');
    const jwt = await vi.importActual<typeof import('next-auth/jwt')>('next-auth/jwt');
    const token = await jwt.encode({ secret: process.env.NEXTAUTH_SECRET!, token: { sub: 'verified-preview-owner' } });
    getToken.mockImplementationOnce(jwt.getToken);
    decide.mockResolvedValue({ decision: 'HOLD', reason: 'Missing evidence' });
    const body = { transitionId: 'test-transition', subject: 'forged-owner' };
    const res = await POST(previewRequest(body, `__Secure-next-auth.session-token=${token}`));
    expect(res.status).toBe(409);
    expect(decide).toHaveBeenCalledWith(body, 'verified-preview-owner');
  });

  it.each(['development', 'production', 'test'])('blocks untrusted preview submissions before auth or evaluation in %s', async (mode) => {
    vi.stubEnv('NODE_ENV', mode);
    vi.stubEnv('V0_SANDBOX_URL', mode === 'development' ? 'https://different.example.test' : 'https://preview.example.test');
    expect((await POST(previewRequest())).status).toBe(403);
    expect(getToken).not.toHaveBeenCalled();
    expect(decide).not.toHaveBeenCalled();
  });
  it('does not evaluate unauthenticated or cross-origin submissions', async () => {
    getToken.mockResolvedValue(null);
    expect((await POST(request())).status).toBe(401);
    getToken.mockResolvedValue({ sub: 'session-owner' });
    expect((await POST(request({}, 'https://evil.example'))).status).toBe(403);
    expect(decide).not.toHaveBeenCalled();
  });
  it.each(['PASS', 'HOLD', 'REJECT', 'ESCALATE'])('returns the exact server %s without initiating any build', async (decision) => {
    const gate = { decision, reason: 'Server decision', receipt: { id: 'test-receipt' } };
    decide.mockResolvedValue(gate);
    const res = await POST(request({ transitionId: 'test-transition' }));
    expect(res.status).toBe(decision === 'PASS' ? 200 : 409);
    expect(res.headers.get('cache-control')).toBe('no-store');
    expect(await res.json()).toEqual({ ok: decision === 'PASS', gate });
    expect(decide).toHaveBeenCalledWith({ transitionId: 'test-transition' }, 'session-owner');
  });
  it('does not expose internal errors', async () => {
    decide.mockRejectedValue(new Error('secret infrastructure details'));
    const res = await POST(request());
    expect(res.status).toBe(503);
    expect(await res.text()).not.toContain('secret infrastructure details');
  });
});
