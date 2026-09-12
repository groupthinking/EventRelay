import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

describe('auth configuration source safety', () => {
  it('uses the local login page instead of the default Auth.js sign-in page', () => {
    const source = readSource('lib/auth.ts');
    expect(source).toContain("signIn: '/login'");
    expect(source).not.toContain("signIn: '/api/auth/signin'");
  });

  it('keeps the Google sign-in asset local to avoid CSP-hosted icon failures', () => {
    const source = readSource('app/login/GoogleSignInButton.tsx');
    expect(source).toContain("signIn('google'");
    expect(source).toContain("from 'lucide-react'");
    expect(source).toContain('<LogIn');
    expect(source).not.toContain('<svg');
    expect(source).not.toContain('<Image');
  });

  it('prefers canonical Google OAuth env names while retaining legacy fallbacks', () => {
    const source = readSource('lib/auth.ts');
    expect(source.indexOf('process.env.GOOGLE_CLIENT_ID')).toBeLessThan(
      source.indexOf('process.env.GOOGLE_OAUTH_CLIENT_ID'),
    );
    expect(source.indexOf('process.env.GOOGLE_CLIENT_SECRET')).toBeLessThan(
      source.indexOf('process.env.GOOGLE_OAUTH_CLIENT_SECRET'),
    );
  });

  it('keeps the root route as a sell Home instead of redirecting to the dashboard', () => {
    const source = readSource('app/page.tsx');
    expect(source).not.toContain("redirect('/dashboard')");
    expect(source).not.toContain('OneLoopStudio');
    expect(source).toContain('HomePasteForm');
  });

  it('folds the retired dashboard skin into the studio', () => {
    const dashboard = readSource('app/dashboard/page.tsx');
    expect(dashboard).toContain('canonicalStudioPath');
    expect(dashboard).toContain('redirect(');
    expect(dashboard).not.toContain('DashboardSplitView');
    expect(dashboard).not.toContain('VideoCard');
  });
});
