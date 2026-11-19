import type { Metadata } from 'next';
import Link from 'next/link';
import { CANONICAL_STUDIO_PATH, safeCallbackPath } from '@/lib/auth-paths';
import { GoogleSignInButton } from './GoogleSignInButton';

export const metadata: Metadata = {
  title: 'Sign in',
  description: 'Sign in to UVAI with Google to open your studio.',
  alternates: { canonical: '/login' },
  robots: { index: false, follow: true },
};

function authErrorMessage(code: string | undefined): string | null {
  if (!code) return null;
  if (code === 'AccessDenied') {
    return 'Access was restricted or canceled for that account. Core Studio analysis remains open without signing in.';
  }
  return 'Sign-in did not complete. Retry with Google or continue directly to Studio.';
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string | string[]; error?: string | string[] }>;
}) {
  const params = await searchParams;
  const rawParam = params?.callbackUrl;
  const raw = Array.isArray(rawParam) ? rawParam[0] : rawParam;
  const callbackUrl = safeCallbackPath(raw ?? CANONICAL_STUDIO_PATH);
  const rawErr = params?.error;
  const errorText = authErrorMessage(Array.isArray(rawErr) ? rawErr[0] : rawErr);

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12" style={{ background: 'var(--uvai-bg)' }}>
      <section className="uvai-card w-full max-w-md p-8">
        <p className="uvai-label">UVAI</p>
        <h1 className="font-display mt-4 text-3xl">Sign in to your workspace</h1>
        <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
          Use your Google account to access your studio and saved workflows, or open Studio directly.
        </p>
        {errorText ? (
          <p
            role="alert"
            className="mt-4 rounded-lg border px-3 py-2 text-xs leading-relaxed"
            style={{
              borderColor: 'var(--uvai-warn-border)',
              background: 'var(--uvai-warn-bg)',
              color: 'var(--uvai-warn-ink)',
            }}
          >
            {errorText}
          </p>
        ) : null}
        <div className="mt-8 space-y-3">
          <GoogleSignInButton callbackUrl={callbackUrl} />
          <Link
            href="/studio"
            className="uvai-btn uvai-btn-secondary w-full justify-center"
          >
            Continue directly to Studio →
          </Link>
        </div>
      </section>
    </main>
  );
}
