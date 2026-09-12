#!/usr/bin/env node
/**
 * #1538: @workflow/world-vercel calls global/Next `fetch` with an npm-undici
 * Agent as `dispatcher`. Those are different undici class copies, so
 * dispatch() throws "Cannot read private member #P".
 *
 * Remove the custom dispatcher from world-vercel call sites that ultimately
 * reach Node/Next global fetch. For world-local, use npm `undici.fetch` with
 * the npm `Agent` so its long-running-step timeout configuration is preserved.
 * Idempotent. Safe to skip if the package is absent.
 *
 * Lives under apps/web. Root .vercelignore must use `/scripts/` (anchored).
 * An unanchored `scripts/` deletes this file after clone (dpl_81Nh / dpl_8y6i).
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);

export function patchSource(src) {
  const hasAffectedCallSite =
    src.includes('await fetch(') ||
    src.includes('await undiciFetch(') ||
    src.includes('dispatcher: getDispatcher(');
  if (!hasAffectedCallSite) {
    return { src, result: 'no-fetch-call' };
  }
  let next = src;
  // Keep global/Next fetch. undici.fetch rejects Request objects
  // ("Failed to parse URL from [object Request]") which getRun uses.
  // dpl_BBme started (runId) but status poll 500'd after the rename.
  if (next.includes('fetch as undiciFetch')) {
    next = next.replace(
      /^import \{ fetch as undiciFetch \} from 'undici';\n/m,
      '',
    );
    next = next.replaceAll('await undiciFetch(', 'await fetch(');
  }
  // Do not pass Agent across fetch (#P / #dispatch).
  next = next
    .replace(/\s*dispatcher:\s*getDispatcher\([^)]*\),?/g, '')
    .replace(/^\s*dispatcher,\s*$/gm, '');
  if (next === src) {
    return { src, result: 'already-patched' };
  }
  return { src: next, result: 'patched' };
}

export function patchWorldLocalSource(src) {
  const hasLocalQueueCall =
    src.includes('dispatcher: httpAgent') ||
    src.includes('undiciFetch(createWorkflowUrl(');
  if (!hasLocalQueueCall) {
    return { src, result: 'no-local-queue-call' };
  }

  let next = src
    .replace(
      "import { Agent } from 'undici';",
      "import { Agent, fetch as undiciFetch } from 'undici';",
    )
    .replace(
      'response = await fetch(createWorkflowUrl(',
      'response = await undiciFetch(createWorkflowUrl(',
    );
  if (next === src) {
    return { src, result: 'already-patched' };
  }
  return { src: next, result: 'patched' };
}

export function patchFile(absPath, transform = patchSource) {
  const original = fs.readFileSync(absPath, 'utf8');
  const { src, result } = transform(original);
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

export function resolveWorldLocalRoot() {
  try {
    let dir = path.dirname(require.resolve('@workflow/world-local'));
    while (dir !== path.dirname(dir)) {
      const pkgPath = path.join(dir, 'package.json');
      if (fs.existsSync(pkgPath)) {
        const name = JSON.parse(fs.readFileSync(pkgPath, 'utf8')).name;
        if (name === '@workflow/world-local') {
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
    path.resolve(process.cwd(), 'node_modules/@workflow/world-local'),
    path.resolve(process.cwd(), '../node_modules/@workflow/world-local'),
    path.resolve(process.cwd(), '../../node_modules/@workflow/world-local'),
    path.resolve(here, '../../node_modules/@workflow/world-local'),
    path.resolve(here, '../../../node_modules/@workflow/world-local'),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(path.join(candidate, 'dist', 'queue.js'))) {
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
    { abs: path.join(pkgRoot, 'dist', 'utils.js'), transform: patchSource },
    { abs: path.join(pkgRoot, 'dist', 'http-core.js'), transform: patchSource },
    { abs: path.join(pkgRoot, 'dist', 'queue.js'), transform: patchSource },
  ];
  const localRoot = resolveWorldLocalRoot();
  if (localRoot) {
    targets.push({
      abs: path.join(localRoot, 'dist', 'queue.js'),
      transform: patchWorldLocalSource,
    });
  }
  const results = [];
  for (const { abs, transform } of targets) {
    if (!fs.existsSync(abs)) {
      console.log(`[patch-world-vercel] skip missing ${abs}`);
      results.push('missing');
      continue;
    }
    const result = patchFile(abs, transform);
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
