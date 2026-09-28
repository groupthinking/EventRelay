'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import OneLoopStudio from '@/components/OneLoopStudio';

export default function StudioShell({ showAgentWorkflowUi }: { showAgentWorkflowUi: boolean }) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const embed = params.get('view') === 'embed';

  function setView(next: 'pack' | 'embed') {
    const qs = new URLSearchParams(params.toString());
    if (next === 'embed') qs.set('view', 'embed');
    else qs.delete('view');
    const tail = qs.toString();
    router.replace(tail ? `${pathname}?${tail}` : pathname);
  }

  return (
    <div className="min-h-screen bg-surface-950 text-white">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2 text-sm">
        <button
          type="button"
          className={`rounded-full px-3 py-1 ${embed ? 'bg-white/10' : 'bg-teal-500 text-black'}`}
          onClick={() => setView('pack')}
        >
          Pack
        </button>
        <button
          type="button"
          className={`rounded-full px-3 py-1 ${embed ? 'bg-teal-500 text-black' : 'bg-white/10'}`}
          onClick={() => setView('embed')}
        >
          Embed
        </button>
        <span className="text-white/50">Same URL: /studio</span>
      </div>
      {embed ? (
        <iframe
          title="UVAI hybrid workspace"
          src="/studio-pane/index.html"
          className="h-[calc(100vh-48px)] w-full border-0 bg-black"
        />
      ) : (
        <OneLoopStudio showAgentWorkflowUi={showAgentWorkflowUi} />
      )}
    </div>
  );
}
