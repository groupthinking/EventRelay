import { expect, test, type Page, type Route } from '@playwright/test';

// Exercises the live-studio flag path end to end with the cached auJzb1D-fag
// sample. Dispatch and status calls are intercepted so no agent run, billing
// or backend is touched.

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function openSample(page: Page) {
  await page.goto('/');
  await expect(page.getByTestId('live-onramp')).toBeVisible();
  await page.getByTestId('home-try-sample').click();
  await expect(page).toHaveURL(/\/studio\?sample=1/);
  await expect(page.getByTestId('live-studio')).toBeVisible();
}

async function waitForSampleDone(page: Page) {
  await expect(page.getByTestId('live-stages').locator('[data-stage="checks"]')).toHaveAttribute('data-state', 'done', {
    timeout: 30_000,
  });
  await expect(page.getByTestId('live-status')).not.toContainText('Replaying sample');
}

test('home is a short on-ramp with one claim, a URL field and a sample', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Paste a video\.\s*Watch it turn into work\./);
  await expect(page.getByLabel('YouTube URL')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Build from video in Studio' })).toBeVisible();
  await expect(page.getByTestId('home-try-sample')).toBeVisible();
  await expect(page.locator('.template-use-cases')).toHaveCount(0);
});

test('pasting a URL opens the live Studio with the video queued', async ({ page }) => {
  await page.route('**/api/video/pack**', (route) => json(route, 503, { error: 'not in this test' }));
  await page.goto('/');
  await page.getByLabel('YouTube URL').fill('https://www.youtube.com/watch?v=auJzb1D-fag');
  await page.getByRole('button', { name: 'Build from video in Studio' }).click();
  await expect(page).toHaveURL(/\/studio\?video=/);
  await expect(page.getByTestId('live-studio')).toBeVisible();
});

test('sample streams stage by stage with skeleton rows, then completes', async ({ page }) => {
  await openSample(page);

  await expect(page.getByTestId('live-status')).toContainText('Replaying sample');
  await expect(page.getByTestId('live-transcript-line-0')).toBeVisible();
  await expect(page.getByTestId('live-tasks-skeleton')).toBeVisible();
  await expect(page.getByTestId('live-sample-label')).toContainText(/sample/i);

  await waitForSampleDone(page);
  await expect(page.getByTestId('live-transcript-skeleton')).toHaveCount(0);
  await expect(page.getByTestId('live-chapter-0')).toBeVisible();
  await expect(page.locator('[data-testid^="live-task-"][data-testid$="-select"]')).toHaveCount(6);
  await expect(page.getByTestId('live-task-ACT-01-check')).toBeVisible();
});

test('a task is editable inline and keeps its source timestamp and keyframe', async ({ page }) => {
  await openSample(page);
  await waitForSampleDone(page);

  const card = page.getByTestId('live-task-G-REQ-01');
  await expect(page.getByTestId('live-task-G-REQ-01-timestamp')).toBeVisible();
  await expect(page.getByTestId('live-task-G-REQ-01-keyframe')).toBeVisible();

  await page.getByTestId('live-task-G-REQ-01-open').click();
  await page.locator('#live-task-G-REQ-01-title').fill('Attach a video and show its token count');
  await page.locator('#live-task-G-REQ-01-check').fill('Token count badge is visible after upload.');
  await page.locator('#live-task-G-REQ-01-owner').selectOption('qa');
  await page.getByTestId('live-task-G-REQ-01-save').click();

  await expect(card).toContainText('Attach a video and show its token count');
  await expect(card).toContainText('Edited');
  await expect(page.getByTestId('live-task-G-REQ-01-check')).toContainText('Token count badge is visible after upload.');
});

test('dispatch streams queued then failed with an upgrade path when Pro is required', async ({ page }) => {
  await page.route('**/api/agents/dispatch', (route) =>
    route.request().method() === 'POST'
      ? json(route, 402, { error: 'Agent dispatch is a Pro feature. Upgrade at /pricing.', upgradeRequired: true })
      : json(route, 200, { available: true }),
  );
  await openSample(page);
  await waitForSampleDone(page);

  await page.getByTestId('live-task-G-REQ-01-select').check();
  await page.getByTestId('live-dispatch-button').click();
  const log = page.getByTestId('live-run-log');
  await expect(log.locator('li[data-status="queued"]')).toHaveCount(1);
  await expect(log.locator('li[data-status="failed"]')).toContainText('402');
  await expect(page.getByTestId('live-dispatch-upgrade')).toBeVisible();
});

test('dispatch streams queued, running and done lines from status polling', async ({ page }) => {
  let dispatched: { job_id?: string; events?: Array<{ id: string }> } = {};
  await page.route('**/api/agents/dispatch', async (route) => {
    if (route.request().method() !== 'POST') return json(route, 200, { available: true });
    dispatched = route.request().postDataJSON() as typeof dispatched;
    return json(route, 200, {
      dispatch_id: 'dsp-e2e',
      executions: (dispatched.events ?? []).map((event, index) => ({
        agent_id: `agent-${index}`,
        agent_type: 'builder',
        status: 'running',
        progress: 20,
        event_id: event.id,
      })),
    });
  });
  await page.route('**/api/agents/status**', (route) => {
    const agentId = new URL(route.request().url()).searchParams.get('agentId');
    return json(route, 200, { agent_id: agentId, agent_type: 'builder', status: 'complete', progress: 100 });
  });

  await openSample(page);
  await waitForSampleDone(page);
  await page.getByTestId('live-task-G-REQ-01-select').check();
  await page.getByTestId('live-task-ACT-01-select').check();
  await expect(page.getByTestId('live-dispatch-button')).toHaveText(/Dispatch 2 tasks/);
  await page.getByTestId('live-dispatch-button').click();

  const log = page.getByTestId('live-run-log');
  await expect(log.locator('li[data-status="running"]').first()).toBeVisible();
  await expect(log.locator('li[data-status="done"]')).toHaveCount(2, { timeout: 10_000 });
  expect(dispatched.events?.map((event) => event.id)).toEqual(['G-REQ-01', 'ACT-01']);
});

test('the Video Pack exports as JSON', async ({ page }) => {
  await openSample(page);
  await waitForSampleDone(page);
  const downloadPromise = page.waitForEvent('download');
  await page.getByTestId('live-download-pack').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('auJzb1D-fag.video-pack.json');
});

test('the live Studio fits the workbench and keeps build files folded', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await openSample(page);
  await waitForSampleDone(page);

  const metrics = await page.evaluate(() => {
    const shell = document.querySelector('.template-studio');
    const main = document.querySelector('main.live-studio');
    return {
      scrollHeight: document.documentElement.scrollHeight,
      mainHeight: main ? main.getBoundingClientRect().height : 0,
      overflowY: shell ? getComputedStyle(shell).overflowY : '',
    };
  });
  expect(metrics.overflowY).not.toBe('hidden');
  expect(metrics.mainHeight).toBeGreaterThan(400);
  expect(metrics.mainHeight).toBeLessThan(2200);
  expect(metrics.scrollHeight).toBeLessThan(2600);

  await page.getByTestId('live-dispatch-button').scrollIntoViewIfNeeded();
  await expect(page.getByTestId('live-dispatch-button')).toBeVisible();
  await expect(page.getByTestId('studio-ide-output')).toBeHidden();
  await page.getByTestId('live-deliverables').getByText('Review and build files', { exact: true }).click();
  await expect(page.getByTestId('studio-ide-output')).toBeVisible();
});

for (const width of [390, 1280]) {
  test(`live Studio has no horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await openSample(page);
    await waitForSampleDone(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
