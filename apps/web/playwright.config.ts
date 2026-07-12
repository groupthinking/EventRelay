import { defineConfig, devices } from '@playwright/test';

const DEFAULT_PORT = 3000;
const baseURL = process.env.BASE_URL || `http://127.0.0.1:${DEFAULT_PORT}`;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command: `npm run dev -- --hostname 127.0.0.1 --port ${DEFAULT_PORT}`,
        env: {
          ...process.env,
          UVAI_RATE_LIMIT_DISABLED: '1',
        },
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120 * 1000,
      },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
