import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'UVAI',
  description: 'Redirect to UVAI home.',
  alternates: { canonical: '/' },
  robots: { index: false, follow: true },
};

export default function PlaygroundRedirect() {
  redirect('/');
}
