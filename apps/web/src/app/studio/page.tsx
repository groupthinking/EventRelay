import { Suspense } from 'react';
import type { Metadata } from 'next';
import OneLoopStudio from '@/components/OneLoopStudio';

export const metadata: Metadata = {
  title: 'Studio',
  description: 'UVAI workbench — paste a YouTube URL, inspect the pack, export, and ship.',
  alternates: { canonical: '/studio' },
};

export default function StudioPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-surface-950" />}>
      <OneLoopStudio />
    </Suspense>
  );
}
