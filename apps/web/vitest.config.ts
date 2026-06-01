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
    env: { BACKEND_URL: '' },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
});
