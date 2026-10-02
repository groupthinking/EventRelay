'use client';

import OneLoopStudio from '@/components/OneLoopStudio';

export default function StudioShell({ showAgentWorkflowUi }: { showAgentWorkflowUi: boolean }) {
  return (
    <div className="min-h-screen bg-surface-950 text-white">
      <OneLoopStudio showAgentWorkflowUi={showAgentWorkflowUi} />
    </div>
  );
}
