import assert from 'node:assert/strict';
import { accessSync, constants, mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { isAbsolute, join, resolve } from 'node:path';
import type { AddressInfo } from 'node:net';
import type { Page } from 'playwright';
import {
  browserBindings, canonicalJson, sha256, type BrowserCheckId, type BrowserReceipt, type Manifest,
} from './contract.ts';
import {
  checkAttachment, checkBoxes, checkInitialView, checkInvalidInput, checkLayout, checkSummary, checkThemeToggle, populateView,
} from './browser-checks.ts';
import {
  captureCheckDetails, captureInventory, dimensions, recordingPath, screenshotPath, supportedViews, themes, viewports,
} from './captures.ts';
import { readLocalFile } from './local-files.ts';

const workspaceRequire = createRequire(new URL('../../apps/web/package.json', import.meta.url));
const fileTypes = {
  '/': 'text/html; charset=utf-8',
  '/index.html': 'text/html; charset=utf-8',
  '/app.js': 'application/javascript; charset=utf-8',
  '/app.css': 'text/css; charset=utf-8',
  '/favicon.png': 'image/png',
} as const;

export type BrowserRun = { runId: string; verifierRevision: string };

export function currentVerifierRevision(): string {
  const paths = [
    'browser.ts', 'browser-checks.ts', 'browser-fixtures.ts', 'captures.ts', 'cli.ts', 'contract.ts', 'local-files.ts',
    'fixtures/illustrative-targets.jpg',
  ];
  const revisions = paths.map((path) => [path, sha256(readFileSync(new URL(path, import.meta.url)))]);
  const { version } = workspaceRequire('playwright/package.json') as { version: string };
  return sha256(canonicalJson([...revisions, ['workspace-playwright', version]]));
}

function chromiumExecutable(): string | undefined {
  const configured = process.env.RECONSTRUCTION_CHROMIUM;
  if (configured) {
    if (!isAbsolute(configured) || resolve(configured) !== configured) throw new Error('RECONSTRUCTION_CHROMIUM requires an absolute executable path');
    accessSync(configured, constants.X_OK);
    return configured;
  }
  try {
    accessSync('/usr/bin/chromium', constants.X_OK);
    return '/usr/bin/chromium';
  } catch {
    return undefined;
  }
}

async function serveApp(appDirectory: string, manifest: Manifest) {
  const files = new Map(manifest.generatedCode.files.map((file) => {
    const bytes = readLocalFile(join(appDirectory, file.path), file.bytes);
    if (bytes.byteLength !== file.bytes || sha256(bytes) !== file.sha256) throw new Error(`Generated file changed before serving: ${file.path}`);
    return ['/' + file.path, bytes] as const;
  }));
  files.set('/', files.get('/index.html')!);
  const server = createServer((request, response) => {
    const path = request.url ?? '';
    const bytes = files.get(path);
    if (request.method !== 'GET' || !bytes || !Object.hasOwn(fileTypes, path)) {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, {
      'Content-Type': fileTypes[path as keyof typeof fileTypes],
      'Content-Security-Policy': "frame-ancestors 'none'",
      'Content-Length': bytes.byteLength,
      'Cache-Control': 'no-store',
      'Referrer-Policy': 'no-referrer',
      'X-DNS-Prefetch-Control': 'off',
      'X-Content-Type-Options': 'nosniff',
    }).end(bytes);
  });
  await new Promise<void>((ready, failed) => {
    server.once('error', failed);
    server.listen(0, '127.0.0.1', () => {
      server.removeListener('error', failed);
      ready();
    });
  });
  const origin = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  return {
    origin,
    accepts: (url: string) => url.startsWith(origin + '/') && files.has(url.slice(origin.length)),
    close: () => new Promise<void>((done, failed) => {
      server.close((error) => error ? failed(error) : done());
      server.closeAllConnections();
    }),
  };
}

export class BrowserVerificationError extends Error {
  constructor(cause: unknown, readonly checks: BrowserReceipt['checks']) {
    super(cause instanceof Error ? cause.message : String(cause), { cause });
  }
}

function captureErrors(page: Page, faults: string[]) {
  page.on('pageerror', (error) => faults.push(error.message));
  page.on('console', (message) => {
    if (['error', 'warning'].includes(message.type())) faults.push(message.text());
  });
  page.on('response', (response) => {
    if (!response.ok()) faults.push(`Unexpected HTTP response ${response.status()}: ${response.url()}`);
  });
}

export async function verifyInBrowser(
  appDirectory: string,
  evidenceDirectory: string,
  manifest: Manifest,
  run: BrowserRun,
  profileFileSha256: string,
) {
  const { chromium } = workspaceRequire('playwright') as typeof import('playwright');
  const checks: BrowserReceipt['checks'] = [];
  const faults: string[] = [];
  const capabilities = {
    media: manifest.requiredCheckIds.includes('youtube-attachment'),
    summary: manifest.requiredCheckIds.includes('summary-renderer'),
    spatial: manifest.requiredCheckIds.includes('box-renderer'),
  };
  const check = async (id: BrowserCheckId, action: () => Promise<string>): Promise<void> => {
    try {
      checks.push({ id, passed: true, details: await action() });
    } catch (error) {
      checks.push({ id, passed: false, details: (error instanceof Error ? error.message : String(error)).slice(0, 2000) });
      throw new Error(`Browser check failed: ${id}: ${checks.at(-1)!.details}`, { cause: error });
    }
  };
  try {
    const browser = await chromium.launch({ executablePath: chromiumExecutable(), headless: true, timeout: 25_000 });
    try {
      const server = await serveApp(appDirectory, manifest);
      try {
        mkdirSync(join(evidenceDirectory, 'screenshots'), { mode: 0o700 });
        mkdirSync(join(evidenceDirectory, 'recordings'), { mode: 0o700 });
        const recordVideoDir = mkdtempSync(join(evidenceDirectory, '.recording-'));
        const views = supportedViews(manifest);
        try {
          for (const [index, viewport] of viewports.entries()) {
            for (const theme of themes) {
              const size = dimensions(viewport.width, viewport.height);
              const context = await browser.newContext({ viewport, colorScheme: theme, serviceWorkers: 'block',
                recordVideo: { dir: recordVideoDir, size: viewport } });
              let video;
              try {
                await context.route('**/*', async (route) => {
                  if (server.accepts(route.request().url()) || route.request().url().startsWith('blob:' + server.origin + '/')) {
                    await route.continue();
                  } else {
                    faults.push(`Unexpected network request: ${route.request().url()}`);
                    await route.abort();
                  }
                });
                const page = await context.newPage();
                video = page.video();
                page.setDefaultTimeout(5000);
                captureErrors(page, faults);
                await page.goto(server.origin + '/', { waitUntil: 'load', timeout: 10_000 });
                await checkInitialView(page, views[0]);
                if (index === 0 && theme === 'light') {
                  await page.goto(server.origin + '/#unknown-view');
                  await page.reload({ waitUntil: 'load' });
                  await checkInitialView(page, views[0]);
                  if (capabilities.media) await check('youtube-attachment', async () => {
                    await checkAttachment(page, manifest.source.videoId);
                    return 'Attached and removed a canonical URL. Token count displayed Unknown.';
                  });
                  if (capabilities.summary) await check('summary-renderer', async () => {
                    await checkSummary(page);
                    return 'Entered instructions, confirmed model action disabled, imported timestamped JSON, rejected a stale file read and cleared the supplied result.';
                  });
                  if (capabilities.spatial) await check('box-renderer', async () => {
                    await checkBoxes(page);
                    return 'Loaded an illustrative local JPEG, validated scaled box geometry, toggled overlays, inspected exact JSON and reset annotations on image replacement.';
                  });
                  await check('invalid-input', async () => {
                    await checkInvalidInput(page, capabilities);
                    return 'Rejected invalid media and malformed or out-of-range data for the selected capabilities.';
                  });
                }
                await checkThemeToggle(page, theme);
                for (const view of views) {
                  await populateView(page, view, capabilities, manifest.source.videoId);
                  await checkLayout(page, theme, viewport.width, viewport.height);
                  await page.screenshot({ path: join(evidenceDirectory, screenshotPath(view, theme, size)), fullPage: true });
                  // Hold the completed view long enough for reviewers to read it in the recording.
                  await page.waitForTimeout(650);
                }
              } finally {
                await context.close();
                if (video) await video.saveAs(join(evidenceDirectory, recordingPath(theme, size)));
              }
            }
          }
        } finally {
          rmSync(recordVideoDir, { recursive: true, force: true });
        }
      } finally {
        await server.close();
      }
      await check('offline-and-console', async () => {
        assert.deepEqual(faults, []);
        return `Chromium ${browser.version()}. No external requests, HTTP failures, console warnings, errors or page exceptions.`;
      });
      const captures = captureInventory(evidenceDirectory, manifest);
      await check('responsive-light-dark', async () => captureCheckDetails(captures, profileFileSha256));
      const receipt: BrowserReceipt = {
        version: 'video-reconstruction.browser-receipt.v1',
        ...browserBindings(manifest), ...run, checks,
      };
      return { captures, receipt };
    } finally {
      await browser.close();
    }
  } catch (error) {
    throw new BrowserVerificationError(error, checks);
  }
}
