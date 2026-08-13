#!/usr/bin/env node
/**
 * #1538: @workflow/world-vercel calls global/Next `fetch` with an npm-undici
 * Agent as `dispatcher`. Those are different undici class copies, so
 * dispatch() throws "Cannot read private member #P".
 *
 * Rebind those two call sites to `undici.fetch` from the same package as Agent.
 * Idempotent. Safe to skip if the package is absent.
 *
 * Lives under apps/web so Vercel (rootDirectory apps/web / turbo prune)
 * includes it. A root postinstall cannot see repo-root scripts/ on preview
 * (dpl_81NhhsSk95m78rT9uq8HjWBCcTSZ MODULE_NOT_FOUND).
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);

export function patchSource(src) {
  if (src.includes('fetch as undiciFetch')) {
    return { src, result: 'already-patched' };
  }
  if (!src.includes('await fetch(')) {
    return { src, result: 'no-fetch-call' };
  }
  let next = src;
  if (!next.includes('fetch as undiciFetch')) {
    next = `import { fetch as undiciFetch } from 'undici';\n${next}`;
  }
  next = next.replaceAll('await fetch(', 'await undiciFetch(');
  return { src: next, result: 'patched' };
}

export function patchFile(absPath) {
  const original = fs.readFileSync(absPath, 'utf8');
  const { src, result } = patchSource(original);
  if (result === 'patched') {
    fs.writeFileSync(absPath, src);
  }
  return result;
}

export function resolveWorldVercelRoot() {
  try {
    // package.json is not in the package "exports" map
    // (ERR_PACKAGE_PATH_NOT_EXPORTED). Resolve the entry and walk up.
    let dir = path.dirname(require.resolve('@workflow/world-vercel'));
    while (dir !== path.dirname(dir)) {
      const pkgPath = path.join(dir, 'package.json');
      if (fs.existsSync(pkgPath)) {
        const name = JSON.parse(fs.readFileSync(pkgPath, 'utf8')).name;
        if (name === '@workflow/world-vercel') {
          return dir;
        }
      }
      dir = path.dirname(dir);
    }
  } catch {
    // fall through to path candidates
  }
  const here = path.dirname(fileURLToPath(import.meta.url));
  const candidates = [
    path.resolve(process.cwd(), 'node_modules/@workflow/world-vercel'),
    path.resolve(process.cwd(), '../node_modules/@workflow/world-vercel'),
    path.resolve(process.cwd(), '../../node_modules/@workflow/world-vercel'),
    path.resolve(here, '../../node_modules/@workflow/world-vercel'),
    path.resolve(here, '../../../node_modules/@workflow/world-vercel'),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(path.join(candidate, 'dist', 'utils.js'))) {
      return candidate;
    }
  }
  return null;
}

export function patchInstalledWorldVercel() {
  const pkgRoot = resolveWorldVercelRoot();
  if (!pkgRoot) {
    console.log('[patch-world-vercel] skip: @workflow/world-vercel not installed');
    return ['not-installed'];
  }
  const targets = [
    path.join(pkgRoot, 'dist', 'utils.js'),
    path.join(pkgRoot, 'dist', 'http-core.js'),
  ];
  const results = [];
  for (const abs of targets) {
    if (!fs.existsSync(abs)) {
      console.log(`[patch-world-vercel] skip missing ${abs}`);
      results.push('missing');
      continue;
    }
    const result = patchFile(abs);
    console.log(`[patch-world-vercel] ${abs} ${result}`);
    results.push(result);
  }
  return results;
}

const invokedDirectly =
  Boolean(process.argv[1]) &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;

if (invokedDirectly) {
  patchInstalledWorldVercel();
}
