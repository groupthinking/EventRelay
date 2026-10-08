import * as Sentry from '@sentry/nextjs';
import {
  SENTRY_SERVER_SKIP_OTEL_SETUP,
  sentryServerIntegrations,
} from '@/lib/sentry-server-integrations';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 1,
  debug: false,
  // Drop NodeFetch *and* skip Sentry's OTel setup. #1539 filtered NodeFetch
  // and still 500'd on production: initOpenTelemetry() re-wraps undici.
  // @sentry/nextjs v11 renamed `skipOpenTelemetrySetup` to the inverted
  // `enableOpenTelemetrySetup` (default false). Keep the skip explicit.
  enableOpenTelemetrySetup: !SENTRY_SERVER_SKIP_OTEL_SETUP,
  integrations: sentryServerIntegrations,
});
