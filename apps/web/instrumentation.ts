// Must be set before Sentry/Next instrument fetch. @workflow/world-vercel
// passes an undici Agent as fetch's dispatcher; any wrap of dispatch() reads
// private field #P on the wrong class copy (#1538).
process.env.NEXT_OTEL_FETCH_DISABLED = '1';

import * as Sentry from '@sentry/nextjs';

export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    await import('./sentry.server.config');
  }

  if (process.env.NEXT_RUNTIME === 'edge') {
    await import('./sentry.edge.config');
  }
}

export const onRequestError = Sentry.captureRequestError;