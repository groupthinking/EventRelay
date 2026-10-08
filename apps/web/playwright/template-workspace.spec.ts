import { test, expect } from '@playwright/test';

// UI checks use the real application; they do not synthesize AI responses or
// start paid processing. Live extraction quality remains a separate evaluation.
for (const width of [390, 1280]) {
  test(`OpenAI template Home, Pricing and Studio are usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.locator('[data-template="openai-responses-starter"]')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Your videos know what to do next.' })).toBeVisible();
    await expect(page.locator('.template-use-cases')).toBeVisible();
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--uvai-accent').trim())).toBe('#171717');
    await page.getByLabel('YouTube URL').fill('unsupported-source');
    await page.getByRole('button', { name: 'Run in Studio' }).click();
    await expect(page.locator('#home-youtube-url-error')).toHaveText('Need a valid YouTube URL.');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: test.info().outputPath(`home-${width}.png`), fullPage: true });

    await page.goto('/pricing');
    await expect(page.getByRole('heading', { name: 'Know what unlocks before you pay.' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: test.info().outputPath(`pricing-${width}.png`), fullPage: true });

    await page.goto('/studio');
    await expect(page.getByTestId('studio-ide-shell')).toBeVisible();
    await expect(page.getByTestId('studio-ide-chat-pane')).toBeVisible();
    await page.getByLabel('YouTube URL', { exact: true }).fill('https://www.youtube.com/watch?v=auJzb1D-fag');
    if (width < 900) {
      await expect(page.getByTestId('studio-ide-video-pane')).toBeHidden();
      await page.getByRole('tab', { name: 'Source', exact: true }).click();
      await expect(page.getByTestId('studio-ide-video-pane')).toBeVisible();
      await expect(page.getByTestId('studio-ide-chat-pane')).toBeHidden();
      await page.getByRole('tab', { name: 'Deliverables', exact: true }).click();
      await expect(page.getByTestId('studio-ide-output-pane')).toBeVisible();
      await page.getByRole('tab', { name: 'Conversation', exact: true }).click();
      await expect(page.getByTestId('studio-ide-chat-pane')).toBeVisible();
    } else {
      await expect(page.getByTestId('studio-ide-video-pane')).toBeVisible();
      await expect(page.getByTestId('studio-ide-output-pane')).toBeVisible();
    }
    await expect(page.getByLabel('YouTube URL', { exact: true })).toHaveValue('https://www.youtube.com/watch?v=auJzb1D-fag');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: test.info().outputPath(`studio-${width}.png`), fullPage: true });
  });
}
