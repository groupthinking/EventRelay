import { test, expect, request } from '@playwright/test';

test.describe('UVAI Production-Path Smoke Suite', () => {
  // Fail-closed gate: Verify BASE_URL is reachable and does not return unauthenticated or server errors.
  test.beforeAll(async () => {
    const baseURL = test.info().project.use.baseURL || 'https://uvai.io';
    const requestContext = await request.newContext({ baseURL });
    console.info(`[Playwright] Initiating smoke tests against target: ${baseURL}`);

    try {
      const response = await requestContext.get('/');
      const status = response.status();

      // If the page is unauthenticated (e.g. 401), missing (404), or broken (5xx),
      // we abort immediately and fail closed.
      if (status === 401) {
        throw new Error(
          `[FAIL-CLOSED] Target ${baseURL} returned 401 Unauthorized. Vercel Protection Bypass may be misconfigured.`
        );
      }
      if (status >= 500) {
        throw new Error(
          `[FAIL-CLOSED] Target ${baseURL} returned server error ${status}. Site is degraded.`
        );
      }
      if (!response.ok()) {
        throw new Error(
          `[FAIL-CLOSED] Target ${baseURL} returned status ${status}. Connection check failed.`
        );
      }

      console.info(`[Playwright] Target ${baseURL} is active and healthy (HTTP ${status}).`);
    } catch (error) {
      console.error(`[FAIL-CLOSED] Connection check failed for ${baseURL}:`, error);
      throw error;
    } finally {
      await requestContext.dispose();
    }
  });

  test('Homepage is a sell page with paste action, not the studio workbench', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/UVAI/i);
    await expect(page.getByText('Universal Video Action Intelligence')).toBeVisible();
    await expect(
      page.getByRole('heading', { name: /Paste a YouTube URL\. Open the Studio workbench\./i })
    ).toBeVisible();
    await expect(page.getByText(/Transcript quality varies by source/i)).toBeVisible();
    await expect(page.getByText('Loading studio')).toHaveCount(0);
    await expect(page.getByLabel(/YouTube URL/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Run in Studio/i })).toBeVisible();
    await expect(page.getByText('$39')).toBeVisible();
    await expect(page.getByText('$199/mo')).toBeVisible();
    await expect(page.getByRole('link', { name: /Get Pro/i }).first()).toBeVisible();
    await expect(page.getByTestId('home-pro-checkout')).toBeVisible();
    await expect(page.getByRole('button', { name: /Monthly checkout/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Annual checkout/i })).toBeVisible();
    await expect(page.getByTestId('pro-checkout-button')).toBeVisible();
    await expect(page.getByTestId('turnstile-widget')).toBeVisible();
  });

  test('Features and playground fold into the Studio workbench', async ({ page }) => {
    for (const path of ['/features', '/playground'] as const) {
      const response = await page.goto(path);
      expect(response?.status()).toBeLessThan(400);
      await expect(page).toHaveURL(/\/studio(\?.*)?$/);
    }
    await expect(page.locator('h1')).toContainText(/Paste a YouTube URL/i);
  });

  test('Pricing page keeps Workflow Pro checkout at $39', async ({ page }) => {
    await page.goto('/pricing');

    await expect(page.getByTestId('workflow-pro-catalog')).toContainText('$39/mo');
    await expect(page.getByTestId('workflow-pro-catalog')).toContainText('$390/yr');
    await expect(page.getByText('Monthly checkout')).toBeVisible();
    await expect(page.getByText('Annual checkout')).toBeVisible();
  });

  test('Dashboard, app, and prototype paths fold into the studio workbench', async ({ page }) => {
    for (const path of ['/dashboard', '/app', '/prototype'] as const) {
      const response = await page.goto(path);
      const status = response?.status();
      expect(status).toBeLessThan(400);
      await expect(page).toHaveURL(/\/studio(\?.*)?$/);
    }
    await expect(page.locator('h1')).toContainText(/Paste a YouTube URL/i);
  });

  test('Home paste navigates to Studio with the video query', async ({ page }) => {
    await page.goto('/');
    await page.getByLabel(/YouTube URL/i).fill('https://www.youtube.com/watch?v=auJzb1D-fag');
    await page.getByRole('button', { name: /Run in Studio/i }).click();
    await expect(page).toHaveURL(/\/studio\?video=/);
    await expect(page.locator('h1')).toContainText(/Paste a YouTube URL/i);
  });
});
