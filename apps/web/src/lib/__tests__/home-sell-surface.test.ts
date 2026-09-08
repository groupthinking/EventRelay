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
    expect(home).toContain('HomeProCheckout');
    expect(home).toContain('Get Pro');
    expect(home).not.toContain('$19/mo');
    expect(home).not.toContain('$180');
  });

  it('does not claim arbitrary-video production E2E or a guaranteed transcript', () => {
    const home = readSource('app/page.tsx');
    const checkout = readSource('components/home/HomeProCheckout.tsx');
    const nav = readSource('components/Nav.tsx');
    const sellCopy = `${home}\n${checkout}\n${nav}`;
    expect(home).toContain('Paste a YouTube URL. Open the Studio workbench.');
    expect(home).toContain('Starts a hashed Video Pack run in Studio (player, events, exports).');
    expect(home).toContain('Transcript quality varies by source');
    expect(home).toContain('not a guaranteed production E2E');
    expect(sellCopy).not.toContain('Ship the work.');
    expect(sellCopy).not.toContain('Not a demo.');
    expect(sellCopy).not.toMatch(/any video/i);
    expect(sellCopy).not.toMatch(/reliable.{0,40}transcript/i);
    expect(sellCopy).not.toMatch(/grounded transcript/i);
  });

  it('keeps the live workbench only on /studio', () => {
    const studio = readSource('app/studio/page.tsx');
    expect(studio).toContain('OneLoopStudio');
    expect(readSource('components/OneLoopStudio.tsx')).toContain('resolveStudioHandoff');
    expect(readSource('components/OneLoopStudio.tsx')).toContain('autoStartedKey');
  });

  it('sends Home paste into /studio?video= after kicking pack emit', () => {
    const paste = readSource('components/home/HomePasteForm.tsx');
    const handoff = readSource('lib/studio-handoff.ts');
    expect(paste).toContain('submitHomePaste');
    expect(paste).toContain('router.push');
    expect(paste).not.toContain('processVideo');
    expect(paste).not.toContain('OneLoopStudio');
    expect(paste).not.toContain('emitVideoPack');
    expect(handoff).toContain('startVideoPackEmit');
    expect(handoff).toContain('submitHomePaste');
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
    expect(config).toContain("source: '/app'");
    expect(config).toContain("source: '/prototype'");
  });

  it('folds Get Pro checkout onto Home via the existing ProCheckoutButton path', () => {
    const home = readSource('app/page.tsx');
    const checkout = readSource('components/home/HomeProCheckout.tsx');
    const button = readSource('components/billing/ProCheckoutButton.tsx');
    const nav = readSource('components/Nav.tsx');
    const pricing = readSource('app/pricing/page.tsx');
    const config = readWebFile('next.config.js');
    expect(home).toContain('HomeProCheckout');
    expect(home).toContain('id="get-pro"');
    expect(home).not.toMatch(/href="\/pricing"[\s\S]{0,80}Get Pro/);
    expect(checkout).toContain("from '@/components/billing/ProCheckoutButton'");
    expect(checkout).toContain('ProCheckoutButton');
    expect(checkout).toContain('Monthly checkout');
    expect(checkout).toContain('Annual checkout');
    expect(checkout).toContain('workflowProPriceLabel');
    expect(checkout).toContain('WORKFLOW_PRO_PRODUCT_NAME');
    expect(checkout).toContain('href="/pricing"');
    expect(checkout).not.toContain('/api/billing/checkout');
    expect(checkout).not.toContain('Maintain');
    expect(checkout).not.toContain('Ship');
    expect(button).toContain("fetch('/api/billing/checkout'");
    expect(button).toContain('turnstileToken');
    expect(nav).toContain('href="/#get-pro"');
    expect(nav).toContain("href: '/pricing'");
    expect(pricing).toContain('ProCheckoutButton');
    expect(pricing).toContain('turnstile');
    expect(config).not.toMatch(/source: '\/pricing'/);
  });
});
