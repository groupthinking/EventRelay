import { describe, expect, it } from 'vitest';
import {
  SENTRY_INTEGRATIONS_UNSAFE_FOR_WDK,
  withoutWorkflowBreakingIntegrations,
} from '@/lib/sentry-server-integrations';

describe('withoutWorkflowBreakingIntegrations (issue #1538)', () => {
  it('drops NodeFetch and keeps Http / everything else', () => {
    const kept = withoutWorkflowBreakingIntegrations([
      { name: 'Http' },
      { name: 'NodeFetch' },
      { name: 'Console' },
      { name: 'OnUncaughtException' },
    ]);

    expect(kept.map((i) => i.name)).toEqual(['Http', 'Console', 'OnUncaughtException']);
  });

  it('is a no-op when NodeFetch is not present', () => {
    const input = [{ name: 'Http' }, { name: 'LinkedErrors' }];
    expect(withoutWorkflowBreakingIntegrations(input)).toEqual(input);
  });

  it('names the integration Sentry actually registers', () => {
    // Guard against a silent rename in @sentry/node — if this string drifts,
    // the filter stops matching and start() 500s again.
    expect(SENTRY_INTEGRATIONS_UNSAFE_FOR_WDK.has('NodeFetch')).toBe(true);
    expect(SENTRY_INTEGRATIONS_UNSAFE_FOR_WDK.has('Undici')).toBe(false);
  });
});
