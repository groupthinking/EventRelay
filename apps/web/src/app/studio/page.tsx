import { Suspense } from 'react';
import type { Metadata } from 'next';
import StudioShell from './StudioShell';

export const metadata: Metadata = {
  title: 'Studio',
  description: 'UVAI workbench — paste a YouTube URL, inspect the pack, export, and ship.',
  alternates: { canonical: '/studio' },
};

export default function StudioPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--uvai-bg)]" />}>
      <StudioShell />
    </Suspense>
  );
}
