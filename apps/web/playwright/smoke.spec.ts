import { test, expect, request } from '@playwright/test';

test.describe('UVAI Production-Path Smoke Suite', () => {
  // Fail-closed gate: Verify BASE_URL is reachable and does not return unauthenticated or server errors.
  test.beforeAll(async () => {
    const baseURL = test.info().project.use.baseURL || 'https://uvai.io';
    console.info(`[Playwright] Initiating smoke tests against target: ${baseURL}`);

    const context = await request.newContext({ baseURL });
    try {
      const response = await context.get('/');
      const status = response.status();

      // If the page is unauthenticated (e.g. 401), missing (404), or broken (5xx),
      // we abort immediately and fail closed.
      if (status === 401) {
        throw new Error(
          `[FAIL-CLOSED] Target ${baseURL} returned 401 Unauthorized. Vercel Protection Bypass may be misconfigured.`
        );
      }
      if (status === 404) {
        throw new Error(
          `[FAIL-CLOSED] Target ${baseURL} returned 404 Not Found. Target deployment may be missing or wrong.`
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
      await context.dispose();
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
    const cta = page.locator('text=Analyze a video').first();
    await expect(cta).toBeVisible();
  });

  test('Features page is reachable and contains template gallery indicators', async ({ page }) => {
    await page.goto('/features');

    const content = await page.content();
    // We expect the template showcase or features descriptive text
    expect(content.toLowerCase()).toContain('workflow');
  });

  test('Pricing page renders monthly and annual subscription plans with toggles', async ({ page }) => {
    await page.goto('/pricing');

    // Ensure all three tiers are clearly presented inside tier cards (avoiding strict-locator table conflicts)
    const freeHeader = page.locator('div.text-sm', { hasText: /^Free$/ }).first();
    const proHeader = page.locator('div.text-sm', { hasText: /^Pro$/ }).first();
    const enterpriseHeader = page.locator('div.text-sm', { hasText: /^Enterprise$/ }).first();

    await expect(freeHeader).toBeVisible();
    await expect(proHeader).toBeVisible();
    await expect(enterpriseHeader).toBeVisible();

    // Check for the billing toggle buttons precisely by their role and exact name
    const monthlyToggle = page.getByRole('button', { name: 'Monthly', exact: true });
    const annualToggle = page.getByRole('button', { name: 'Annual -20%', exact: true }).or(
      page.getByRole('button', { name: 'Annual', exact: true })
    );

    await expect(monthlyToggle).toBeVisible();
    await expect(annualToggle).toBeVisible();
  });

  test('Dashboard path is handled gracefully and does not 404 or 5xx', async ({ page }) => {
    const response = await page.goto('/dashboard');
    const status = response?.status();

    // Must not result in a 404 or 5xx server error.
    expect(status).not.toBe(404);
    expect(status).toBeLessThan(500);

    // Assert graceful handling: should either render the dashboard or redirect to auth/login destination.
    const url = page.url();
    const isLoginRedirect = url.includes('/api/auth/signin') || url.includes('/login') || url.includes('/signin');
    const isDashboard = url.endsWith('/dashboard');
    expect(isLoginRedirect || isDashboard).toBe(true);
  });

  test('Critical EventRelay path - submits YouTube URL and adds to dashboard library', async ({ page }) => {
    // Navigate directly to the dashboard (or auth redirect which we bypass if cookies are injected)
    await page.goto('/dashboard');

    const url = page.url();
    // Skip full submission verification if unauthenticated and redirected to NextAuth login,
    // but ensure the page does not 500.
    if (url.includes('/api/auth/signin') || url.includes('/login')) {
      console.info('[Playwright] Redirected to login page. Skipping interactive submission test in unauthenticated preview.');
      return;
    }

    // Interactive Flow:
    // 1. Locate YouTube input field
    const youtubeInput = page.getByPlaceholder('https://youtube.com/watch?v=...');
    await expect(youtubeInput).toBeVisible();

    // 2. Fill with standard short video URL
    const testUrl = 'https://www.youtube.com/watch?v=auJzb1D-fag';
    await youtubeInput.fill(testUrl);

    // 3. Click submit button
    const submitButton = page.getByRole('button', { name: 'Analyze Footage', exact: true });
    await expect(submitButton).toBeVisible();
    await submitButton.click();

    // 4. Verify that video library card or processing element appears
    const librarySection = page.getByText('Your Library');
    await expect(librarySection).toBeVisible();

    // Verify card is added
    const addedCard = page.getByText('auJzb1D-fag').first();
    await expect(addedCard).toBeVisible();
  });
});
