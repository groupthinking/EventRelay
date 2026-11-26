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
  test(`Studio Hybrid D stage shell keeps media-dominant stage at ${width}px`, async ({ page }) => {
    await openStudio(page, width);
    await expect(page.getByRole('main')).toHaveCount(1);
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByTestId('studio-ide-shell')).toHaveAttribute('data-shell', 'hybrid-d');

    const activityRail = page.getByTestId('studio-activity-rail');
    const stagePane = page.getByTestId('studio-ide-video-pane');
    const contextRail = page.getByTestId('studio-context-rail');
    const chatPane = page.getByTestId('studio-ide-chat-pane');
    await expect(activityRail).toBeVisible();
    await expect(stagePane).toBeVisible();
    await expect(contextRail).toBeVisible();
    await expect(chatPane).toBeVisible();

    const activityBox = await activityRail.boundingBox();
    const stageBox = await stagePane.boundingBox();
    const contextBox = await contextRail.boundingBox();
    expect(activityBox && stageBox && contextBox).toBeTruthy();

    // Activity left → stage center (dominant) → context right.
    expect(activityBox!.x).toBeLessThan(stageBox!.x);
    expect(stageBox!.x).toBeLessThan(contextBox!.x);
    // Stage owns at least half of the combined stage+context width.
    expect(stageBox!.width).toBeGreaterThanOrEqual((stageBox!.width + contextBox!.width) * 0.48);
    // Stage is tall — media owns the viewport (not a 300px compact strip).
    expect(stageBox!.height).toBeGreaterThan(360);

    await page.getByTestId('studio-activity-tools').click();
    await expect(page.getByTestId('studio-ide-output-pane')).toBeVisible();
    await expect(page.getByTestId('studio-ide-output-tablist').getByRole('tab')).toHaveCount(4);
    await expect(page.getByTestId('studio-ide-output-tablist').getByRole('tab')).toHaveText([
      'Preview',
      'Tasks & Tools',
      'Code & Spec',
      'Transcript',
    ]);

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

test('Studio context rail collapse/restore and responsive breakpoint switching stay accessible', async ({ page }) => {
  await openStudio(page, 1440);
  await page.getByTestId('studio-context-collapse').click();
  await expect(page.getByTestId('studio-ide-shell')).toHaveAttribute('data-context-collapsed', 'true');
  await expect(page.getByTestId('studio-ide-video-pane')).toBeVisible();
  await page.getByTestId('studio-context-restore').click();
  await expect(page.getByTestId('studio-context-rail')).toBeVisible();
  await expect(page.getByTestId('studio-ide-chat-pane')).toBeVisible();

  for (const width of [720, 640, 390, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole('main')).toBeVisible();
    await expectNoOverflow(page);
  }
});
