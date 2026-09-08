import type { Metadata } from 'next';
import { safeCallbackPath } from '@/lib/auth-paths';
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
  const callbackUrl = safeCallbackPath(raw ?? '/');

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-950/80 p-8 shadow-2xl backdrop-blur">
        <p className="text-sm font-semibold tracking-[0.2em] text-teal-300">UVAI</p>
        <h1 className="mt-4 text-3xl font-bold text-white">Sign in to your workspace</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Use your Google account to access your studio and saved workflows.
        </p>
        <div className="mt-8">
          <GoogleSignInButton callbackUrl={callbackUrl} />
        </div>
      </section>
    </main>
  );
}
