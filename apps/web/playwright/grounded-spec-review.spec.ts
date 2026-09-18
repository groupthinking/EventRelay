import { mkdir } from 'node:fs/promises';
import { test, expect, type Page } from '@playwright/test';

const storageKey = 'eventrelay-dashboard-v1';

test.beforeEach(({ baseURL }) => {
  test.skip(!process.env.BASE_URL || !baseURL || !['localhost', '127.0.0.1', '[::1]'].includes(new URL(baseURL).hostname), 'Synthetic review fixtures are local-only, not production smoke tests.');
});

async function seedReview(page: Page, baseURL: string | undefined, storageBlocked = false) {
  if (!baseURL || !['localhost', '127.0.0.1', '[::1]'].includes(new URL(baseURL).hostname)) {
    throw new Error('Synthetic review tests require an explicit local BASE_URL; never run against production.');
  }
  const origin = new URL(baseURL).origin;
  const unexpectedRequests: string[] = [];
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== origin) return route.abort();
    if (url.pathname === '/api/auth/session' && request.method() === 'GET') {
      return route.fulfill({ json: {} });
    }
    if (url.pathname.startsWith('/api/') || !['GET', 'HEAD'].includes(request.method())) {
      unexpectedRequests.push(`${request.method()} ${url.pathname}`);
      return route.abort();
    }
    return route.continue();
  });
  const { browserSpecFixture, reviewPackFixture } = await import('../src/test/grounded-spec-fixture');
  const raw = browserSpecFixture();
  raw.grounded_spec.unresolved.push({ id: 'reload', requirementIds: ['toggle'], question: 'Should checked tasks survive reload?', required: true });
  const pack = reviewPackFixture(raw);
  const legacy = structuredClone(pack);
  delete legacy.grounded_spec;
  const tampered = structuredClone(pack);
  if (tampered.grounded_spec?.status !== 'available') throw new Error('Invalid synthetic fixture');
  tampered.grounded_spec.spec.limitations.push('Content changed without a new digest.');
  const videos = [pack, legacy, tampered].map((value, index) => ({
    id: `synthetic-${index}`, title: ['Synthetic blocked review', 'Synthetic legacy pack', 'Synthetic tampered review'][index],
    url: value.source_url, thumbnail: '', status: 'failed', progress: 0,
    failure: { stage: 'analysis', message: 'Synthetic later workflow failure; stored pack remains reviewable.', retryable: false, failedAt: '2026-09-13T00:00:00.000Z' },
    videoPack: { packId: value.id, videoId: value.video_id, sourceUrl: value.source_url, sourceHash: value.provenance.source_hash, version: value.version, pack: value },
  }));
  await page.addInitScript(({ key, videos, storageBlocked }) => {
    if (!sessionStorage.getItem('synthetic-review-seeded')) {
      localStorage.setItem(key, JSON.stringify({ state: { videos, activities: [] }, version: 0 }));
      sessionStorage.setItem('synthetic-review-seeded', 'true');
    }
    if (storageBlocked) {
      const original = Storage.prototype.setItem;
      Storage.prototype.setItem = function (name, value) {
        if (name === key) throw new DOMException('Synthetic quota exceeded', 'QuotaExceededError');
        original.call(this, name, value);
      };
    }
  }, { key: storageKey, videos, storageBlocked });
  await page.goto('/studio');
  const selector = page.getByRole('combobox', { name: 'Stored packs' });
  await expect(selector).toBeVisible();
  await selector.selectOption('synthetic-0');
  await expect(page.getByRole('button', { name: 'Acknowledge review', exact: true })).toBeEnabled();
  return unexpectedRequests;
}

for (const viewport of [{ width: 830, height: 709 }, { width: 390, height: 844 }]) {
  test(`synthetic inspection, acknowledgment, reload, clear and isolation at ${viewport.width}px`, async ({ page, baseURL }) => {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ colorScheme: 'dark' });
    const unexpected = await seedReview(page, baseURL);
    const review = page.getByTestId('grounded-spec-review');
    const acknowledgment = page.getByRole('button', { name: 'Acknowledge review', exact: true });
    await expect(review).toContainText('Model-reported source coverage: partial');
    await expect(review).toContainText('Blocker · reload: Should checked tasks survive reload?');
    await expect(review).toContainText('Proposed checks only. These tests have not been executed.');
    await review.getByText('Supporting source', { exact: true }).click();
    await expect(review.getByRole('link', { name: 'Open source at 0:04' })).toHaveAttribute('href', 'https://www.youtube.com/watch?v=auJzb1D-fag&t=4s');
    await review.getByRole('button', { name: 'Seek to 0:04' }).click();
    await acknowledgment.focus();
    await expect(acknowledgment).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(review).toContainText('Review acknowledged locally. Blockers remain unresolved.');
    await expect(review).toContainText('Blocker · reload');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await mkdir('/tmp/agent-browser', { recursive: true });
    await review.screenshot({ path: `/tmp/agent-browser/grounded-review-${viewport.width}.png` });
    await page.reload();
    await page.getByRole('combobox', { name: 'Stored packs' }).selectOption('synthetic-0');
    await expect(page.getByRole('button', { name: 'Clear local acknowledgment' })).toBeVisible();
    await page.getByRole('combobox', { name: 'Stored packs' }).selectOption('synthetic-1');
    await expect(review).toContainText('Grounded specification unavailable for this pack.');
    await expect(acknowledgment).toHaveCount(0);
    await page.getByRole('combobox', { name: 'Stored packs' }).selectOption('synthetic-2');
    await expect(review).toContainText('Content digest does not match.');
    await expect(acknowledgment).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Clear local acknowledgment' })).toHaveCount(0);
    await page.getByRole('combobox', { name: 'Stored packs' }).selectOption('synthetic-0');
    await page.getByRole('button', { name: 'Clear local acknowledgment' }).click();
    await expect(acknowledgment).toBeEnabled();
    await page.reload();
    await page.getByRole('combobox', { name: 'Stored packs' }).selectOption('synthetic-0');
    await expect(acknowledgment).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Clear local acknowledgment' })).toHaveCount(0);
    await expect(page.getByTestId('studio-deploy-button')).toHaveText('Check preflight');
    expect(unexpected).toEqual([]);
  });
}

test('synthetic storage failure is session-only and cannot survive reload', async ({ page, baseURL }) => {
  const unexpected = await seedReview(page, baseURL, true);
  await page.getByRole('button', { name: 'Acknowledge review', exact: true }).click();
  await expect(page.getByTestId('grounded-spec-review')).toContainText('Session-only review state — not saved for reload.');
  await page.reload();
  await page.getByRole('combobox', { name: 'Stored packs' }).selectOption('synthetic-0');
  await expect(page.getByRole('button', { name: 'Acknowledge review', exact: true })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Clear local acknowledgment' })).toHaveCount(0);
  expect(unexpected).toEqual([]);
});
