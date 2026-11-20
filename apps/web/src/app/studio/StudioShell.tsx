'use client';

import OneLoopStudio, { type StudioLayout } from '@/components/OneLoopStudio';

export default function StudioShell({
  showAgentWorkflowUi,
  layout,
}: {
  showAgentWorkflowUi: boolean;
  layout: StudioLayout;
}) {
  return (
    <div className="min-h-screen bg-[var(--uvai-bg)] text-[var(--uvai-ink)]">
      <OneLoopStudio showAgentWorkflowUi={showAgentWorkflowUi} layout={layout} />
    </div>
  );
}
