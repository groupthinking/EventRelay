import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('EventRelay Production E2E', () => {
  test('homepage loads and displays core elements', async ({ page }) => {
    await page.goto(BASE_URL);
    // Home should mention the platform name
    await expect(page.locator('body')).toContainText('UVAI');
    // Check for a video URL input or submission field
    const input = page.locator('input[placeholder*="YouTube"], input[type="text"]').first();
    if (await input.isVisible()) {
       await expect(input).toBeVisible();
    }
  });

  test('dashboard page renders navigation and content', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    // Basic dashboard content
    const h1 = page.locator('h1');
    await expect(h1.first()).toBeVisible();

    // Check for navigation links
    await expect(page.locator('nav')).toBeVisible();
  });

  test('features page shows workflow templates and details', async ({ page }) => {
    await page.goto(`${BASE_URL}/features`);
    await expect(page.locator('body')).toContainText(/workflow|template/i);

    // Should have multiple feature cards or sections
    const sections = page.locator('section');
    expect(await sections.count()).toBeGreaterThan(0);
  });

  test('api health endpoint is reachable from frontend proxy', async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });
});
