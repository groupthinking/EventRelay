import { test, expect } from '@playwright/test';

test.describe('UVAI Production-Path Smoke Suite', () => {
  // Fail-closed gate: Verify BASE_URL is reachable and does not return unauthenticated or server errors.
  test.beforeAll(async ({ request }) => {
    const baseURL = test.info().project.use.baseURL || 'https://uvai.io';
    console.info(`[Playwright] Initiating smoke tests against target: ${baseURL}`);

    try {
      const response = await request.get('/');
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
    }
  });

  test('Homepage renders critical branding and CTA elements', async ({ page }) => {
    await page.goto('/');

    // Assert title or logo is present
    await expect(page).toHaveTitle(/EventRelay|UVAI|Video/i);

    // Assert key product heading is visible
    const heading = page.locator('h1');
    await expect(heading).toContainText(/Turn any video into actions/i);

    // Assert the primary CTA exists
    const cta = page.locator('text=Analyze a video');
    await expect(cta).toBeVisible();
  });

  test('Features page is reachable and contains template gallery indicators', async ({ page }) => {
    await page.goto('/features');

    const content = await page.content();
    // We expect the template showcase or features descriptive text
    expect(content.toLowerCase()).toContain('workflow');
  });

  test('Pricing page renders monthly and annual subscription plans', async ({ page }) => {
    await page.goto('/pricing');

    // Ensure all three tiers are clearly presented to users
    await expect(page.locator('text=Free')).toBeVisible();
    await expect(page.locator('text=Pro')).toBeVisible();
    await expect(page.locator('text=Enterprise')).toBeVisible();

    // Check for the billing toggles
    await expect(page.locator('text=Monthly')).toBeVisible();
    await expect(page.locator('text=Annual')).toBeVisible();
  });

  test('Dashboard path is handled gracefully', async ({ page }) => {
    const response = await page.goto('/dashboard');
    const status = response?.status();

    // The dashboard is gated; it must redirect to login/auth, or render if authenticated.
    // In either case, the deployment must handle it gracefully without returning a 5xx error.
    expect(status).toBeLessThan(500);
  });
});
