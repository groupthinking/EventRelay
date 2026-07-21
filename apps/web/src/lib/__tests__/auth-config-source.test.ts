import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

describe('auth configuration source safety', () => {
  it('does not point NextAuth custom signIn page at its own API route', () => {
    const source = readSource('lib/auth.ts');
    expect(source).not.toContain("signIn: '/api/auth/signin'");
  });

  it('accepts both project-specific and common Google OAuth env names with standard names prioritized over legacy fallback names', () => {
    const source = readSource('lib/auth.ts');
    expect(source).toContain('GOOGLE_OAUTH_CLIENT_ID');
    expect(source).toContain('GOOGLE_CLIENT_ID');
    expect(source).toContain('GOOGLE_OAUTH_CLIENT_SECRET');
    expect(source).toContain('GOOGLE_CLIENT_SECRET');

    // Verify canonical precedence ordering in process.env lookups
    const idIdxCanonical = source.indexOf('process.env.GOOGLE_CLIENT_ID');
    const idIdxFallback = source.indexOf('process.env.GOOGLE_OAUTH_CLIENT_ID');
    expect(idIdxCanonical).toBeGreaterThan(-1);
    expect(idIdxFallback).toBeGreaterThan(-1);
    expect(idIdxCanonical).toBeLessThan(idIdxFallback);

    const secretIdxCanonical = source.indexOf('process.env.GOOGLE_CLIENT_SECRET');
    const secretIdxFallback = source.indexOf('process.env.GOOGLE_OAUTH_CLIENT_SECRET');
    expect(secretIdxCanonical).toBeGreaterThan(-1);
    expect(secretIdxFallback).toBeGreaterThan(-1);
    expect(secretIdxCanonical).toBeLessThan(secretIdxFallback);
  });

  it('keeps the root route as a landing page instead of redirecting to the app', () => {
    const source = readSource('app/page.tsx');
    expect(source).not.toContain("redirect('/dashboard')");
    expect(source).toContain('Turn any video into actions, insights, and agent workflows.');
  });
});
