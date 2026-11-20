'use client';

import OneLoopStudio, { type StudioLayout } from '@/components/OneLoopStudio';

export default function StudioShell({ layout }: { layout: StudioLayout }) {
  return (
    <div className="min-h-screen bg-[var(--uvai-bg)] text-[var(--uvai-ink)]">
      <OneLoopStudio layout={layout} />
    </div>
  );
}
