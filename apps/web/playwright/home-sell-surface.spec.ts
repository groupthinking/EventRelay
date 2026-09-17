import { expect, test } from '@playwright/test';

const fixtureUrl = 'https://www.youtube.com/watch?v=auJzb1D-fag';

for (const width of [360, 1280]) {
  test(`Home stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');

    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'Paste a YouTube URL. Open the Studio workbench.',
    );
    await expect(page.getByLabel('YouTube URL')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Run in Studio' })).toBeVisible();
    await expect(page.getByTestId('home-pro-checkout')).toBeVisible();
    await expect(page.getByRole('link', { name: 'See all plans' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

test('Home validates invalid input and sends a valid YouTube URL to Studio', async ({ page }) => {
  await page.goto('/');
  const input = page.getByLabel('YouTube URL');

  await input.fill('not a YouTube URL');
  await page.getByRole('button', { name: 'Run in Studio' }).click();
  await expect(page.getByText('Need a valid YouTube URL.')).toBeVisible();

  await input.fill(fixtureUrl);
  await page.getByRole('button', { name: 'Run in Studio' }).click();
  await expect(page).toHaveURL(/\/studio\?video=/);
});

test('Home controls are reachable by keyboard', async ({ page }) => {
  await page.goto('/');

  for (const control of [
    page.getByLabel('YouTube URL'),
    page.getByRole('button', { name: 'Run in Studio' }),
    page.getByRole('button', { name: 'Monthly checkout' }),
    page.getByRole('button', { name: 'Annual checkout' }),
    page.getByRole('link', { name: 'See all plans' }),
  ]) {
    await control.focus();
    await expect(control).toBeFocused();
  }
});
