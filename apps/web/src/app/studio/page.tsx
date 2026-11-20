import { Suspense } from 'react';
import type { Metadata } from 'next';
import StudioShell from './StudioShell';
import { agentWorkflowUi, liveStudio } from '@/flags';

export const metadata: Metadata = {
  title: 'Studio',
  description: 'UVAI workbench — paste a YouTube URL, inspect the pack, export, and ship.',
  alternates: { canonical: '/studio' },
};

export default async function StudioPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [showAgentWorkflowUi, liveStudioEnabled, params] = await Promise.all([
    agentWorkflowUi(),
    liveStudio(),
    searchParams,
  ]);
  const layout = liveStudioEnabled && params.shell !== 'classic' ? 'live' : 'classic';

  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--uvai-bg)]" />}>
      <StudioShell showAgentWorkflowUi={showAgentWorkflowUi} layout={layout} />
    </Suspense>
  );
}
