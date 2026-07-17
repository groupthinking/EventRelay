// Client-side Sentry initialization. Next.js loads this file for every
// browser session (replaces the deprecated sentry.client.config.ts, which
// Turbopack does not support).
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN ?? process.env.SENTRY_DSN,
  tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? '0.1'),
  debug: false,
});

// Instruments App Router navigations for Sentry tracing.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
