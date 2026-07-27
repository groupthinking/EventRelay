import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { safeCallbackPath } from '@/lib/auth-paths';

export const metadata: Metadata = {
  title: 'Sign in',
  description: 'Sign in to UVAI with Google to open your dashboard.',
  alternates: { canonical: '/login' },
  robots: { index: false, follow: true },
};

/**
 * Canonical product login entry. Middleware already gates /dashboard; this route
 * funnels marketing "Sign in" links into the NextAuth Google flow with a safe
 * same-origin callback.
 */
export default async function LoginRedirect({
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
  redirect(`/api/auth/signin?callbackUrl=${encodeURIComponent(callback)}`);
}
