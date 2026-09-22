import { describe, expect, it, vi } from 'vitest';
import { probeLiveDeploymentUrl } from '@/lib/live-deployment-probe';

describe('probeLiveDeploymentUrl', () => {
  it('returns ok for reachable https responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 200,
        url: 'https://demo.vercel.app/',
        ok: true,
      }),
    );
    const result = await probeLiveDeploymentUrl('https://demo.vercel.app');
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.statusCode).toBe(200);
    }
    vi.unstubAllGlobals();
  });

  it('returns failure for non-success status codes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 503,
        url: 'https://demo.vercel.app/',
        ok: false,
      }),
    );
    const result = await probeLiveDeploymentUrl('https://demo.vercel.app');
    expect(result.ok).toBe(false);
    vi.unstubAllGlobals();
  });
});
