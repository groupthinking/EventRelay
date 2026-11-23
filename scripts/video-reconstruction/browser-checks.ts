import assert from 'node:assert/strict';
import { Buffer } from 'node:buffer';
import type { Page } from 'playwright';
import {
  exactFixtureBoxes, fixtureBoxes, fixtureImage, fixturePrompt, fixtureSummary,
} from './browser-fixtures.ts';
import { jsonText } from './local-files.ts';

const navTitle = { video: 'Video analysis', spatial: 'Spatial view' } as const;
const text = async (page: Page, selector: string) => (await page.locator(selector).textContent()) ?? '';

export async function checkInitialView(page: Page, view: keyof typeof navTitle): Promise<void> {
  await page.getByRole('heading', { name: navTitle[view], exact: true }).waitFor();
  assert.equal(await page.getByRole('link', { name: navTitle[view], exact: true }).getAttribute('aria-current'), 'page');
  assert.equal(await page.locator('section.view:visible').count(), 1);
}

export async function openView(page: Page, view: keyof typeof navTitle): Promise<void> {
  const link = page.getByRole('link', { name: navTitle[view], exact: true });
  if (await link.getAttribute('aria-current') !== 'page') await link.click();
  await page.getByRole('heading', { name: navTitle[view], exact: true }).waitFor();
  assert.equal(await link.getAttribute('aria-current'), 'page');
}

async function attachVideo(page: Page, videoId: string) {
  await page.getByRole('button', { name: 'Add media', exact: true }).click();
  await page.getByLabel('YouTube URL').fill(`https://youtu.be/${videoId}?feature=shared`);
  await page.getByRole('button', { name: 'Attach video', exact: true }).click();
  await page.locator('#attachment').waitFor();
  assert.equal(await text(page, '#attached-url'), `https://www.youtube.com/watch?v=${videoId}`);
  assert.match(await text(page, '.tokens'), /Unknown/);
}

export async function checkAttachment(page: Page, videoId: string): Promise<void> {
  await openView(page, 'video');
  await attachVideo(page, videoId);
  assert.equal(await page.getByRole('dialog').count(), 0);
  await page.getByRole('button', { name: 'Remove', exact: true }).click();
  await page.getByRole('button', { name: 'Add media', exact: true }).waitFor();
  assert.equal(await text(page, '#attached-url'), '');
  assert.equal(await page.locator('#attachment').isHidden(), true);
}

async function openImport(page: Page, kind: 'summary' | 'boxes') {
  await page.getByRole('button', { name: `Import ${kind}`, exact: true }).click();
  await page.getByRole('dialog').waitFor();
}

async function submitImport(page: Page) {
  await page.getByRole('button', { name: 'Import data', exact: true }).click();
}

async function importSummary(page: Page) {
  await openImport(page, 'summary');
  await page.getByLabel('Choose JSON file').setInputFiles({
    name: 'illustrative-summary.json',
    mimeType: 'application/json',
    buffer: Buffer.from(jsonText(fixtureSummary)),
  });
  await page.waitForFunction((title) => document.querySelector<HTMLTextAreaElement>('#json-text')!.value.includes(title), fixtureSummary.title);
  await submitImport(page);
  await page.getByRole('heading', { name: fixtureSummary.title, exact: true }).waitFor();
  assert.equal(await text(page, '#summary-result .tag'), 'User-supplied output');
  assert.equal(await page.locator('#summary-sections li').count(), 2);
  assert.equal(await page.locator('#summary-sections time').first().textContent(), '00:00:00 – 00:00:18');
}

