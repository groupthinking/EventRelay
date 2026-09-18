import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

describe('dashboard search accessibility', () => {
  it('keeps a programmatic label on the search input without overriding the Go button name', () => {
    const source = readSource('components/dashboard/panels.tsx');
    const searchForm = source.match(
      /<form[\s\S]*?<label htmlFor="search-video" className="sr-only">[\s\S]*?{searchLoading \? '…' : 'Go'}[\s\S]*?<\/form>/,
    )?.[0];

    expect(searchForm).toBeDefined();
    expect(searchForm).toContain('<label htmlFor="search-video" className="sr-only">');
    expect(searchForm).toContain('id="search-video"');
    expect(searchForm).not.toContain('aria-label="Submit search"');
    expect(searchForm).not.toContain('aria-label="Search"');
  });

  it('labels a prepared action plan as review state rather than active dispatch', () => {
    const source = readSource('components/dashboard/panels.tsx');

    expect(source).toContain("isPrepared ? 'Status: prepared for review'");
    expect(source).toContain('nothing below\n              has run yet');
  });
});
