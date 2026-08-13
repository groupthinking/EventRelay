import * as Sentry from '@sentry/nextjs';
import { sentryServerIntegrations } from '@/lib/sentry-server-integrations';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 1,
  debug: false,
  // Drop NodeFetch/undici wrapping — see sentry-server-integrations.ts / #1538.
  integrations: sentryServerIntegrations,
});
