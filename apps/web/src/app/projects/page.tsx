import type { Metadata } from 'next';
import ProjectsLibrary from '@/components/projects/ProjectsLibrary';

export const metadata: Metadata = {
  title: 'Projects',
  description: 'Manage your canonical YouTube Video Pack projects in UVAI.',
  alternates: { canonical: '/projects' },
};

export default function ProjectsPage() {
  return <ProjectsLibrary />;
}
