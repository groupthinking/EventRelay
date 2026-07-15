import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

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
  searchParams: Promise<{ callbackUrl?: string }>;
}) {
  const params = await searchParams;
  const raw = params?.callbackUrl ?? '/dashboard';
  const callback =
    raw.startsWith('/') && !raw.startsWith('//') ? raw : '/dashboard';
  redirect(`/api/auth/signin?callbackUrl=${encodeURIComponent(callback)}`);
}
