/* @vitest-environment jsdom */
import type { ReactNode } from 'react';
import { act } from 'react';
import { hydrateRoot, type Root } from 'react-dom/client';
import { renderToString } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { StructuredData } from '@/components/StructuredData';
import RootLayout from './layout';

vi.mock('next/font/google', () => {
  const font = ({ variable }: { variable: string }) => ({ variable });
  return { Inter: font, JetBrains_Mono: font, Space_Grotesk: font };
});

vi.mock('@vercel/analytics/next', () => ({ Analytics: () => null }));
vi.mock('@vercel/speed-insights/next', () => ({ SpeedInsights: () => null }));
vi.mock('@/components/AuthSessionProvider', () => ({
  AuthSessionProvider: ({ children }: { children: ReactNode }) => children,
}));

const jsonLdSelector = 'script[type="application/ld+json"]';
const layout = (
  <RootLayout>
    <main id="page-content">UVAI Studio</main>
  </RootLayout>
);

let root: Root | null = null;

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  document.open();
  document.write(`<!DOCTYPE html>${renderToString(layout)}`);
  document.close();
});

afterEach(async () => {
  if (root) {
    await act(async () => root?.unmount());
    root = null;
  }
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.open();
  document.write('<!DOCTYPE html><html><head></head><body></body></html>');
  document.close();
});

describe('Root layout structured data', () => {
  it('server-renders unchanged JSON-LD inside the body content wrapper', () => {
    expect(document.head.querySelector(jsonLdSelector)).toBeNull();
    const script = document.body.querySelector(jsonLdSelector);
    expect(script?.outerHTML).toBe(renderToString(<StructuredData />));
    expect(script?.parentElement).toBe(document.getElementById('page-content')?.parentElement);
    expect(JSON.parse(script?.textContent ?? '')).toMatchObject({
      '@context': 'https://schema.org',
      '@type': 'HowTo',
      name: 'Open the UVAI Studio workbench from a YouTube URL',
      step: [
        { '@type': 'HowToStep', position: 1, name: 'Paste URL' },
        { '@type': 'HowToStep', position: 2, name: 'Open Studio' },
        { '@type': 'HowToStep', position: 3, name: 'Use the workbench' },
      ],
    });
  });

  it.each([
    { scenario: 'without preview injection', injectScript: false },
    { scenario: 'with an inline preview script prepended to head', injectScript: true },
  ])('hydrates without replacing server content $scenario', async ({ injectScript }) => {
    const originalContent = document.getElementById('page-content');
    const originalJsonLd = document.querySelector(jsonLdSelector);
    const originalJsonLdText = originalJsonLd?.textContent;
    expect(originalContent).not.toBeNull();
    expect(originalJsonLd).not.toBeNull();

    const previewScript = document.createElement('script');
    previewScript.textContent = 'window.__V0_SANDBOX_ID__="hydration-test";';
    const previewScriptText = previewScript.textContent;
    if (injectScript) document.head.prepend(previewScript);

    const onRecoverableError = vi.fn();
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    await act(async () => {
      root = hydrateRoot(document, layout, { onRecoverableError });
    });

    expect(onRecoverableError).not.toHaveBeenCalled();
    expect(consoleError).not.toHaveBeenCalled();
    expect(document.getElementById('page-content')).toBe(originalContent);
    expect(document.querySelectorAll(jsonLdSelector)).toHaveLength(1);
    expect(document.querySelector(jsonLdSelector)).toBe(originalJsonLd);
    expect(originalJsonLd?.textContent).toBe(originalJsonLdText);
    if (injectScript) {
      expect(document.head.contains(previewScript)).toBe(true);
      expect(previewScript.textContent).toBe(previewScriptText);
      expect(previewScript.hasAttribute('type')).toBe(false);
    }
  });
});
