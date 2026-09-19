import { describe, expect, it } from 'vitest';
import {
  factoryDeliverFromHostedSpec,
  hostedSpecHealthFromPackResolution,
  hostedSpecLivePath,
  latestHostedSpecHealthCheck,
  recordHostedSpecHealthCheck,
  resetHostedSpecHealthChecksForTests,
} from '@/lib/compiled-spec-host';

describe('compiled-spec-host', () => {
  it('builds canonical hosted paths for compiled specs', () => {
    expect(hostedSpecLivePath('auJzb1D-fag')).toBe('/d/auJzb1D-fag');
  });

  it('records health checks and returns the latest check', () => {
    resetHostedSpecHealthChecksForTests();
    const first = recordHostedSpecHealthCheck('auJzb1D-fag', {
      ok: true,
      status: 200,
      checked_at: '2026-09-18T00:00:00.000Z',
    });
    const second = recordHostedSpecHealthCheck('auJzb1D-fag', {
      ok: false,
      status: 503,
      checked_at: '2026-09-18T00:01:00.000Z',
    });

    expect(first.ok).toBe(true);
    expect(second.ok).toBe(false);
    expect(latestHostedSpecHealthCheck('auJzb1D-fag')).toEqual(second);
  });

  it('maps store read failures to HOSTED_PACK_STORE_ERROR', () => {
    const health = hostedSpecHealthFromPackResolution({
      kind: 'store_error',
      message: 'upstash read timeout',
    });
    expect(health.ok).toBe(false);
    expect(health.reason_code).toBe('HOSTED_PACK_STORE_ERROR');
    expect(health.detail).toMatch(/timeout/i);
  });

  it('maps missing packs to a non-503 health probe with reason_code', () => {
    const health = hostedSpecHealthFromPackResolution({ kind: 'missing' });
    expect(health.ok).toBe(false);
    expect(health.status).toBe(200);
    expect(health.reason_code).toBe('HOSTED_PACK_NOT_FOUND');
  });

  it('detects hosted live page paths separately from health and assets', async () => {
    const { isHostedLivePagePath, isHostedHealthPath } = await import('@/lib/compiled-spec-host');
    expect(isHostedLivePagePath('/d/auJzb1D-fag', 'auJzb1D-fag')).toBe(true);
    expect(isHostedLivePagePath('/d/auJzb1D-fag/', 'auJzb1D-fag')).toBe(true);
    expect(isHostedHealthPath('/d/auJzb1D-fag/health', 'auJzb1D-fag')).toBe(true);
    expect(isHostedLivePagePath('/d/auJzb1D-fag/health', 'auJzb1D-fag')).toBe(false);
    expect(isHostedLivePagePath('/d/auJzb1D-fag/src/pack', 'auJzb1D-fag')).toBe(false);
  });

  it('drives Factory Deliver only when live URL and health are both valid', () => {
    const ready = factoryDeliverFromHostedSpec({
      videoId: 'auJzb1D-fag',
      liveUrl: 'https://uvai.io/d/auJzb1D-fag',
      health: {
        ok: true,
        status: 200,
        checked_at: '2026-09-18T00:01:00.000Z',
      },
    });
    expect(ready.ready).toBe(true);
    expect(ready.reason_code).toBe('FACTORY_DELIVER_READY');

    const held = factoryDeliverFromHostedSpec({
      videoId: 'auJzb1D-fag',
      liveUrl: 'https://uvai.io/d/auJzb1D-fag',
      health: {
        ok: false,
        status: 503,
        checked_at: '2026-09-18T00:01:00.000Z',
      },
    });
    expect(held.ready).toBe(false);
    expect(held.reason_code).toBe('FACTORY_DELIVER_HEALTH_FAILED');
  });
});
