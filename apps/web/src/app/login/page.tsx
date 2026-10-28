import type { Metadata } from 'next';
import { CANONICAL_STUDIO_PATH, safeCallbackPath } from '@/lib/auth-paths';
import { GoogleSignInButton } from './GoogleSignInButton';

export const metadata: Metadata = {
  title: 'Sign in',
  description: 'Sign in to UVAI with Google to open your studio.',
  alternates: { canonical: '/login' },
  robots: { index: false, follow: true },
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string | string[] }>;
}) {
  const params = await searchParams;
  const rawParam = params?.callbackUrl;
  const raw = Array.isArray(rawParam) ? rawParam[0] : rawParam;
  const callbackUrl = safeCallbackPath(raw ?? CANONICAL_STUDIO_PATH);

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12" style={{ background: 'var(--uvai-bg)' }}>
      <section className="uvai-card w-full max-w-md p-8">
        <p className="uvai-label">UVAI</p>
        <h1 className="font-display mt-4 text-3xl">Sign in to your workspace</h1>
        <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
          Use your Google account to access your studio and saved workflows.
        </p>
        <div className="mt-8">
          <GoogleSignInButton callbackUrl={callbackUrl} />
        </div>
      </section>
    </main>
  );
}
