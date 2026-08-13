/**
 * Sentry integrations that break Workflow DevKit's Vercel world client.
 *
 * `@workflow/world-vercel` calls `fetch(url, { dispatcher })` with an
 * `undici.Agent`. Sentry's `NodeFetch` integration (`instrumentUndici`)
 * wraps `dispatch` in a Proxy that then reads a private field (`#P`) on
 * that Agent. When the Agent and the instrumented undici are different
 * class copies, Node throws:
 *
 *   TypeError: fetch failed
 *     [cause]: Cannot read private member #P from an object whose class did not declare it
 *         at Proxy.dispatch
 *
 * That is production issue #1538 — `start()` never returns a runId.
 * Incoming-request `Http` tracing is left alone.
 */
export const SENTRY_INTEGRATIONS_UNSAFE_FOR_WDK = new Set(['NodeFetch']);

export function withoutWorkflowBreakingIntegrations<T extends { name: string }>(
  integrations: readonly T[],
): T[] {
  return integrations.filter((integration) => !SENTRY_INTEGRATIONS_UNSAFE_FOR_WDK.has(integration.name));
}

/** Passed to `Sentry.init({ integrations })` on the Node server. */
export function sentryServerIntegrations<T extends { name: string }>(
  integrations: T[],
): T[] {
  return withoutWorkflowBreakingIntegrations(integrations);
}

export const WORKFLOW_UNDICI_DISPATCH_CODE = 'WORKFLOW_UNDICI_DISPATCH_CONFLICT';

export function workflowStartErrorBody(err: unknown): {
  error: string;
  hint: string;
  code?: string;
} {
  const message = err instanceof Error ? err.message : String(err);
  const cause =
    err instanceof Error && err.cause instanceof Error ? err.cause.message : undefined;
  const undiciPrivateField = typeof cause === 'string' && cause.includes('private member');
  return {
    error: message,
    hint: undiciPrivateField
      ? 'Sentry NodeFetch/undici instrumentation is wrapping fetch.dispatch; disable it (issue #1538).'
      : 'Ensure next.config.js wraps with withWorkflow and `workflow` is installed.',
    ...(undiciPrivateField ? { code: WORKFLOW_UNDICI_DISPATCH_CODE } : {}),
  };
}
