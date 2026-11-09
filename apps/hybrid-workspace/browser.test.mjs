// Deterministic browser/DOM boundary tests for the hybrid workspace prototype (#2202).
// Uses Playwright Chromium against the actual app modules served on loopback, with
// fixture adapters for the CDN editor/terminal/layout APIs. External requests are
// stubbed; no live Gateway, provider, or production credential is involved.
//
// Env:
//   VERIFIED_HEAD            commit the receipt is tied to (CI sets it)
//   HYBRID_BOUNDARY_RECEIPT  receipt path (default: <os tmpdir>/hybrid-workspace-boundary-receipt.json)
//   HYBRID_CHROMIUM_PATH     optional Chromium executable (e.g. a system chromium)
import { createRequire } from 'node:module';
import { createServer } from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';

// playwright is locked under apps/web (not hoisted to the repo root since #2520).
const requireFromWeb = createRequire(new URL('../web/package.json', import.meta.url));
const { chromium } = requireFromWeb('playwright');

const TEST_TIMEOUT_MS = 10_000;
const FAKE_KEY = 'sk-fixture-NOT-A-REAL-GATEWAY-KEY';
const SENTINEL = 'parent-only-sentinel-2202';
const KEY_PATTERN = new RegExp(`AI_GATEWAY_API_KEY|${FAKE_KEY}|${SENTINEL}`);
// Key material only: chat and srcdoc may legitimately echo source code that names the variable.
const VALUE_PATTERN = new RegExp(`${FAKE_KEY}|${SENTINEL}`);
const receiptPath = process.env.HYBRID_BOUNDARY_RECEIPT || join(tmpdir(), 'hybrid-workspace-boundary-receipt.json');

