import { escapeHtml, injectVirtualAssets, shouldEscalate, summarizeFrom, parseTermCommand } from "./logic.js";
import assert from "node:assert/strict";

assert.equal(escapeHtml("<img onerror=x>"), "&lt;img onerror=x&gt;");

const html = `<html><head><link rel="stylesheet" href="styles.css" /></head><body><script src="app.js"></script></body></html>`;
const injected = injectVirtualAssets(html, { "styles.css": "body{color:red}", "app.js": "1" });
assert.match(injected, /<style>body\{color:red\}<\/style>/);
assert.match(injected, /<script>1<\/script>/);
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

console.log("hybrid-workspace logic tests passed");
