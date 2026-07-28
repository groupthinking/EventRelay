import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for UVAI/EventRelay smoke tests.
 *
 * Supports:
 * - Dynamic base URL target via BASE_URL environment variable.
 * - Automatic Vercel Protection Bypass when VERCEL_AUTOMATION_BYPASS_SECRET is set.
 */
const BASE_URL = process.env.BASE_URL || 'https://uvai.io';
const VERCEL_BYPASS_SECRET = process.env.VERCEL_AUTOMATION_BYPASS_SECRET || '';

const extraHTTPHeaders: Record<string, string> = {};
if (VERCEL_BYPASS_SECRET) {
  extraHTTPHeaders['x-vercel-protection-bypass'] = VERCEL_BYPASS_SECRET;
  extraHTTPHeaders['x-vercel-set-bypass-cookie'] = 'true';
}

export default defineConfig({
  testDir: './playwright',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: BASE_URL,
    extraHTTPHeaders,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
