import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'UVAI',
  description: 'Redirect to the UVAI workbench.',
  alternates: { canonical: '/studio' },
  robots: { index: false, follow: true },
};

export default function FeaturesRedirect() {
  redirect('/studio');
}
