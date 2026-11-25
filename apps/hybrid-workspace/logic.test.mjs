import { createRequire } from 'node:module';
// jsdom is locked under apps/web (not hoisted to the repo root since #2520),
// so resolve it from that workspace instead of by bare root-level name.
const requireFromWeb = createRequire(new URL('../web/package.json', import.meta.url));
const { JSDOM } = requireFromWeb('jsdom');
globalThis.DOMParser = new JSDOM('').window.DOMParser;
import { escapeHtml, injectVirtualAssets, shouldEscalate, summarizeFrom, parseTermCommand } from "./logic.js";
import assert from "node:assert/strict";

assert.equal(escapeHtml("<img onerror=x>"), "&lt;img onerror=x&gt;");

const html = `<html><head><link rel="stylesheet" href="styles.css" /></head><body><script src="app.js"></script></body></html>`;
const injected = injectVirtualAssets(html, { "styles.css": "body{color:red}", "app.js": "1" });
assert.match(injected, /<style>body\{color:red\}<\/style>/);
assert.match(injected, /<script>1<\/script>/);
assert.match(injectVirtualAssets('<script src="app.js"></script >', {"app.js":"1"}), /<script>1<\/script>/);
assert.doesNotMatch(injected, /src="app\.js"/);

assert.equal(shouldEscalate("help me understand this CSS", "ask"), false);
assert.equal(shouldEscalate("file a ticket please", "ask"), true);
assert.equal(shouldEscalate("", "escalate"), true);

const sum = summarizeFrom({
  "lesson.md": { value: "<script>alert(1)</script>\nmore" },
  "index.html": { value: "<title>Fish</title><h1>Nemo</h1>" },
});
assert.equal(sum.title, "Fish");
assert.equal(sum.headings[0], "Nemo");
assert.doesNotMatch(sum.html, /<script>alert/);

assert.deepEqual(parseTermCommand("summarize"), { action: "summarize", text: "" });
assert.deepEqual(parseTermCommand("ask why css"), { action: "ask", text: "why css" });

assert.equal(shouldEscalate("please file a ticket", "ask"), true);
const reordered = `<link href='styles.css' rel='stylesheet'><script defer src='app.js'></script>`;
const hostile = injectVirtualAssets(reordered, { "styles.css": 'a{content:"$&"}', "app.js": 'console.log("</script><img>")' });
assert.match(hostile, /content:"\$&"/);
assert.doesNotMatch(hostile, /<\/script><img>/);
assert.equal(injectVirtualAssets('<script src="appXjs"></script>', { "app.js": "1" }), '<script src="appXjs"></script>');
assert.equal(injectVirtualAssets('<link href="missing.css">', { "styles.css": "1" }), '<link href="missing.css">');
for (const markup of ['<link data-href="styles.css">', `<link title=' href="styles.css"'>`, '<script data-src="app.js"></script>', `<script title=' src="app.js"'></script>`]) {
  assert.equal(injectVirtualAssets(markup, {"styles.css":"bad", "app.js":"bad"}), markup);
}
assert.equal(summarizeFrom({"index.html":{value:'<title>Edited</title><h1>New</h1>'},"lesson.md":{value:'<img onerror="x">'}}).title,'Edited');

console.log("hybrid-workspace logic tests passed");
