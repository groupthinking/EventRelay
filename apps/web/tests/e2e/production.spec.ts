import { test, expect } from '@playwright/test';

test.describe('EventRelay Production E2E', () => {
  test('homepage loads and displays core elements', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole('heading', { name: 'Analyze New Video' })).toBeVisible();
    await expect(page.getByLabel('Workflow steps')).toBeVisible();
  });

  test('dashboard page renders navigation and content', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Analyze New Video' })).toBeVisible();
    await expect(page.locator('nav')).toBeVisible();
  });

  test('features page shows workflow templates and details', async ({ page }) => {
    await page.goto('/features');
    await expect(page.locator('body')).toContainText('Platform Features');
    await expect(page.locator('body')).toContainText('that actually matter');
    const sections = page.locator('section');
    expect(await sections.count()).toBeGreaterThan(0);
  });

  test('api health endpoint is reachable from frontend proxy', async ({ page }) => {
    await page.goto('/dashboard');
    const response = await page.request.get(new URL('/api', page.url()).toString());
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('operational');
  });
});
