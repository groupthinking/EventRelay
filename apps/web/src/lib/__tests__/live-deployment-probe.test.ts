import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
const { lookup } = vi.hoisted(() => ({ lookup: vi.fn() }));
vi.mock('node:dns/promises', () => ({ lookup }));
import { probeLiveDeploymentUrl } from '@/lib/live-deployment-probe';

beforeEach(() => {
  lookup.mockReset();
  lookup.mockResolvedValue([{ address: '93.184.216.34', family: 4 }]);
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('exact deployment target reachability', () => {
  it('accepts a public HTTPS 2xx response for the same normalized URL', async () => {
    const fetcher = vi.fn().mockResolvedValue({ status: 200, url: 'https://demo.vercel.app/', redirected: false });
    vi.stubGlobal('fetch', fetcher);
    expect(await probeLiveDeploymentUrl('https://demo.vercel.app')).toEqual({
      ok: true, statusCode: 200, finalUrl: 'https://demo.vercel.app/',
    });
    expect(fetcher).toHaveBeenCalledWith('https://demo.vercel.app/', expect.objectContaining({ redirect: 'error' }));
  });
  it.each([301, 302, 303, 307, 308])('rejects redirect status %s without following Location', async (status) => {
    const fetcher = vi.fn().mockResolvedValue({ status, url: 'https://demo.vercel.app/', headers: new Headers({ Location: 'http://127.0.0.1/admin' }) });
    vi.stubGlobal('fetch', fetcher);
    expect(await probeLiveDeploymentUrl('https://demo.vercel.app')).toEqual({ ok: false, statusCode: status, error: 'redirect_rejected' });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][1].redirect).toBe('error');
  });
  it.each(['http://127.0.0.1/admin', 'https://other.example/', 'https://demo.vercel.app/other'])('rejects substituted success URL %s', async (url) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status: 200, url, redirected: false }));
    expect(await probeLiveDeploymentUrl('https://demo.vercel.app')).toEqual({ ok: false, error: 'target_mismatch' });
  });
  it('rejects a response marked redirected even when its URL matches', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status: 200, url: 'https://demo.vercel.app/', redirected: true }));
    expect((await probeLiveDeploymentUrl('https://demo.vercel.app')).ok).toBe(false);
  });
  it.each(['http://example.com/', 'https://user:secret@example.com/', 'https://localhost/', 'https://127.0.0.1/', 'https://[::1]/', 'https://example.com/#fragment'])('blocks invalid/private target before fetch: %s', async (url) => {
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    expect((await probeLiveDeploymentUrl(url)).ok).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('blocks private and mixed DNS answers before fetch', async () => {
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    lookup.mockResolvedValue([{ address: '93.184.216.34', family: 4 }, { address: '10.0.0.2', family: 4 }]);
    expect((await probeLiveDeploymentUrl('https://demo.vercel.app')).ok).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('fails closed on DNS failure without leaking resolver details', async () => {
    lookup.mockRejectedValue(new Error('EAI_AGAIN internal.example'));
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    expect(await probeLiveDeploymentUrl('https://demo.vercel.app')).toEqual({ ok: false, error: 'invalid_target' });
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('fails closed on fetch failure and never retries an alternative destination', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('private transport details'));
    vi.stubGlobal('fetch', fetcher);
    expect(await probeLiveDeploymentUrl('https://demo.vercel.app')).toEqual({ ok: false, error: 'probe_failed' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('returns a failed HTTP result without retrying', async () => {
    const fetcher = vi.fn().mockResolvedValue({ status: 503, url: 'https://demo.vercel.app/' });
    vi.stubGlobal('fetch', fetcher);
    expect(await probeLiveDeploymentUrl('https://demo.vercel.app')).toEqual({ ok: false, statusCode: 503, error: 'http_503' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('blocks empty and over-budget URLs before fetch', async () => {
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    expect((await probeLiveDeploymentUrl('')).ok).toBe(false);
    expect((await probeLiveDeploymentUrl('https://example.com/' + 'a'.repeat(2048))).ok).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
  });
});
