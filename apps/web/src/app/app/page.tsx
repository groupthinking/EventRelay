import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { CANONICAL_STUDIO_PATH } from '@/lib/auth-paths';

export const metadata: Metadata = {
  title: 'App',
  description: 'Redirect to the UVAI workbench.',
  alternates: { canonical: '/' },
  robots: { index: false, follow: true },
};

export default function AppRedirect() {
  redirect(CANONICAL_STUDIO_PATH);
}
