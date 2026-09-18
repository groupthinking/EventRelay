import { test, expect, request } from '@playwright/test';
import {
  buildVercelProtectionBypassHeaders,
  isVercelProtectionResponse,
} from '../src/lib/e2e-preview-auth';

test.describe('UVAI Production-Path Smoke Suite', () => {
  // Fail-closed gate: Verify BASE_URL is reachable and does not return unauthenticated or server errors.
  test.beforeAll(async () => {
    const baseURL = test.info().project.use.baseURL || 'https://uvai.io';
    const requestContext = await request.newContext({
      baseURL,
      extraHTTPHeaders: buildVercelProtectionBypassHeaders(
        process.env.VERCEL_AUTOMATION_BYPASS_SECRET,
      ),
    });
    console.info(`[Playwright] Initiating smoke tests against target: ${baseURL}`);

    try {
      const response = await requestContext.get('/', {
        failOnStatusCode: false,
        maxRedirects: 0,
      });
      const status = response.status();
      const location = response.headers()['location'] || '';

      // If preview protection intercepts the request, or the page is missing or
      // broken, abort immediately and fail closed.
      if (isVercelProtectionResponse(status, location)) {
        throw new Error(
          `[FAIL-CLOSED] Target ${baseURL} returned ${status}` +
            `${location ? ` → ${location}` : ''}. Vercel Protection Bypass may be misconfigured.`
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
      page.getByRole('heading', { name: /Paste a YouTube URL\. Continue in Studio\./i })
    ).toBeVisible();
    await expect(page.getByText(/Transcript quality varies by source/i)).toBeVisible();
    await expect(page.getByText('Loading studio')).toHaveCount(0);
    await expect(page.getByLabel(/YouTube URL/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Run in Studio/i })).toBeVisible();
    await expect(page.getByTestId('home-workflow-pro-selected-price')).toHaveText('$39/mo');
    await expect(page.getByText(/Paste a YouTube URL/i).nth(1)).toBeVisible();
    await expect(page.getByText('Open Studio')).toBeVisible();
    await expect(page.getByText('Review the outputs')).toBeVisible();
    await expect(page.getByRole('link', { name: /Get Pro/i }).first()).toBeVisible();
    await expect(page.getByTestId('home-pro-checkout')).toBeVisible();
    await expect(page.getByRole('button', { name: /Monthly checkout/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Annual checkout/i })).toBeVisible();
    await expect(page.getByTestId('pro-checkout-button')).toBeVisible();
    await expect(page.getByTestId('turnstile-widget')).toBeVisible();
  });

  test('Features and playground fold into Home', async ({ page }) => {
    const features = await page.goto('/features');
    expect(features?.status()).toBeLessThan(400);
    await expect(page).toHaveURL(/\/(\?.*)?$/);
    await expect(page.getByText('Universal Video Action Intelligence')).toBeVisible();

    const playground = await page.goto('/playground');
    expect(playground?.status()).toBeLessThan(400);
    await expect(page).toHaveURL(/\/(\?.*)?$/);
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
