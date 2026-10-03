import { Suspense } from 'react';
import type { Metadata } from 'next';
import StudioShell from './StudioShell';
import { agentWorkflowUi } from '@/flags';

export const metadata: Metadata = {
  title: 'Studio',
  description: 'UVAI workbench — paste a YouTube URL, inspect the pack, export, and ship.',
  alternates: { canonical: '/studio' },
};

export default async function StudioPage() {
  const showAgentWorkflowUi = await agentWorkflowUi();

  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f2f5f9]" />}>
      <StudioShell showAgentWorkflowUi={showAgentWorkflowUi} />
    </Suspense>
  );
}
