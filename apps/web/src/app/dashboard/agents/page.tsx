import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { CANONICAL_STUDIO_PATH } from '@/lib/auth-paths';

export const metadata: Metadata = {
  title: 'Studio',
  description: 'Redirect to the UVAI workbench.',
  alternates: { canonical: '/' },
  robots: { index: false, follow: true },
};

export default function LegacyAgentsRedirect() {
  redirect(CANONICAL_STUDIO_PATH);
}
