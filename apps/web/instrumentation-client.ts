import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.SENTRY_DSN,

  tracesSampleRate: 1,

  debug: false,

  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Enable session replay to debug UI interactions leading to errors in the video workflow
  integrations: [
    Sentry.replayIntegration({
      // ...
    }),
  ],
});