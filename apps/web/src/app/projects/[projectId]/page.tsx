import { Suspense } from 'react';
import type { Metadata } from 'next';
import ProjectWorkspace from '@/components/projects/ProjectWorkspace';

export const metadata: Metadata = {
  title: 'Project Workspace',
  description: 'Brief, transcript, and chat for one YouTube Video Pack project.',
  robots: { index: false, follow: false },
};

export default async function ProjectWorkspacePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--uvai-bg)]" />}>
      <ProjectWorkspace projectId={projectId} />
    </Suspense>
  );
}
