#!/usr/bin/env node
/**
 * #1538: @workflow/world-vercel calls global/Next `fetch` with an npm-undici
 * Agent as `dispatcher`. Those are different undici class copies, so
 * dispatch() throws "Cannot read private member #P".
 *
 * Rebind those two call sites to `undici.fetch` from the same package as Agent.
 * Idempotent. Safe to skip if the package is absent.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function patchFile(absPath) {
  let src = fs.readFileSync(absPath, 'utf8');
  if (src.includes('fetch as undiciFetch')) {
    return 'already-patched';
  }
  if (!src.includes('await fetch(')) {
    return 'no-fetch-call';
  }
  if (!src.includes("from 'undici'") && !src.includes('from "undici"')) {
    src = `import { fetch as undiciFetch } from 'undici';\n${src}`;
  }
  src = src.replaceAll('await fetch(', 'await undiciFetch(');
  fs.writeFileSync(absPath, src);
  return 'patched';
}

const pkgRoot = path.join(root, 'node_modules', '@workflow', 'world-vercel');
const targets = [
  path.join(pkgRoot, 'dist', 'utils.js'),
  path.join(pkgRoot, 'dist', 'http-core.js'),
];

for (const abs of targets) {
  if (!fs.existsSync(abs)) {
    console.log(`[patch-world-vercel] skip missing ${path.relative(root, abs)}`);
    continue;
  }
  const result = patchFile(abs);
  console.log(`[patch-world-vercel] ${path.relative(root, abs)} ${result}`);
}
