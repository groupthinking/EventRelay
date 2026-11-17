'use client';

import OneLoopStudio from '@/components/OneLoopStudio';

export default function StudioShell({ showAgentWorkflowUi }: { showAgentWorkflowUi: boolean }) {
  return (
    <div className="min-h-screen bg-[var(--uvai-bg)] text-[var(--uvai-ink)]">
      <OneLoopStudio showAgentWorkflowUi={showAgentWorkflowUi} />
    </div>
  );
}