async function checkSummaryFileReplacement(page: Page) {
  await openImport(page, 'summary');
  const file = page.getByLabel('Choose JSON file');
  const field = page.getByLabel('JSON data');
  const submit = page.getByRole('button', { name: 'Import data', exact: true });
  const buffer = Buffer.from(jsonText(fixtureSummary));
  await file.setInputFiles({ name: 'first-summary.json', mimeType: 'application/json', buffer });
  await page.waitForFunction((title) => document.querySelector<HTMLTextAreaElement>('#json-text')!.value.includes(title), fixtureSummary.title);

  // Pause one File read so its completion order is independent of the filesystem.
  await page.evaluate(() => {
    const original = File.prototype.arrayBuffer;
    File.prototype.arrayBuffer = function (this: File) {
      if (this.name !== 'delayed-summary.json') return original.call(this);
      return new Promise<ArrayBuffer>((resolve) => {
        window.addEventListener('release-summary-fixture', () => {
          File.prototype.arrayBuffer = original;
          resolve(original.call(this).then((data) => {
            document.documentElement.dataset.fixtureFileReleased = 'true';
            return data;
          }));
        }, { once: true });
      });
    };
  });
  await file.setInputFiles({ name: 'delayed-summary.json', mimeType: 'application/json', buffer });
  assert.equal(await field.inputValue(), '');
  assert.equal(await submit.isDisabled(), true);
  await page.locator('#json-form').evaluate((form: HTMLFormElement) => form.requestSubmit());
  assert.equal(await page.getByRole('dialog').isVisible(), true);
  assert.equal(await page.locator('#summary-result').isHidden(), true);

  await file.setInputFiles({ name: 'oversized-summary.json', mimeType: 'application/json', buffer: Buffer.alloc(65_537, 32) });
  await page.getByText('Choose a nonempty JSON file up to 64 KiB.').waitFor();
  assert.equal(await submit.isEnabled(), true);
  assert.equal(await field.inputValue(), '');
  await page.evaluate(() => window.dispatchEvent(new Event('release-summary-fixture')));
  await page.waitForFunction(() => document.documentElement.dataset.fixtureFileReleased === 'true');
  assert.equal(await field.inputValue(), '');
  assert.equal(await page.locator('#summary-result').isHidden(), true);

  await field.fill(jsonText(fixtureSummary));
  await submitImport(page);
  await page.getByRole('heading', { name: fixtureSummary.title, exact: true }).waitFor();
  await page.getByRole('button', { name: 'Clear summary', exact: true }).click();
}

export async function checkSummary(page: Page): Promise<void> {
  await openView(page, 'video');
  await page.getByLabel('Instructions').fill(fixturePrompt);
  assert.equal(await page.getByRole('button', { name: 'Run model', exact: true }).isDisabled(), true);
  assert.match(await text(page, '#model-reason'), /requires a live backend/);
  await importSummary(page);
  await page.getByRole('button', { name: 'Clear summary', exact: true }).click();
  await page.getByText('No summary imported').waitFor();
  assert.equal(await page.locator('#summary-sections li').count(), 0);
  await checkSummaryFileReplacement(page);
}

async function loadImage(page: Page) {
  const previous = await page.locator('#local-image').getAttribute('src');
  await page.getByLabel('Choose image').setInputFiles(fixtureImage);
  await page.locator('#local-image').waitFor();
  await page.waitForFunction((oldSource) => {
    const image = document.querySelector<HTMLImageElement>('#local-image');
    return image?.getAttribute('src') !== oldSource && Boolean(image?.naturalWidth);
  }, previous);
  assert.equal(await text(page, '#image-name'), fixtureImage.name);
}

async function importBoxes(page: Page) {
  await openImport(page, 'boxes');
  await page.getByLabel('Choose JSON file').setInputFiles({
    name: 'illustrative-boxes.json', mimeType: 'application/json', buffer: exactFixtureBoxes,
  });
  await page.waitForFunction(() => document.querySelector<HTMLTextAreaElement>('#json-text')!.value.includes('Illustration: display'));
  await submitImport(page);
  await page.locator('#box-layer .box').first().waitFor();
  assert.equal(await text(page, '#boxes-result .tag'), 'User-supplied annotations');
  assert.deepEqual(await page.locator('#box-layer .box-label').allTextContents(), fixtureBoxes.boxes.map(({ label }) => label));
  const image = await page.locator('#local-image').boundingBox();
  const overlay = await page.locator('#box-layer .box').first().boundingBox();
  assert.ok(image && overlay);
  const coordinates = fixtureBoxes.boxes[0];
  assert.ok(Math.abs(overlay.x - image.x - image.width * coordinates.x) <= 1);
  assert.ok(Math.abs(overlay.y - image.y - image.height * coordinates.y) <= 1);
  assert.ok(Math.abs(overlay.width - image.width * coordinates.width) <= 1);
  assert.ok(Math.abs(overlay.height - image.height * coordinates.height) <= 1);
}

export async function checkBoxes(page: Page): Promise<void> {
  await openView(page, 'spatial');
  assert.equal(await page.getByRole('button', { name: 'Import boxes', exact: true }).isDisabled(), true);
  await loadImage(page);
  await importBoxes(page);
  await page.getByLabel('Show boxes').uncheck();
  assert.equal(await page.locator('#box-layer .box').first().isHidden(), true);
  await page.getByLabel('Show boxes').check();
  assert.equal(await page.locator('#box-layer .box').first().isVisible(), true);
  await page.getByText('Box JSON', { exact: true }).click();
  assert.equal(await text(page, '#exact-box-json'), exactFixtureBoxes.toString('utf8'));
  await loadImage(page);
  assert.equal(await page.locator('#boxes-result').isHidden(), true);
  assert.equal(await page.locator('#box-layer .box').count(), 0);
}

