import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/e2e/**/*.test.ts'],
    testTimeout: 120_000, // 2 min per test — pipeline tests need time
    hookTimeout: 30_000,
    reporters: ['verbose'],
    globals: true,
    env: {
      BASE_URL: process.env.BASE_URL || 'https://uvai.io',
      TEST_YOUTUBE_URL:
        process.env.TEST_YOUTUBE_URL ||
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    },
  },
});
