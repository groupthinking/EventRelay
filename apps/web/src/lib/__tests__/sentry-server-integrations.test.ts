import { describe, expect, it } from 'vitest';
import {
  SENTRY_INTEGRATIONS_UNSAFE_FOR_WDK,
  SENTRY_SERVER_SKIP_OTEL_SETUP,
  WORKFLOW_UNDICI_DISPATCH_CODE,
  sentryServerIntegrations,
  withoutWorkflowBreakingIntegrations,
  workflowStartErrorBody,
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

  it('requires skipOpenTelemetrySetup — filtering NodeFetch alone is not enough', () => {
    // #1539 deployed to uvai.io and still returned WORKFLOW_UNDICI_DISPATCH_CONFLICT.
    expect(SENTRY_SERVER_SKIP_OTEL_SETUP).toBe(true);
  });

  it('is the Sentry.init integrations callback', () => {
    const result = sentryServerIntegrations([
      { name: 'Http' },
      { name: 'NodeFetch' },
      { name: 'LinkedErrors' },
    ]);
    expect(result.map((i) => i.name)).toEqual(['Http', 'LinkedErrors']);
  });

  it('names the integration Sentry actually registers', () => {
    // Guard against a silent rename in @sentry/node — if this string drifts,
    // the filter stops matching and start() 500s again.
    expect(SENTRY_INTEGRATIONS_UNSAFE_FOR_WDK.has('NodeFetch')).toBe(true);
    expect(SENTRY_INTEGRATIONS_UNSAFE_FOR_WDK.has('Undici')).toBe(false);
  });
});

describe('workflowStartErrorBody (issue #1538)', () => {
  it('returns a stable code and does not leak the nested cause on the undici #P path', () => {
    const err = new Error('fetch failed');
    err.cause = new Error(
      'Cannot read private member #P from an object whose class did not declare it',
    );
    const body = workflowStartErrorBody(err);
    expect(body.error).toBe('fetch failed');
    expect(body.code).toBe(WORKFLOW_UNDICI_DISPATCH_CODE);
    expect(body.hint).toMatch(/NodeFetch/);
    expect(body).not.toHaveProperty('cause');
  });

  it('keeps the generic withWorkflow hint for other start() failures', () => {
    const body = workflowStartErrorBody(new Error('world not configured'));
    expect(body.error).toBe('world not configured');
    expect(body.code).toBeUndefined();
    expect(body.hint).toMatch(/withWorkflow/);
    expect(body).not.toHaveProperty('cause');
  });
});
