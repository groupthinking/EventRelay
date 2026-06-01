import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'App',
  description: 'Redirect to the UVAI dashboard.',
  alternates: { canonical: '/dashboard' },
  robots: { index: false, follow: true },
};

export default function AppRedirect() {
  redirect('/dashboard');
}
