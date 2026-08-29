import { Suspense } from 'react';
import OneLoopStudio from '@/components/OneLoopStudio';

export default function StudioPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-surface-950" />}>
      <OneLoopStudio />
    </Suspense>
  );
}
