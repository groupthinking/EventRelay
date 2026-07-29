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

    // Extract the specific <button> opening tag that owns a given onClick
    // handler, so each assertion is bound to its own control rather than to
    // the file at large. The closing `>` of a JSX opening tag sits on its own
    // line here, which lets us stop at it without tripping over the `=>` in
    // the arrow handler.
    const buttonTagFor = (handler: string) => {
      const openingTags = source.match(/<button\b[\s\S]*?\n\s*>/g) ?? [];
      return openingTags.find((tag) => tag.includes(handler));
    };

    // Dispatch (indigo-400) and Refresh (white) rings composite against the
    // ~#0e0e13 dashboard background; the opacities asserted below are the
    // minimum that clear the 3:1 focus-indicator contrast ratio. Asserting on
    // each button's own tag guards against a regression on one button being
    // masked by the class merely existing elsewhere, and vice versa.
    const dispatchButton = buttonTagFor('onDispatch(video.id)');
    expect(dispatchButton).toBeDefined();
    expect(dispatchButton).toContain('focus-visible:ring-2');
    expect(dispatchButton).toContain('focus-visible:ring-indigo-400/70');
    expect(dispatchButton).not.toContain('focus-visible:ring-indigo-400/50');

    const refreshButton = buttonTagFor('onRefresh(video.id)');
    expect(refreshButton).toBeDefined();
    expect(refreshButton).toContain('focus-visible:ring-2');
    expect(refreshButton).toContain('focus-visible:ring-white/40');
    expect(refreshButton).not.toContain('focus-visible:ring-white/30');
  });
});