const root = new URL('./', import.meta.url);
const allowed = new Set(['index.html', 'app.js', 'logic.js', 'fx-adapter.js', 'styles.css']);
const requested = [];
const server = createServer(async (req, res) => {
  requested.push(req.url);
  const name = req.url === '/' ? 'index.html' : req.url.slice(1).split('?')[0];
  if (!allowed.has(name)) { res.writeHead(404).end(); return; }
  res.setHeader('Content-Type', name.endsWith('.js') ? 'text/javascript' : name.endsWith('.css') ? 'text/css' : 'text/html');
  res.end(await readFile(new URL(name, root)));
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const origin = `http://127.0.0.1:${server.address().port}`;

// Models are created in FILES order: 0 index.html, 1 styles.css, 2 app.js, 3 lesson.md.
const IDX = { html: 0, css: 1, js: 2, lesson: 3 };

function fixtureInit({ fakeKey, sentinel }) {
  // addInitScript runs in every frame; the sandboxed preview must stay untouched.
  if (window !== window.top) return;
  window.Split = () => {};
  const models = [], changes = [];
  let active;
  window.monaco = { editor: {
    createModel(value) { const m = { getValue: () => value, getValueInRange: () => value, edit: (v) => { value = v; } }; models.push(m); return m; },
    create(_el, opts) { active = opts.model; return { setModel: (m) => { active = m; }, getModel: () => active, getSelection: () => ({}), onDidChangeModelContent: (fn) => changes.push(fn) }; },
  } };
  window.require = (_deps, fn) => fn(); window.require.config = () => {};
  window.fixtureEdit = (index, value) => { active = models[index]; active.edit(value); changes.forEach((fn) => fn()); };
  window.Terminal = class { open() {} write() {} writeln() {} onData(fn) { window.fixtureType = fn; } };
  window.__keyTouches = 0;
  Object.defineProperty(window, 'AI_GATEWAY_API_KEY', {
    get() { window.__keyTouches++; throw new Error('Forbidden credential access'); },
    set() { window.__keyTouches++; throw new Error('Forbidden credential write'); },
  });
  // Parent-only material the preview must never reach.
  window.__parentFakeKey = fakeKey;
  try { localStorage.setItem('parent-sentinel', sentinel); sessionStorage.setItem('parent-sentinel', sentinel); } catch {}
  document.cookie = `parent_sentinel=${sentinel}; path=/`;
}

async function openApp(browser) {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(TEST_TIMEOUT_MS - 2000);
  const errors = [], popups = [], downloads = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('download', (d) => downloads.push(d.url()));
  context.on('page', (p) => popups.push(p.url()));
  await page.route('**/*', (route) => route.request().url().startsWith(origin + '/')
    ? route.continue()
    : route.fulfill({ status: 200, body: '', contentType: 'text/javascript' }));
  await page.addInitScript(fixtureInit, { fakeKey: FAKE_KEY, sentinel: SENTINEL });
  await page.goto(origin);
  await page.waitForFunction(() => document.querySelectorAll('#files button').length === 4);
  return { context, page, errors, popups, downloads };
}

// The preview iframe is re-rendered (new srcdoc document) on every edit.
async function previewFrame(page, marker) {
  await page.frameLocator('#preview').locator(marker).waitFor({ state: 'attached' });
  const handle = await page.$('#preview');
  return handle.contentFrame();
}

const edit = (page, index, value) => page.evaluate(([i, v]) => window.fixtureEdit(i, v), [index, value]);
const threadText = (page) => page.locator('#thread').innerText();

async function assertNoKeyAnywhere(page) {
  const leak = await page.evaluate(([pattern, valuePattern]) => {
    const re = new RegExp(pattern);
    const valueRe = new RegExp(valuePattern);
    const names = Object.getOwnPropertyNames(window).filter((n) => n !== 'AI_GATEWAY_API_KEY' && /api[_-]?key|gateway/i.test(n));
    const store = (s) => Object.keys(s).filter((k) => k !== 'parent-sentinel').map((k) => `${k}=${s.getItem(k)}`).join(';');
    return {
      touches: window.__keyTouches,
      windowNames: names,
      storage: re.test(store(localStorage)) || re.test(store(sessionStorage)),
      url: re.test(location.href),
      chat: valueRe.test(document.getElementById('thread').innerHTML),
      chatSample: (document.getElementById('thread').innerHTML.match(valueRe) || [''])[0],
      srcdoc: valueRe.test(document.getElementById('preview').srcdoc || ''),
    };
  }, [KEY_PATTERN.source, VALUE_PATTERN.source]);
  assert.equal(leak.touches, 0, 'app read or wrote window.AI_GATEWAY_API_KEY');
  assert.deepEqual(leak.windowNames, [], 'key-like global on window');
  assert.equal(leak.storage, false, 'key in parent storage');
  assert.equal(leak.url, false, 'key in URL');
  assert.equal(leak.chat, false, `key in chat: ${leak.chatSample}`);
  assert.equal(leak.srcdoc, false, 'key in preview srcdoc');
  assert.doesNotMatch(page.url(), KEY_PATTERN);
}

const PROBE = `<title>Probe</title><h1>Probe</h1><a id="dl" href="data:text/plain,x" download="x.txt">dl</a><script>
const r = {};
const t = (k, f) => { try { const v = f(); r[k] = 'reached:' + String(v).slice(0, 80); } catch (e) { r[k] = 'blocked:' + e.name; } };
t('parentDom', () => parent.document.body.dataset.poison = '1');
t('topDom', () => top.document.title);
t('parentKey', () => parent.AI_GATEWAY_API_KEY);
t('parentFakeKey', () => parent.__parentFakeKey);
t('parentLocalStorage', () => parent.localStorage.getItem('parent-sentinel'));
t('ownLocalStorage', () => localStorage.getItem('parent-sentinel'));
t('ownSessionStorage', () => sessionStorage.getItem('parent-sentinel'));
t('cookie', () => document.cookie);
t('parentCookie', () => parent.document.cookie);
t('popup', () => { const w = window.open('/popup-attempt', '_blank'); if (w) throw new Error('popup-opened'); return null; });
r.popup = r.popup === 'reached:null' ? 'blocked:null-window' : r.popup;
t('topNav', () => { top.location.href = '/top-nav-attempt'; return 'assigned'; });
try { document.getElementById('dl').click(); } catch {}
document.body.dataset.probe = JSON.stringify(r);
document.body.dataset.done = '1';
</script>`;

const tests = [
  ['identity and exact sandbox flags', async ({ page }) => {
    assert.equal(await page.title(), 'UVAI Hybrid Workspace');
    assert.equal(await page.locator('#preview').getAttribute('sandbox'), 'allow-scripts');
    assert.equal(await page.locator('iframe').count(), 1);
  }],

  ['preview cannot reach parent DOM, storage, cookies, popups, top navigation, downloads or parent key', async (ctx) => {
    const { page, popups, downloads } = ctx;
    await edit(page, IDX.html, PROBE);
    const frame = await previewFrame(page, 'body[data-done="1"]');
    const r = JSON.parse(await frame.evaluate(() => document.body.dataset.probe));
    for (const [k, v] of Object.entries(r)) assert.match(v, /^blocked:/, `${k} was ${v}`);
    await page.waitForTimeout(500);
    assert.equal(await page.locator('body').getAttribute('data-poison'), null);
    assert.equal(page.url(), origin + '/');
    assert.deepEqual(popups, []);
    assert.deepEqual(downloads, []);
    assert.ok(!requested.some((u) => u.includes('top-nav-attempt') || u.includes('popup-attempt')), 'blocked navigation reached the server');
    assert.equal(await page.evaluate(() => window.__keyTouches), 0);
    ctx.detail = r;
  }],

  ['HTML, CSS and JS edits reach the preview', async ({ page }) => {
    await edit(page, IDX.html, '<!DOCTYPE html><html><head><link rel="stylesheet" href="styles.css"><title>T</title></head><body><h1 id="h">Edited heading</h1><script src="app.js"></script></body></html>');
    let frame = await previewFrame(page, 'h1#h');
    assert.equal(await frame.locator('h1#h').innerText(), 'Edited heading');
    await edit(page, IDX.css, 'h1 { color: rgb(1, 2, 3); }');
    frame = await previewFrame(page, 'style');
    assert.equal(await frame.evaluate(() => getComputedStyle(document.getElementById('h')).color), 'rgb(1, 2, 3)');
    await edit(page, IDX.js, 'document.body.dataset.js = "ran";');
    frame = await previewFrame(page, 'body[data-js="ran"]');
    assert.equal(await frame.locator('h1#h').innerText(), 'Edited heading');
    assert.equal(await frame.evaluate(() => getComputedStyle(document.getElementById('h')).color), 'rgb(1, 2, 3)');
  }],

  ['embedded </script> and </style> cannot break out of injected assets', async ({ page }) => {
    await edit(page, IDX.html, '<html><head><link href="styles.css" rel="stylesheet"></head><body><h1 id="h">x</h1><script defer src="app.js"></script></body></html>');
    await edit(page, IDX.css, 'h1 { color: rgb(4, 5, 6); } /* </style><img id="cssbreak" src="x" onerror="document.body.dataset.broke=1"> */');
    await edit(page, IDX.js, 'const s = "</script><img id=\\"jsbreak\\" src=x onerror=\\"document.body.dataset.broke=1\\">"; document.body.dataset.js = String(s.length > 0);');
    const frame = await previewFrame(page, 'body[data-js="true"]');
    assert.equal(await frame.locator('img').count(), 0);
    assert.equal(await frame.locator('script').count(), 1);
    assert.equal(await frame.locator('style').count(), 1);
    assert.equal(await frame.evaluate(() => document.body.dataset.broke), undefined);
    assert.equal(await frame.evaluate(() => getComputedStyle(document.getElementById('h')).color), 'rgb(4, 5, 6)');
  }],

  ['missing virtual assets are left alone and the preview still renders', async ({ page, errors }) => {
    await edit(page, IDX.html, '<html><head><link rel="stylesheet" href="missing.css"></head><body><h1 id="m">Still here</h1><script src="missing.js"></script></body></html>');
    const frame = await previewFrame(page, 'h1#m');
    assert.equal(await frame.locator('link[href="missing.css"]').count(), 1);
    assert.equal(await frame.locator('script[src="missing.js"]').count(), 1);
    assert.equal(await frame.locator('style').count(), 0);
    assert.deepEqual(errors, []);
  }],

  ['repeated edits keep one preview and reflect only the latest content', async ({ page }) => {
    for (let i = 1; i <= 6; i++) await edit(page, IDX.html, `<title>Rev ${i}</title><h1 id="r">Rev ${i}</h1>`);
    const frame = await previewFrame(page, 'h1#r');
    assert.equal(await frame.locator('h1#r').innerText(), 'Rev 6');
    assert.equal(await page.locator('iframe').count(), 1);
    await page.locator('[data-action="summarize"]').click();
    const text = await threadText(page);
    assert.match(text, /Rev 6/);
    assert.doesNotMatch(text, /Rev [1-5]\b/);
  }],

  ['Embed, Summarize and Extract use current content and escape markup', async ({ page }) => {
    await page.locator('[data-action="embed"]').click();
    assert.match(await threadText(page), /Split screen stays locked/);
    await edit(page, IDX.html, '<title>Edited</title><h1>New</h1>');
    await edit(page, IDX.lesson, '<img src=x onerror="parent.document.body.dataset.poison=1"><script>parent.document.body.dataset.poison=2</script>');
    await page.locator('[data-action="summarize"]').click();
    const text = await threadText(page);
    assert.match(text, /Edited/);
    assert.match(text, /New/);
    assert.doesNotMatch(text, /Animal Trading Cards/);
    assert.match(text, /<img src=x onerror=/);
    await page.locator('#files button', { hasText: 'lesson.md' }).click();
    await page.locator('[data-action="extract"]').click();
    const extracted = await page.locator('#thread .msg.bot').last().innerText();
    assert.match(extracted, /Extracted from lesson\.md/);
    assert.match(extracted, /<img src=x onerror=/);
    assert.equal(await page.locator('#thread img, #thread script').count(), 0);
    assert.equal(await page.locator('body').getAttribute('data-poison'), null);
  }],

  ['free-form Ask summarizes with escaping', async ({ page }) => {
    await edit(page, IDX.html, '<title>Ask Title</title><h1>Ask Heading</h1>');
    await edit(page, IDX.lesson, '<img src=x onerror="document.body.dataset.poison=1"> lesson body');
    await page.locator('#ask').fill('please summarize <b id="userb">this</b> <img src=x onerror="document.body.dataset.poison=1">');
    await page.locator('#composer button').click();
    const last = page.locator('#thread .msg.bot').last();
    const text = await last.innerText();
    assert.match(text, /Current lesson title in preview: Ask Title/);
    assert.match(text, /Ask Heading/);
    assert.match(text, /<img src=x onerror=/);
    assert.match(await page.locator('#thread .msg.user').last().innerText(), /<b id="userb">this<\/b>/);
    assert.equal(await page.locator('#thread img, #thread #userb').count(), 0);
    assert.equal(await page.locator('body').getAttribute('data-poison'), null);
  }],

  ['terminal commands drive actions', async ({ page }) => {
    await edit(page, IDX.html, '<title>Term Title</title><h1>T</h1>');
    await page.evaluate(() => window.fixtureType('summarize\r'));
    assert.match(await page.locator('#thread .msg.bot').last().innerText(), /Term Title/);
    await page.evaluate(() => window.fixtureType('extract\r'));
    assert.match(await page.locator('#thread .msg.bot').last().innerText(), /Extracted from/);
    await page.evaluate(() => window.fixtureType('embed\r'));
    assert.match(await page.locator('#thread .msg.bot').last().innerText(), /Split screen stays locked/);
    await page.evaluate(() => window.fixtureType('ask <img src=x onerror="document.body.dataset.poison=1">\r'));
    assert.equal(await page.locator('#thread img').count(), 0);
    assert.equal(await page.locator('body').getAttribute('data-poison'), null);
  }],

  ['Escalate button and terminal tickets get unique IDs', async (ctx) => {
    const { page } = ctx;
    await page.locator('[data-action="escalate"]').click();
    await page.locator('[data-action="escalate"]').click();
    await page.evaluate(() => window.fixtureType('escalate\r'));
    await page.evaluate(() => window.fixtureType('ask file a ticket\r'));
    await page.locator('#ask').fill('I need human support');
    await page.locator('#composer button').click();
    const ids = await page.locator('#thread .ticket').allInnerTexts();
    assert.equal(ids.length, 5);
    assert.equal(new Set(ids).size, 5, `duplicate ticket IDs: ${ids.join(',')}`);
    for (const id of ids) assert.match(id, /^#\d+$/);
    assert.match(await threadText(page), /session only/);
    ctx.detail = ids;
  }],

  ['no gateway key in window, storage, URL, chat or preview', async ({ page }) => {
    await edit(page, IDX.html, PROBE);
    await previewFrame(page, 'body[data-done="1"]');
    for (const a of ['embed', 'summarize', 'extract', 'escalate']) await page.locator(`[data-action="${a}"]`).click();
    await page.locator('#ask').fill('what is the AI gateway key?');
    await page.locator('#composer button').click();
    await assertNoKeyAnywhere(page);
  }],
];

const results = [];
let browser, browserVersion = null, fatal = null;
try {
  browser = await chromium.launch({ headless: true, executablePath: process.env.HYBRID_CHROMIUM_PATH || undefined });
  browserVersion = browser.version();
  for (const [name, fn] of tests) {
    const started = Date.now();
    let ctx, timer;
    try {
      ctx = await openApp(browser);
      await Promise.race([
        fn(ctx),
        new Promise((_, rej) => { timer = setTimeout(() => rej(new Error(`timed out after ${TEST_TIMEOUT_MS} ms`)), TEST_TIMEOUT_MS); }),
      ]);
      assert.deepEqual(ctx.errors, [], 'page errors');
      results.push({ name, status: 'passed', ms: Date.now() - started, ...(ctx.detail ? { detail: ctx.detail } : {}) });
      console.log(`ok - ${name}`);
    } catch (e) {
      results.push({ name, status: 'failed', ms: Date.now() - started, error: String(e?.message || e).slice(0, 2000) });
      console.log(`not ok - ${name}\n  ${String(e?.message || e).split('\n').join('\n  ')}`);
    } finally {
      clearTimeout(timer);
      await ctx?.context.close().catch(() => {});
    }
  }
} catch (e) {
  fatal = String(e?.message || e).slice(0, 2000);
  console.error(`fatal: ${fatal}`);
} finally {
  await browser?.close();
  await new Promise((r) => server.close(r));
}

const failed = results.filter((r) => r.status !== 'passed').length;
const receipt = {
  status: !fatal && failed === 0 && results.length === tests.length ? 'VERIFIED' : 'FAILED',
  head: process.env.VERIFIED_HEAD || 'local-unpinned',
  issue: 2202,
  surface: 'apps/hybrid-workspace (prototype; /studio is canonical)',
  boundary: 'Chromium DOM + sandboxed srcdoc iframe',
  browser: browserVersion,
  node: process.version,
  generatedAt: new Date().toISOString(),
  perTestTimeoutMs: TEST_TIMEOUT_MS,
  externalServices: 'stubbed (no network beyond loopback)',
  gatewayCalls: 'none (production Gateway disabled; no credentials provided)',
  editor: 'fixture adapter (not live Monaco)',
  totals: { tests: tests.length, passed: results.length - failed, failed, notRun: tests.length - results.length },
  ...(fatal ? { fatal } : {}),
  tests: results,
};
const serialized = JSON.stringify(receipt, null, 2);
if (VALUE_PATTERN.test(serialized)) throw new Error('receipt would contain fixture secret material');
await writeFile(receiptPath, serialized + '\n');
console.log(`receipt: ${receiptPath}`);
console.log(JSON.stringify({ status: receipt.status, head: receipt.head, totals: receipt.totals }));
if (receipt.status !== 'VERIFIED') process.exitCode = 1;
