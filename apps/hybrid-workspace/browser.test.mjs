// Browser plugin not available. Uses Playwright Chromium and actual app modules,
// with fixture adapters for CDN editor/terminal/layout APIs; no live Gateway.
import { createRequire } from 'node:module';
const requireFromWeb = createRequire(new URL('../web/package.json', import.meta.url));
const { chromium } = requireFromWeb('playwright');
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const root = new URL('./', import.meta.url);
const allowed = new Set(['index.html','app.js','logic.js','fx-adapter.js','styles.css']);
const server = createServer(async (req,res) => {
  const name = req.url === '/' ? 'index.html' : req.url.slice(1);
  if (!allowed.has(name)) { res.writeHead(404).end(); return; }
  res.setHeader('Content-Type', name.endsWith('.js') ? 'text/javascript' : name.endsWith('.css') ? 'text/css' : 'text/html');
  res.end(await readFile(new URL(name,root)));
});
await new Promise(r => server.listen(0,'127.0.0.1',r));
let browser;
try {
  browser = await chromium.launch({headless:true});
  const page = await browser.newPage();
  const origin = `http://127.0.0.1:${server.address().port}`;
  const errors = [];
  const requests = [];
  const requiredHead = process.env.VERIFIED_HEAD || 'local-unpinned';
  const receiptPath = process.env.RECEIPT_PATH || '';
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', req => requests.push(req.url()));
  await page.route('**/*', route => route.request().url().startsWith(origin+'/') ? route.continue() : route.fulfill({status:200,body:'',contentType:'text/javascript'}));
  await page.addInitScript(() => {
    window.Split = () => {};
    const models = [], changes = [];
    let active;
    window.monaco = {editor:{createModel(value) {const m={getValue:()=>value,getValueInRange:()=>value,edit:v=>{value=v;}}; models.push(m);return m;},create(_el,opts){active=opts.model;return {setModel:m=>{active=m;},getModel:()=>active,getSelection:()=>({}),onDidChangeModelContent:fn=>changes.push(fn)};}}};
    window.require = (_deps,fn) => fn(); window.require.config = () => {};
    window.fixtureEdit = (index,value) => {active=models[index];active.edit(value);changes.forEach(fn=>fn());};
    window.Terminal = class {open(){} write(){} writeln(){} onData(fn){window.fixtureType=fn;}};
    Object.defineProperty(window,'AI_GATEWAY_API_KEY',{get(){throw new Error('Forbidden credential access');},set(){throw new Error('Forbidden credential write');}});
  });
  await page.goto(origin);
  await page.waitForFunction(() => document.querySelectorAll('#files button').length===4);
  assert.equal(await page.title(),'UVAI Hybrid Workspace');
  assert.equal(await page.locator('#preview').getAttribute('sandbox'),'allow-scripts');
  const sandboxTokens = (await page.locator('#preview').getAttribute('sandbox')).split(/\s+/).filter(Boolean);
  assert.deepEqual(sandboxTokens, ['allow-scripts']);
  for (const disallowed of ['allow-same-origin','allow-top-navigation','allow-popups','allow-downloads']) {
    assert.equal(sandboxTokens.includes(disallowed), false);
  }
  assert.equal(await page.evaluate(() => location.search), '');
  await page.locator('[data-action="embed"]').click();
  assert.match(await page.locator('#thread').innerText(),/Split screen stays locked/);
  await page.evaluate(() => window.fixtureEdit(0,'<title>Edited</title><h1>New</h1><script>try { parent.document.body.dataset.poison="1" } catch { document.body.dataset.confined="1" }</script>'));
  await page.locator('[data-action="summarize"]').click();
  assert.match(await page.locator('#thread').innerText(),/Edited/);
  assert.equal(await page.locator('body').getAttribute('data-poison'),null);
  const preview = page.frameLocator('#preview');
  await preview.locator('body[data-confined="1"]').waitFor();
  await page.evaluate(() => window.fixtureEdit(0,'<title>Edited Again</title><h1>Newer</h1>'));
  await page.locator('[data-action="summarize"]').click();
  assert.match(await page.locator('#thread').innerText(),/Edited Again/);
  await page.evaluate(() => window.fixtureEdit(3,'# Lesson\n<img src=x onerror=\"window.lessonPoison=1\">'));
  await page.locator('[data-action="summarize"]').click();
  assert.equal(await page.locator('#thread img').count(),0);
  const sandboxRuntime = await preview.locator('body').evaluate((body) => {
    const out = {};
    try { body.ownerDocument.defaultView.parent.document.body.dataset.cross='1'; out.parentDom = 'allowed'; } catch { out.parentDom = 'blocked'; }
    try { body.ownerDocument.defaultView.parent.localStorage.setItem('x', '1'); out.parentStorage = 'allowed'; } catch { out.parentStorage = 'blocked'; }
    try {
      const popup = body.ownerDocument.defaultView.open('https://example.invalid/');
      out.popup = popup ? 'allowed' : 'blocked';
      popup?.close?.();
    } catch { out.popup = 'blocked'; }
    return out;
  });
  assert.deepEqual(sandboxRuntime, { parentDom: 'blocked', parentStorage: 'blocked', popup: 'blocked' });
  await page.evaluate(() => window.fixtureEdit(3,'<img src=x onerror="parent.document.body.dataset.poison=1">'));
  await page.locator('[data-action="summarize"]').click();
  assert.equal(await page.locator('#thread img').count(),0);
  await page.locator('[data-action="extract"]').click();
  assert.equal(await page.locator('#thread img').count(),0);
  await page.locator('#ask').fill('<img onerror="x">');
  await page.locator('#composer button').click();
  assert.equal(await page.locator('#thread img').count(),0);
  await page.locator('[data-action="escalate"]').click();
  const ticketsBefore = await page.locator('#thread .ticket').count();
  await page.evaluate(() => window.fixtureType('ask file a ticket\r'));
  assert.equal(await page.locator('#thread .ticket').count(), ticketsBefore + 1);
  assert.match(await page.locator('#thread').innerText(),/session only/);
  const credentialLeak = await page.evaluate(() => {
    const keys = ['AI_GATEWAY_API_KEY','GEMINI_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY','UPSTASH_REDIS_REST_TOKEN'];
    const hasWindow = [];
    for (const k of keys) {
      try {
        if (typeof window[k] !== 'undefined') hasWindow.push(k);
      } catch {
        // Guarded credential trap itself is expected and should not fail scan.
      }
    }
    const readStorage = (store) => {
      const out = [];
      for (let i = 0; i < store.length; i++) {
        const k = store.key(i);
        const v = store.getItem(k);
        out.push(`${k}:${v}`);
      }
      return out;
    };
    const storage = [...readStorage(window.localStorage), ...readStorage(window.sessionStorage)];
    const exposedStorage = storage.filter((entry) => /(api[_-]?key|token|secret)/i.test(entry));
    const receiptText = document.getElementById('thread')?.innerText || '';
    const exposedReceipts = /(api[_-]?key|token|secret|AIza|sk-)/i.test(receiptText);
    return { hasWindow, exposedStorage, exposedReceipts };
  });
  assert.deepEqual(credentialLeak, { hasWindow: [], exposedStorage: [], exposedReceipts: false });
  assert.deepEqual(errors,[]);
  const sensitiveOutboundRequests = requests.filter(
    (url) =>
      /^https?:/i.test(url) &&
      !url.startsWith(origin + '/') &&
      /(gateway|openai|anthropic|googleapis|api\.uvai|upstash|redis)/i.test(url),
  );
  assert.deepEqual(sensitiveOutboundRequests, []);
  const receipt = {
    status:'VERIFIED',
    head:requiredHead,
    surface:'hybrid-workspace',
    boundary:'Chromium DOM + sandbox',
    externalServices:'disabled',
    prototypeStatus:'prototype-only',
    canonicalSurface:'/studio',
    editor:'fixture adapter',
    checks:[
      'identity',
      'embed',
      'edited summary',
      'extract',
      'ask escaping',
      'terminal escalation',
      'sandbox confinement',
      'credential access trap',
      'storage/query boundary',
      'network isolation',
      'console health',
    ],
  };
  if (receiptPath) {
    await writeFile(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
  }
  console.log(JSON.stringify(receipt));
} finally { await browser?.close(); await new Promise(r=>server.close(r)); }
