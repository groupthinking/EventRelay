import type { Metadata } from 'next';
import Link from 'next/link';
import { safeCallbackPath } from '@/lib/auth-paths';
import GoogleSignInButton from './GoogleSignInButton';

export const metadata: Metadata = {
  title: 'Sign in',
  description: 'Sign in to UVAI with Google to open your dashboard.',
  alternates: { canonical: '/login' },
  robots: { index: false, follow: true },
};

/**
 * Canonical product login page. Middleware gates /dashboard and NextAuth's
 * `pages.signIn` points here, so this must render a real sign-in surface (not
 * redirect back to /api/auth/signin, which would loop). The Google button is a
 * client component that calls signIn('google') with a sanitized same-origin
 * callback.
 */
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string | string[] }>;
}) {
  const params = await searchParams;
  // A repeated ?callbackUrl= yields an array at runtime — take the first value.
  const rawParam = params?.callbackUrl;
  const raw = Array.isArray(rawParam) ? rawParam[0] : rawParam;
  // Reuse the shared sanitizer so /login enforces the same open-redirect
  // protection (backslash + scheme tricks) as the proxy's callback handling.
  const callback = safeCallbackPath(raw ?? '/dashboard');

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-16">
      <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/5 p-8 shadow-xl backdrop-blur">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-white">Sign in to UVAI</h1>
          <p className="mt-2 text-sm text-slate-300">
            Continue with Google to open your dashboard.
          </p>
        </div>
        <GoogleSignInButton callbackUrl={callback} />
        <p className="mt-6 text-center text-xs text-slate-400">
          By continuing you agree to our{' '}
          <Link href="/terms" className="underline hover:text-slate-200">
            Terms
          </Link>{' '}
          and{' '}
          <Link href="/privacy" className="underline hover:text-slate-200">
            Privacy Policy
          </Link>
          .
        </p>
      </div>
    </main>
  );
}
