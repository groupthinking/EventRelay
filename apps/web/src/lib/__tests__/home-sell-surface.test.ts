import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const webRoot = join(dirname(fileURLToPath(import.meta.url)), '../../..');
const webSrc = join(webRoot, 'src');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

function readWebFile(relativePath: string) {
  return readFileSync(join(webRoot, relativePath), 'utf8');
}

describe('Home is a sell page; Studio is the workbench', () => {
  it('does not mount OneLoopStudio or the Loading studio fallback on /', () => {
    const home = readSource('app/page.tsx');
    expect(home).not.toContain('OneLoopStudio');
    expect(home).not.toContain('Loading studio');
    expect(home).toContain('Universal Video Action Intelligence');
    expect(home).toContain('HomePasteForm');
    expect(home).toContain('$199');
    expect(home).toContain('Get Pro');
    expect(home).not.toContain('$19/mo');
    expect(home).not.toContain('$180');
  });

  it('keeps the live workbench only on /studio', () => {
    const studio = readSource('app/studio/page.tsx');
    expect(studio).toContain('OneLoopStudio');
    expect(readSource('components/OneLoopStudio.tsx')).toContain('resolveStudioHandoff');
    expect(readSource('components/OneLoopStudio.tsx')).toContain('autoStartedKey');
  });

  it('sends Home paste into /studio?video= via the shared handoff helper', () => {
    const paste = readSource('components/home/HomePasteForm.tsx');
    expect(paste).toContain('studioVideoHref');
    expect(paste).toContain("router.push");
    expect(paste).not.toContain('processVideo');
    expect(paste).not.toContain('OneLoopStudio');
  });

  it('prioritizes Home, Studio, and Pricing in the sitemap', () => {
    const sitemap = readSource('app/sitemap.ts');
    expect(sitemap).toContain("'/studio'");
    expect(sitemap).toContain("'/pricing'");
    expect(sitemap).not.toContain("'/features'");
    expect(sitemap).not.toContain("'/playground'");
  });

  it('308s retired marketing surfaces into Home and dashboard skins into Studio', () => {
    const config = readWebFile('next.config.js');
    expect(config).toContain("source: '/features'");
    expect(config).toContain("source: '/playground'");
    expect(config).toMatch(/source: '\/features'[\s\S]*destination: '\/'/);
    expect(config).toMatch(/source: '\/playground'[\s\S]*destination: '\/'/);
    expect(config).toContain("source: '/dashboard'");
    expect(config).toContain("destination: '/studio'");
  });
});
