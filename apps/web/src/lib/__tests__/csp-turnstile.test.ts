import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const nextConfigPath = join(
  dirname(fileURLToPath(import.meta.url)),
  '../../../next.config.js',
);

function extractCspString(source: string): string {
  const match = source.match(
    /const contentSecurityPolicy = \[([\s\S]*?)\]\.join\('; '\);/,
  );
  if (!match) {
    throw new Error('contentSecurityPolicy not found in next.config.js');
  }
  const directives = [...match[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
  if (directives.length === 0) {
    throw new Error('contentSecurityPolicy has no directive strings');
  }
  return directives.join('; ');
}

function parseCspDirectives(csp: string): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const part of csp.split(';')) {
    const tokens = part.trim().split(/\s+/).filter(Boolean);
    if (tokens.length === 0) continue;
    const [directive, ...sources] = tokens;
    map.set(directive, sources);
  }
  return map;
}

describe('CSP allows Cloudflare Turnstile on Pro checkout', () => {
  const csp = extractCspString(readFileSync(nextConfigPath, 'utf8'));
  const directives = parseCspDirectives(csp);

  it('includes challenges.cloudflare.com in script-src so turnstile api.js can load', () => {
    expect(directives.get('script-src')).toContain(
      'https://challenges.cloudflare.com',
    );
  });

  it('includes challenges.cloudflare.com in frame-src so the widget iframe can render', () => {
    expect(directives.get('frame-src')).toContain(
      'https://challenges.cloudflare.com',
    );
  });

  it('includes challenges.cloudflare.com in connect-src so the widget is not blocked by a restrictive connect-src', () => {
    expect(directives.get('connect-src')).toContain(
      'https://challenges.cloudflare.com',
    );
  });

  it('keeps existing Stripe script-src and frame-src hosts', () => {
    expect(directives.get('script-src')).toContain('https://js.stripe.com');
    expect(directives.get('frame-src')).toContain('https://js.stripe.com');
    expect(directives.get('frame-src')).toContain('https://hooks.stripe.com');
  });
});
