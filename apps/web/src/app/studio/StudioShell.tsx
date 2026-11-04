'use client';

import OneLoopStudio from '@/components/OneLoopStudio';

export default function StudioShell({ showAgentWorkflowUi }: { showAgentWorkflowUi: boolean }) {
  return (
    <div className="min-h-screen bg-[#f2f5f9] text-slate-900">
      <OneLoopStudio showAgentWorkflowUi={showAgentWorkflowUi} />
    </div>
  );
}