export async function checkInvalidInput(page: Page, capabilities: { media: boolean; summary: boolean; spatial: boolean }) {
  const { media, summary, spatial } = capabilities;
  if (media) {
    await openView(page, 'video');
    await page.getByRole('button', { name: 'Add media', exact: true }).click();
    for (const invalid of [
      'javascript:alert(1)', 'https://example.com/watch?v=auJzb1D-fag',
      'https://www.youtube.com.example.com/watch?v=auJzb1D-fag', 'https://user@www.youtube.com/watch?v=auJzb1D-fag',
      'https://www.youtube.com:443/watch?v=auJzb1D-fag', 'https://youtu.be/short', 'https://www.youtube.com/watch?v=auJzb1D-fag&v=auJzb1D-fag',
    ]) {
      await page.getByLabel('YouTube URL').fill(invalid);
      await page.getByRole('button', { name: 'Attach video', exact: true }).click();
      await page.locator('#media-error').waitFor();
      assert.equal(await page.getByLabel('YouTube URL').getAttribute('aria-invalid'), 'true');
      assert.equal(await page.locator('#attachment').isHidden(), true);
    }
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  }
  if (summary) {
    await openView(page, 'video');
    await openImport(page, 'summary');
    const invalidSection = { ...fixtureSummary.sections[0], endSeconds: -1 };
    for (const invalid of ['{', jsonText({ ...fixtureSummary, sections: [invalidSection] }),
      jsonText({ ...fixtureSummary, sections: Array(33).fill(fixtureSummary.sections[0]) })]) {
      await page.getByLabel('JSON data').fill(invalid);
      await submitImport(page);
      await page.locator('#json-error').waitFor();
      assert.equal(await page.locator('#summary-result').isHidden(), true);
    }
    const literalText = '<b id="injected">Literal markup</b>';
    await page.getByLabel('JSON data').fill(jsonText({ ...fixtureSummary, title: literalText }));
    await submitImport(page);
    await page.getByRole('heading', { name: literalText, exact: true }).waitFor();
    assert.equal(await page.locator('#injected').count(), 0);
    await page.getByRole('button', { name: 'Clear summary', exact: true }).click();
  }
  if (spatial) {
    await openView(page, 'spatial');
    for (const badImage of [
      { name: 'rejected.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg></svg>') },
      { name: 'spoofed.png', mimeType: 'image/png', buffer: Buffer.from('<svg></svg>') },
    ]) {
      await page.getByLabel('Choose image').setInputFiles(badImage);
      await page.locator('#image-error').waitFor();
    }
    await loadImage(page);
    await openImport(page, 'boxes');
    for (const invalid of [
      { ...fixtureBoxes.boxes[0], width: 0.99 }, { ...fixtureBoxes.boxes[0], height: 0 }, { ...fixtureBoxes.boxes[0], x: -0.1 },
    ]) {
      await page.getByLabel('JSON data').fill(jsonText({ boxes: [invalid] }));
      await submitImport(page);
      await page.locator('#json-error').waitFor();
      assert.equal(await page.locator('#boxes-result').isHidden(), true);
    }
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  }
}

export async function populateView(page: Page, view: keyof typeof navTitle, capabilities: { media: boolean; summary: boolean }, videoId: string) {
  await openView(page, view);
  if (view === 'video') {
    if (capabilities.media) await attachVideo(page, videoId);
    await page.getByLabel('Instructions').fill(fixturePrompt);
    if (capabilities.summary) await importSummary(page);
  } else {
    await loadImage(page);
    await importBoxes(page);
    await page.getByText('Box JSON', { exact: true }).click();
  }
}

export async function checkLayout(page: Page, theme: string, width: number, height: number) {
  assert.deepEqual(await page.evaluate(() => [innerWidth, innerHeight]), [width, height]);
  assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
  assert.equal(await page.getByRole('button', { name: 'Dark mode', exact: true }).getAttribute('aria-pressed'), String(theme === 'dark'));
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Document overflowed horizontally');
  const panels = await page.locator('section.view:visible .card:visible').evaluateAll((cards) =>
    cards.map((card) => {
      const bounds = card.getBoundingClientRect();
      return { left: bounds.left, right: bounds.right, width: bounds.width };
    }));
  assert.ok(panels.length > 0 && panels.every((panel) => panel.left >= 0 && panel.right <= width && panel.width >= 250));
}

export async function checkThemeToggle(page: Page, theme: string) {
  const toggle = page.getByRole('button', { name: 'Dark mode', exact: true });
  await toggle.click();
  assert.equal(await page.locator('html').getAttribute('data-theme'), theme === 'dark' ? 'light' : 'dark');
  await toggle.click();
  assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
}
