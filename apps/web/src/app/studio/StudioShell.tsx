'use client';

import OneLoopStudio from '@/components/OneLoopStudio';

export default function StudioShell() {
  return (
    <div className="min-h-screen bg-[var(--uvai-bg)] text-[var(--uvai-ink)]">
      <OneLoopStudio />
    </div>
  );
}
