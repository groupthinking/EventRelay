import type { Metadata } from 'next';
import RunConsole from '@/components/run/RunConsole';

export const metadata: Metadata = {
  title: 'Delivery run — EventRelay',
  description:
    'Source to shipped product with a gate report: requirements, human approval, build, tests, and a live URL that answered a request.',
};

/**
 * `/studio` is the single run surface. The former 1200-line video workflow
 * component still exists for the analysis-only path; this route is the
 * verified delivery pipeline.
 */
export default function StudioPage() {
  return <RunConsole />;
}
