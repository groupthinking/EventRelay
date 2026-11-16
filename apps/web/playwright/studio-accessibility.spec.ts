import { expect, test, type Locator, type Page } from '@playwright/test';

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

async function expectAnnouncedWidth(splitter: Locator, pane: Locator) {
  await expect.poll(async () => {
    const announced = Number(await splitter.getAttribute('aria-valuenow'));
    const rendered = (await pane.boundingBox())?.width ?? 0;
    return Math.abs(rendered - announced);
  }).toBeLessThan(1);
}

async function expectUsableLayout(page: Page) {
  const chat = await page.getByTestId('studio-ide-chat-pane').boundingBox();
  expect(chat?.width).toBeGreaterThanOrEqual(240);
  for (const side of ['left', 'right']) {
    const splitter = page.getByTestId(`studio-ide-splitter-${side}`);
    const value = Number(await splitter.getAttribute('aria-valuenow'));
    expect(value).toBeGreaterThanOrEqual(Number(await splitter.getAttribute('aria-valuemin')));
    expect(value).toBeLessThanOrEqual(Number(await splitter.getAttribute('aria-valuemax')));
  }
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
      await expect(page.getByTestId('studio-ide-splitter-left')).toBeHidden();
      await expect(page.getByTestId('studio-ide-splitter-right')).toBeHidden();
    }
    const source = views.getByRole('tab', { name: 'Source', exact: true });
    await source.focus();
    await source.press('ArrowRight');
    await expect(views.getByRole('tab', { name: 'Conversation', exact: true })).toBeFocused();
    await expect(views.getByRole('tab', { name: 'Conversation', exact: true })).toHaveAttribute('aria-selected', 'true');
    await expectUsableLayout(page);
  });
}

for (const width of [901, 1000, 1100, 1101, 1440]) {
  test(`Studio rendered and announced pane widths agree during keyboard resize at ${width}px`, async ({ page }) => {
    await openStudio(page, width);
    await expect(page.getByRole('main')).toHaveCount(1);
    await expect(page.getByRole('main')).toBeVisible();
    for (const [side, paneName, grow, shrink] of [
      ['left', 'video', 'ArrowRight', 'ArrowLeft'],
      ['right', 'output', 'ArrowLeft', 'ArrowRight'],
    ] as const) {
      const splitter = page.getByTestId(`studio-ide-splitter-${side}`);
      const pane = page.getByTestId(`studio-ide-${paneName}-pane`);
      await expect(splitter).toBeVisible();
      await expectAnnouncedWidth(splitter, pane);
      await splitter.focus();
      const initial = Number(await splitter.getAttribute('aria-valuenow'));
      await splitter.press(grow);
      await expect(splitter).toHaveAttribute('aria-valuenow', String(initial + 20));
      await expectAnnouncedWidth(splitter, pane);
      await splitter.press(shrink);
      await expect(splitter).toHaveAttribute('aria-valuenow', String(initial));
      await expectAnnouncedWidth(splitter, pane);
      await splitter.press('Home');
      await expect(splitter).toHaveAttribute('aria-valuenow', (await splitter.getAttribute('aria-valuemin'))!);
      await splitter.press(shrink);
      await expect(splitter).toHaveAttribute('aria-valuenow', (await splitter.getAttribute('aria-valuemin'))!);
      await expectAnnouncedWidth(splitter, pane);
      await splitter.press('End');
      await expect(splitter).toHaveAttribute('aria-valuenow', (await splitter.getAttribute('aria-valuemax'))!);
      await splitter.press(grow);
      await expect(splitter).toHaveAttribute('aria-valuenow', (await splitter.getAttribute('aria-valuemax'))!);
      await expectAnnouncedWidth(splitter, pane);
      await expectUsableLayout(page);
      // Leave room for the opposite pane so its grow direction can be tested.
      await splitter.press('Home');
    }
    await expectUsableLayout(page);
  });
}

test('Studio reconciles rendered and announced pane widths when crossing responsive boundaries', async ({ page }) => {
  await openStudio(page, 1440);
  const left = page.getByTestId('studio-ide-splitter-left');
  const right = page.getByTestId('studio-ide-splitter-right');
  await left.focus();
  await left.press('End');
  await right.focus();
  await right.press('End');
  for (const width of [1100, 1000, 901, 900, 390, 901, 1101]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole('main')).toBeVisible();
    if (width <= 900) {
      await expect(left).toBeHidden();
      await expect(right).toBeHidden();
    } else {
      await expectAnnouncedWidth(left, page.getByTestId('studio-ide-video-pane'));
      await expectAnnouncedWidth(right, page.getByTestId('studio-ide-output-pane'));
      await expectUsableLayout(page);
    }
  }
});
