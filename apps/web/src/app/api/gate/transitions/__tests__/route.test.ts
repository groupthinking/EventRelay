import { NextRequest } from 'next/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';
const { getToken, decide } = vi.hoisted(() => ({ getToken: vi.fn(), decide: vi.fn() }));
vi.mock('next-auth/jwt', () => ({ getToken }));
vi.mock('@/lib/origin-gate-store', () => ({ decideOriginGate: decide }));
import { POST } from '../route';

function request(body: unknown = {}, origin = 'https://uvai.io') {
  return new NextRequest('https://uvai.io/api/gate/transitions', { method: 'POST', headers: { origin, 'content-type': 'application/json' }, body: JSON.stringify(body) });
}
describe('POST /api/gate/transitions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('NEXTAUTH_SECRET', 'unit-test-secret-with-at-least-32-characters');
    getToken.mockResolvedValue({ sub: 'session-owner' });
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
