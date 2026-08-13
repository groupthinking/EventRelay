import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  patchFile,
  patchInstalledWorldVercel,
  patchSource,
  resolveWorldVercelRoot,
} from '../../../scripts/patch-world-vercel-undici-fetch.mjs';

const VERCELIGNORE = fs.readFileSync(
  path.resolve(import.meta.dirname, '../../../../../.vercelignore'),
  'utf8',
);

const FIXTURE = `import { getDispatcher } from './http-client.js';
export async function doRequest(request) {
  const response = await fetch(request, {
    dispatcher: getDispatcher(),
  });
  return response;
}
`;

describe('patch-world-vercel-undici-fetch (issue #1538)', () => {
  it('externalizes undici and world-vercel so webpack cannot split them', () => {
    const config = fs.readFileSync(
      path.resolve(import.meta.dirname, '../../../next.config.js'),
      'utf8',
    );
    expect(config).toMatch(
      /serverExternalPackages:\s*\[[^\]]*'undici'[^\]]*'@workflow\/world-vercel'/,
    );
  });

  it('does not let .vercelignore delete apps/web/scripts', () => {
    const patterns = VERCELIGNORE.split('\n')
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#'));
    expect(patterns).not.toContain('scripts/');
    expect(patterns).toContain('/scripts/');
  });

  it('rewrites await fetch( to undici.fetch from the same module as Agent', () => {
    const { src, result } = patchSource(FIXTURE);
    expect(result).toBe('patched');
    expect(src).toContain("import { fetch as undiciFetch } from 'undici';");
    expect(src).toContain('await undiciFetch(request, {');
    expect(src).not.toContain('await fetch(');
  });

  it('is idempotent', () => {
    const once = patchSource(FIXTURE);
    const twice = patchSource(once.src);
    expect(twice.result).toBe('already-patched');
    expect(twice.src).toBe(once.src);
  });

  it('leaves files without the WDK call site alone', () => {
    const { src, result } = patchSource("export const ping = () => 'ok';\n");
    expect(result).toBe('no-fetch-call');
    expect(src).toBe("export const ping = () => 'ok';\n");
  });

  it('writes the rewrite to disk', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'world-vercel-patch-'));
    const file = path.join(dir, 'utils.js');
    fs.writeFileSync(file, FIXTURE);
    expect(patchFile(file)).toBe('patched');
    expect(patchFile(file)).toBe('already-patched');
    const written = fs.readFileSync(file, 'utf8');
    expect(written).toContain('await undiciFetch(');
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it('installed @workflow/world-vercel call sites use undiciFetch', () => {
    const results = patchInstalledWorldVercel();
    expect(results).not.toContain('not-installed');
    const pkgRoot = resolveWorldVercelRoot();
    expect(pkgRoot).toBeTruthy();
    const utils = fs.readFileSync(
      path.join(pkgRoot as string, 'dist', 'utils.js'),
      'utf8',
    );
    const httpCore = fs.readFileSync(
      path.join(pkgRoot as string, 'dist', 'http-core.js'),
      'utf8',
    );
    expect(utils).toContain('await undiciFetch(');
    expect(httpCore).toContain('await undiciFetch(');
  });
});
