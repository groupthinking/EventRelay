/**
 * Static guard for audit finding F4: no server module may write to a path
 * derived from `process.cwd()`.
 *
 * ## Why a source scan rather than a runtime test
 *
 * The bug class is invisible at runtime in the environment where it is written.
 * `data/training/*.jsonl`, `data/embeddings/*.json`, and `.data/entitlements.json`
 * all worked perfectly on a developer laptop and threw EROFS on every single
 * Vercel invocation, because the deployed bundle is mounted read-only. Several
 * of the call sites then swallowed the error, so the failure surfaced as
 * "no training examples" and "no embeddings for this video" — plausible empty
 * states rather than a broken store. No unit test running locally would have
 * caught it; only reading the source does.
 *
 * ## What is allowed
 *
 * A `process.cwd()`-rooted write is permitted only when it is unreachable in
 * production. In practice that means the module gates the branch on
 * `NODE_ENV !== 'production'`. That is the "explicit dev-only branch, never a
 * silent default" rule from the delivery plan, enforced rather than documented.
 *
 * Writes to an operator-supplied absolute path (e.g. `KAIZEN_TRACE_PATH`) are
 * not in scope: the operator chose a writable location, and nothing is assumed
 * about the bundle.
 */

import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = path.resolve(__dirname, '../..');

/** Node filesystem mutations. Read APIs are deliberately absent. */
const WRITE_CALL =
  /\b(writeFile|writeFileSync|appendFile|appendFileSync|mkdir|mkdirSync|createWriteStream|rename|renameSync|copyFile|copyFileSync|rm|rmSync|unlink|unlinkSync|truncate|truncateSync)\s*\(/;

const CWD = /process\.cwd\(\)/;

/** Marks a module whose cwd usage is fenced off from production. */
const DEV_GUARD = /NODE_ENV\s*!==\s*['"]production['"]/;

/**
 * Every non-test TypeScript file under `src`.
 *
 * Hand-rolled rather than using a glob package so the guard has no dependency
 * that could be dropped from the tree and take the suite's coverage with it.
 */
function serverSourceFiles(dir: string = SRC, found: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === '__tests__') continue;
      serverSourceFiles(full, found);
      continue;
    }
    if (!/\.tsx?$/.test(entry.name)) continue;
    if (/\.test\.tsx?$/.test(entry.name)) continue;
    found.push(full);
  }
  return found;
}

describe('F4 regression: no server module writes under process.cwd()', () => {
  const files = serverSourceFiles();

  it('finds source files to scan', () => {
    // A glob that silently matches nothing would make this suite vacuously
    // green, which is worse than no suite at all.
    expect(files.length).toBeGreaterThan(100);
  });

  it('every module combining process.cwd() with a write is dev-guarded', () => {
    const offenders: string[] = [];

    for (const file of files) {
      const source = readFileSync(file, 'utf8');
      if (!CWD.test(source)) continue;
      if (!WRITE_CALL.test(source)) continue;
      if (DEV_GUARD.test(source)) continue;
      offenders.push(path.relative(SRC, file));
    }

    expect(
      offenders,
      'These modules write to a process.cwd() path with no production guard. ' +
        'On Vercel that filesystem is read-only, so the write throws at runtime. ' +
        'Move the data to Postgres, Blob, or KV — and if a local file is genuinely ' +
        'wanted for development, gate the branch on NODE_ENV !== "production".',
    ).toEqual([]);
  });
});

describe('F4 regression: the stores that caused the finding stay migrated', () => {
  it.each([
    ['training-store.ts', 'lib/training-store.ts'],
    ['embedding-store.ts', 'lib/embedding-store.ts'],
  ])('%s persists through the database client', (_name, relative) => {
    const source = readFileSync(path.join(SRC, relative), 'utf8');
    expect(source).toMatch(/@\/lib\/db\/client/);
  });

  it('entitlement writes reach the durable store before the local mirror', () => {
    const source = readFileSync(path.join(SRC, 'lib/billing/entitlement-store.ts'), 'utf8');
    const durable = source.indexOf('await redis.set(');
    // The call site, not the prose above it: the doc comment explaining the
    // original bug also names this function, and matching that made the
    // assertion pass for the wrong reason.
    const mirror = source.indexOf('await writeEntitlementToFile(stored)');
    expect(durable).toBeGreaterThan(-1);
    expect(mirror).toBeGreaterThan(-1);
    // The original ordering charged customers whose entitlement was never
    // recorded: the filesystem mirror threw EROFS before the Redis write ran.
    expect(durable).toBeLessThan(mirror);
  });
});
