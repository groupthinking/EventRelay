import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('EventRelay Production E2E', () => {
  test('homepage connectivity', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page).toHaveTitle(/UVAI/i);
  });

  test('dashboard navigation', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 15000 });
  });

  test('v1 health check proxy', async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/v1/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('features page routing', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/features`);
    if (response?.status() === 429) {
      console.warn('Rate limited on features page, skipping content check');
      return;
    }
    expect(response?.ok()).toBeTruthy();
    await expect(page.locator('body')).toContainText(/workflow|template/i);
  });
});
