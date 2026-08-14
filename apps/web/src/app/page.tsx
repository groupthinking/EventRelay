import { Suspense } from 'react';
import OneLoopStudio from '@/components/OneLoopStudio';

export default function HomePage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-surface-950" />}>
      <OneLoopStudio />
    </Suspense>
  );
}
