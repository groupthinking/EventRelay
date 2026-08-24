import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

/**
 * Vitest config for the EventRelay web app.
 *
 * Uses the `node` environment because the current suite exercises pure logic
 * (the Zustand dashboard store, the API client, and Next.js route handlers) —
 * none of it renders React, so jsdom is unnecessary and would only slow things
 * down. Add a jsdom project later if/when component rendering tests land.
 *
 * The root `vitest.config.ts` targets `tests/e2e/**` against a live deployment;
 * this config is scoped to `apps/web/src` and runs offline with mocked fetch.
 */
export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    // Force frontend-only behaviour in route handlers (BACKEND_AVAILABLE=false)
    // so tests are deterministic regardless of the developer's shell env.
    // BILLING_COOKIE_SECRET lets billing tests mint/verify signed identity cookies.
    //
    // The AI gateway keys are blanked for the same reason. Without this, any
    // machine with e.g. AI_GATEWAY_API_KEY exported would make route handlers
    // take their *live* provider branch and issue a real network request to
    // https://ai-gateway.vercel.sh — which is both non-hermetic and flaky
    // (billing-chat-gating intermittently blew its 5s timeout). Tests that need
    // a key set it explicitly in their own setup, so a blank default is safe.
    // `resolveBackendCapability()` accepts BACKEND_URL, NEXT_PUBLIC_BACKEND_URL,
    // and NEXT_PUBLIC_API_URL (see lib/backend/capability.ts). Blanking only
    // BACKEND_URL would leave the other two live, so any machine with the real
    // deployed backend exported — every Vercel build, since
    // NEXT_PUBLIC_BACKEND_URL is a project env var — would resolve
    // `configured: true` and start issuing real network calls from unit tests.
    // All three must be blanked together for the suite to stay hermetic.
    env: {
      BACKEND_URL: '',
      NEXT_PUBLIC_BACKEND_URL: '',
      NEXT_PUBLIC_API_URL: '',
      BILLING_COOKIE_SECRET: 'test-billing-cookie-secret',
      AI_GATEWAY_API_KEY: '',
      VERCEL_AI_GATEWAY_API_KEY: '',
      VERCEL_AI_GATEWAY_API: '',
      VERCEL_API_KEY: '',
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      'server-only': fileURLToPath(new URL('./src/test/server-only.ts', import.meta.url)),
    },
  },
});
