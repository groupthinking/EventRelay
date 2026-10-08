// Browser plugin not available. Uses Playwright Chromium and actual app modules,
// with fixture adapters for CDN editor/terminal/layout APIs; no live Gateway.
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
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
  page.on('pageerror', e => errors.push(e.message));
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
  await page.locator('[data-action="embed"]').click();
  assert.match(await page.locator('#thread').innerText(),/Split screen stays locked/);
  await page.evaluate(() => window.fixtureEdit(0,'<title>Edited</title><h1>New</h1><script>try { parent.document.body.dataset.poison="1" } catch { document.body.dataset.confined="1" }</script>'));
  await page.locator('[data-action="summarize"]').click();
  assert.match(await page.locator('#thread').innerText(),/Edited/);
  assert.equal(await page.locator('body').getAttribute('data-poison'),null);
  const preview = page.frameLocator('#preview');
  await preview.locator('body[data-confined="1"]').waitFor();
  await page.evaluate(() => window.fixtureEdit(3,'<img src=x onerror="parent.document.body.dataset.poison=1">'));
  await page.locator('[data-action="summarize"]').click();
  assert.equal(await page.locator('#thread img').count(),0);
  await page.locator('[data-action="extract"]').click();
  assert.equal(await page.locator('#thread img').count(),0);
  await page.locator('#ask').fill('<img onerror="x">');
  await page.locator('#composer button').click();
  assert.equal(await page.locator('#thread img').count(),0);
  await page.locator('[data-action="escalate"]').click();
  await page.evaluate(() => window.fixtureType('ask file a ticket\r'));
  assert.match(await page.locator('#thread').innerText(),/session only/);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({status:'VERIFIED',surface:'hybrid-workspace',boundary:'Chromium DOM + sandbox',externalServices:'disabled',editor:'fixture adapter',checks:['identity','embed','edited summary','extract','ask escaping','terminal escalation','sandbox confinement','credential access trap','console health']}));
} finally { await browser?.close(); await new Promise(r=>server.close(r)); }
