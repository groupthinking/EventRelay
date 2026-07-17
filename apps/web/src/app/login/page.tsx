import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'Sign in',
  description:
    'UVAI is currently open for use without an account — you go straight to the dashboard.',
  alternates: { canonical: '/dashboard' },
  robots: { index: false, follow: true },
};

export default function LoginRedirect() {
  redirect('/dashboard');
}
