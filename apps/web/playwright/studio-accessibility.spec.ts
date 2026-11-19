import { expect, test, type Page } from '@playwright/test';

const consoleMessages = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const messages: string[] = [];
  consoleMessages.set(page, messages);
  page.on('console', message => {
    if (['error', 'warning'].includes(message.type())) messages.push(`${message.type()}: ${message.text()}`);
  });
  page.on('pageerror', error => messages.push(`pageerror: ${error.message}`));
});
test.afterEach(async ({ page }, testInfo) => {
  await testInfo.attach('browser-console', { body: JSON.stringify(consoleMessages.get(page) ?? [], null, 2), contentType: 'application/json' });
  if (!page.isClosed()) {
    await testInfo.attach('studio-viewport', { body: await page.screenshot(), contentType: 'image/png' });
  }
});

// These checks exercise the real Studio shell and production styles without
// starting video processing, AI generation, checkout, or deployment.
async function openStudio(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto('/studio');
  await expect(page.getByTestId('studio-ide-shell')).toBeVisible();
}

async function expectNoOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

for (const width of [390, 900]) {
  test(`selected Studio tabs stay visually distinct and retain a main landmark at ${width}px`, async ({ page }) => {
    await openStudio(page, width);
    const main = page.getByRole('main');
    await expect(main).toHaveCount(1);
    await expect(main).toBeVisible();
    const views = page.getByRole('tablist', { name: 'Studio views' });
    const tabs = views.getByRole('tab');
    for (const name of ['Source', 'Conversation', 'Deliverables']) {
      const tab = views.getByRole('tab', { name, exact: true });
      await tab.click();
      await expect(tab).toHaveAttribute('aria-selected', 'true');
      await expect(tabs).toHaveCount(3);
      const other = views.getByRole('tab', { name: name === 'Source' ? 'Conversation' : 'Source', exact: true });
      await expect(other).toHaveAttribute('aria-selected', 'false');
      const selectedColors = await tab.evaluate(el => ({ background: getComputedStyle(el).backgroundColor, color: getComputedStyle(el).color }));
      const otherColors = await other.evaluate(el => ({ background: getComputedStyle(el).backgroundColor, color: getComputedStyle(el).color }));
      expect(selectedColors.background).not.toBe(otherColors.background);
      expect(selectedColors.color).not.toBe(otherColors.color);
      const panelId = await tab.getAttribute('aria-controls');
      const panel = page.locator(`#${panelId}`);
      await expect(panel).toBeVisible();
      await expect(panel).toHaveAttribute('role', 'tabpanel');
      await expect(panel).toHaveAttribute('aria-labelledby', (await tab.getAttribute('id'))!);
      await expect(main).toBeVisible();
      expect(await main.evaluate((el, id) => el.contains(document.getElementById(id!)), panelId)).toBe(true);
    }
    const source = views.getByRole('tab', { name: 'Source', exact: true });
    await source.focus();
    await source.press('ArrowRight');
    await expect(views.getByRole('tab', { name: 'Conversation', exact: true })).toBeFocused();
    await expect(views.getByRole('tab', { name: 'Conversation', exact: true })).toHaveAttribute('aria-selected', 'true');
    await expectNoOverflow(page);
  });
}

for (const width of [901, 1000, 1100, 1280, 1440]) {
  test(`Studio renders the split workbench (Source + Chat left, Deliverables right) at ${width}px`, async ({ page }) => {
    await openStudio(page, width);
    await expect(page.getByRole('main')).toHaveCount(1);
    await expect(page.getByRole('main')).toBeVisible();
    const videoBox = await page.getByTestId('studio-ide-video-pane').boundingBox();
    const chatBox = await page.getByTestId('studio-ide-chat-pane').boundingBox();
    const outputBox = await page.getByTestId('studio-ide-output-pane').boundingBox();
    expect(videoBox && chatBox && outputBox).toBeTruthy();
    // Deliverables sits side-by-side to the right of Source, near the top of the 900px viewport.
    expect(outputBox!.x).toBeGreaterThan(videoBox!.x);
    expect(outputBox!.y).toBeLessThanOrEqual(150);
    // Source video is height-capped and stacked above Chat in the left column.
    expect(videoBox!.height).toBeLessThanOrEqual(300);
    expect(videoBox!.x).toBeLessThanOrEqual(chatBox!.x + 2);
    expect(videoBox!.y).toBeLessThan(chatBox!.y);
    await expectNoOverflow(page);
  });
}

test('Studio collapse/restore controls and responsive breakpoint switching stay accessible', async ({ page }) => {
  await openStudio(page, 1440);
  await page.getByRole('button', { name: 'Collapse video pane' }).click();
  await expect(page.getByTestId('studio-ide-video-pane')).toBeHidden();
  await page.getByRole('button', { name: 'Show video' }).click();
  await expect(page.getByTestId('studio-ide-video-pane')).toBeVisible();

  await page.getByRole('button', { name: 'Collapse output pane' }).click();
  await expect(page.getByTestId('studio-ide-output-pane')).toBeHidden();
  await page.getByRole('button', { name: 'Show deliverables' }).click();
  await expect(page.getByTestId('studio-ide-output-pane')).toBeVisible();

  for (const width of [900, 390, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole('main')).toBeVisible();
    await expectNoOverflow(page);
  }
});
