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
  // The live-studio flag serves the live workspace; this suite covers the classic IDE shell.
  await page.goto('/studio?shell=classic');
  await expect(page.getByTestId('studio-ide-shell')).toBeVisible();
}

async function expectNoOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

for (const width of [390, 640]) {
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

for (const width of [720, 900, 1000, 1280, 1440]) {
  test(`Studio renders side-by-side split workbench with single-row 4-tab Deliverables at ${width}px`, async ({ page }) => {
    await openStudio(page, width);
    await expect(page.getByRole('main')).toHaveCount(1);
    await expect(page.getByRole('main')).toBeVisible();

    const chatPane = page.getByTestId('studio-ide-chat-pane');
    const videoPane = page.getByTestId('studio-ide-video-pane');
    const outputPane = page.getByTestId('studio-ide-output-pane');
    await expect(chatPane).toBeVisible();
    await expect(videoPane).toBeVisible();
    await expect(outputPane).toBeVisible();

    const chatBox = await chatPane.boundingBox();
    const videoBox = await videoPane.boundingBox();
    const outputBox = await outputPane.boundingBox();
    expect(chatBox && videoBox && outputBox).toBeTruthy();

    // Conversation owns the full-height left column; Video + Deliverables share the right column.
    expect(chatBox!.x).toBeLessThan(videoBox!.x);
    expect(chatBox!.x).toBeLessThan(outputBox!.x);
    expect(chatBox!.y).toBeLessThanOrEqual(150);
    expect(chatBox!.height).toBeGreaterThan(videoBox!.height);
    expect(videoBox!.height).toBeLessThanOrEqual(300);
    expect(Math.abs(videoBox!.x - outputBox!.x)).toBeLessThanOrEqual(2);
    expect(videoBox!.y).toBeLessThan(outputBox!.y);
    expect(outputBox!.y).toBeLessThan(500);

    // Deliverables tablist exposes 4 plain-English tabs on one single non-wrapping row.
    const outputTabs = page.getByTestId('studio-ide-output-tablist').getByRole('tab');
    await expect(outputTabs).toHaveCount(4);
    await expect(outputTabs).toHaveText(['Preview', 'Tasks & Tools', 'Code & Spec', 'Transcript']);
    const tabBoxes = await Promise.all(
      [0, 1, 2, 3].map((idx) => outputTabs.nth(idx).boundingBox()),
    );
    expect(tabBoxes.every(Boolean)).toBe(true);
    const firstTabY = tabBoxes[0]!.y;
    for (const box of tabBoxes) {
      expect(Math.abs(box!.y - firstTabY)).toBeLessThanOrEqual(4);
    }

    await expectNoOverflow(page);
  });
}

test('Home primary navigation links remain visible without horizontal overflow at 720x900 half-screen', async ({ page }) => {
  await page.setViewportSize({ width: 720, height: 900 });
  await page.goto('/');
  const primaryNav = page.locator('nav.template-nav').first();
  await expect(primaryNav).toBeVisible();
  for (const label of ['Home', 'Studio', 'Pricing']) {
    await expect(primaryNav.getByRole('link', { name: label, exact: true })).toBeVisible();
  }
  await expectNoOverflow(page);
});

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

  for (const width of [720, 640, 390, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole('main')).toBeVisible();
    await expectNoOverflow(page);
  }
});
