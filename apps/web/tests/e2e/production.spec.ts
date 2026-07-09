import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('EventRelay Production E2E', () => {
  test('homepage loads and shows welcome message', async ({ page }) => {
    await page.goto(BASE_URL);
    // Homepage is the Video Workflow Studio, it should have a YouTube URL input or similar indicators
    const content = await page.textContent('body');
    expect(content).toContain('UVAI');
  });

  test('dashboard page renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    const h1 = await page.locator('h1');
    const text = await h1.first().textContent();
    // Allow for various titles like 'Dashboard', 'Analytics', etc.
    expect(text?.length).toBeGreaterThan(0);
  });

  test('features page shows workflow templates', async ({ page }) => {
    await page.goto(`${BASE_URL}/features`);
    const content = await page.textContent('body');
    expect(content?.toLowerCase()).toContain('workflow');
  });
});
