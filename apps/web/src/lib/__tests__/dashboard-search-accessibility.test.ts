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

  it('communicates the search loading state on the Go button via aria-busy', () => {
    const source = readSource('components/dashboard/panels.tsx');
    const goButton = source.match(
      /<button\s+type="submit"[\s\S]*?{searchLoading \? '…' : 'Go'}/,
    )?.[0];

    expect(goButton).toBeDefined();
    expect(goButton).toContain('aria-busy={searchLoading || undefined}');
  });

  it('gives dashboard panel controls a visible keyboard focus state that meets the WCAG 2.2 SC 2.4.11 3:1 contrast floor', () => {
    const source = readSource('components/dashboard/panels.tsx');

    // Dispatch (indigo-400) and Refresh (white) rings composite against the
    // ~#0e0e13 dashboard background; the opacities below are the minimum that
    // clear the 3:1 focus-indicator contrast ratio. Guard against regressing
    // them back to the sub-threshold /50 and /30 values.
    expect(source).toContain('focus-visible:ring-indigo-400/70');
    expect(source).toContain('focus-visible:ring-white/40');
    expect(source).not.toContain('focus-visible:ring-indigo-400/50');
    expect(source).not.toContain('focus-visible:ring-white/30');
  });
});
