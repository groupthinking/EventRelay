import { test, expect, type Page } from '@playwright/test';

const viewports = [
  { width: 360, height: 800 },
  { width: 1280, height: 720 },
] as const;

test.beforeEach(({ baseURL }) => {
  test.skip(
    !baseURL || !['localhost', '127.0.0.1', '[::1]'].includes(new URL(baseURL).hostname),
    'Landing-page acceptance checks require an explicit local BASE_URL.',
  );
});

async function expectNoHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

for (const viewport of viewports) {
  test(`keeps the landing conversion path visible without horizontal overflow at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'Paste a YouTube URL. Continue in Studio.' })).toBeVisible();
    await expect(page.getByLabel('YouTube URL')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Run in Studio' })).toBeVisible();
    await expect(page.getByText('UVAI Workflow Pro').last()).toBeVisible();
    await expect(page.getByTestId('home-pro-checkout')).toBeVisible();
    await expect(page.getByRole('link', { name: 'See all plans' })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
}

test('announces an invalid URL and exposes the invalid field state', async ({ page }) => {
  await page.goto('/');
  const input = page.getByLabel('YouTube URL');

  await input.fill('not a YouTube URL');
  await page.getByRole('button', { name: 'Run in Studio' }).click();

  await expect(input).toHaveAttribute('aria-invalid', 'true');
  await expect(input).toHaveAttribute('aria-describedby', 'home-youtube-url-error');
  await expect(page.locator('#home-youtube-url-error')).toHaveText('Need a valid YouTube URL.');
});

test('keeps the keyboard path on native labelled controls', async ({ page }) => {
  await page.goto('/');

  const input = page.getByLabel('YouTube URL');
  const submit = page.getByRole('button', { name: 'Run in Studio' });
  const monthly = page.getByRole('button', { name: 'Monthly checkout' });
  const annual = page.getByRole('button', { name: 'Annual checkout' });
  const pricing = page.getByRole('link', { name: 'See all plans' });

  for (const control of [input, submit, monthly, annual, pricing]) {
    await control.focus();
    await expect(control).toBeFocused();
  }
});
