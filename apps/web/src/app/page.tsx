import { Suspense } from 'react';
import OneLoopStudio from '@/components/OneLoopStudio';

export default function HomePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#0b0c10] text-white/60">
          Loading studio…
        </div>
      }
    >
      <OneLoopStudio />
    </Suspense>
  );
}
