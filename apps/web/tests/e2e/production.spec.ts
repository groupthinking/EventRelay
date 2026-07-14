import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('EventRelay Production E2E', () => {
  test('homepage loads and displays core elements', async ({ page }) => {
    await page.goto(BASE_URL);
    // Home should mention the platform name
    await expect(page.locator('body')).toContainText('UVAI');
    // Check for a video URL input or submission field
    const input = page.locator('input[placeholder*="YouTube"], input[type="text"]').first();
    await expect(input).toBeVisible();
  });

  test('dashboard page renders navigation and content', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    // Basic dashboard content
    const h1 = page.locator('h1');
    await expect(h1.first()).toBeVisible({ timeout: 10000 });

    // Check for navigation links
    await expect(page.locator('nav')).toBeVisible();
  });

  test('features page shows workflow templates and details', async ({ page }) => {
    // Note: features page might be rate-limited in some environments.
    // If it returns 429, we skip the content check to avoid flakiness while still verifying routing.
    const response = await page.goto(`${BASE_URL}/features`);
    if (response?.status() === 200) {
      await expect(page.locator('body')).toContainText(/workflow|template/i);
      const sections = page.locator('section');
      expect(await sections.count()).toBeGreaterThan(0);
    } else if (response?.status() === 429) {
      console.warn('Features page rate limited, skipping content verification');
    } else {
      expect(response?.ok()).toBeTruthy();
    }
  });

  test('api health endpoint is reachable from frontend proxy', async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/v1/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });
});
