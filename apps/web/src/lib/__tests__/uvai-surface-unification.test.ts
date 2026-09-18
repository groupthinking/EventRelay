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

describe('UVAI is one product surface', () => {
  it('keeps Home as a sell page and Studio as the sole workbench', () => {
    const home = readSource('app/page.tsx');
    const studio = readSource('app/studio/page.tsx');
    expect(home).not.toContain('OneLoopStudio');
    expect(studio).toContain('OneLoopStudio');
    expect(home).not.toContain("redirect('/dashboard')");
  });

  it('does not link the studio footer or primary nav to the retired library', () => {
    const nav = readSource('components/Nav.tsx');
    const studio = readSource('components/OneLoopStudio.tsx');
    expect(nav).not.toContain("href: '/dashboard'");
    expect(nav).toContain("href: '/'");
    expect(nav).toContain("label: 'Home'");
    expect(nav).toContain("href: '/studio'");
    expect(nav).toContain("label: 'Studio'");
    expect(nav).not.toContain("href: '/features'");
    expect(nav).toContain("href: '/pricing'");
    expect(studio).not.toContain('href="/dashboard"');
    expect(studio).toContain('Stack checks');
  });

  it('308s /dashboard, /app, and /prototype into the canonical workbench', () => {
    const config = readWebFile('next.config.js');
    expect(config).toContain("source: '/dashboard'");
    expect(config).toContain("destination: '/studio'");
    expect(config).toContain("source: '/dashboard/:path*'");
    expect(config).toContain("source: '/app'");
    expect(config).toContain("source: '/prototype'");
    expect(config).toContain('permanent: true');
    expect(config).not.toMatch(/source: '\/app'[\s\S]{0,80}destination: '\/'/);
    expect(config).not.toMatch(/source: '\/prototype'[\s\S]{0,80}destination: '\/'/);
  });

  it('points sell-page CTAs at Home or Studio, not a second skin', () => {
    const features = readSource('app/features/page.tsx');
    const pricing = readSource('app/pricing/page.tsx');
    const landingNav = readSource('components/landing/LandingNav.tsx');
    expect(features).toContain('redirect(');
    expect(pricing).toContain("from '@/components/Nav'");
    expect(features).not.toContain('href="/dashboard"');
    expect(pricing).not.toContain('href="/dashboard"');
    expect(landingNav).not.toContain('href="/dashboard"');
    expect(landingNav).toContain("href: '/studio'");
  });

  it('keeps stack-check unlock on the same OneLoopStudio page', () => {
    const studio = readSource('components/OneLoopStudio.tsx');
    expect(studio).toContain('packFormation.checks');
    expect(studio).toContain('setCompletedChecks');
    expect(studio).not.toMatch(/window\.location\.(href|assign).*dashboard/);
    expect(studio).not.toMatch(/router\.push\(['"`]\/dashboard/);
  });

  it('does not hold anonymous Deploy behind non-runnable stack checks', () => {
    const studio = readSource('components/OneLoopStudio.tsx');
    expect(studio).toContain("deployHoldReason(linkedSop, completedChecks, 'anonymous')");
    expect(studio).toContain('stackCheckStatus');
    expect(studio).toContain('stackCheckStatusLabel');
    expect(studio).not.toContain('href="/ship"');
  });
});
