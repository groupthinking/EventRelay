'use client';

import { useMemo, useState } from 'react';
import StepRunner, { type StepRunnerPlayer } from '@/components/studio/StepRunner';
import {
  RUNBOOK_MARKDOWN_FILENAME,
  renderRunbookMarkdown,
  type Runbook,
  type RunbookProgress,
  type RunbookStep,
} from '@/lib/runbook-steps';

type RunbookView = 'runner' | 'markdown';

export interface StudioRunbookPaneProps {
  runbook: Runbook;
  player: StepRunnerPlayer | null;
  progress: RunbookProgress | null | undefined;
  onProgressChange: (progress: RunbookProgress) => void;
  onActiveStepChange?: (step: RunbookStep | null, index: number) => void;
  onTroubleshoot?: (step: RunbookStep) => void;
}

/**
 * Deliverables → Runbook. Two modes over the same compiled runbook:
 * - Step-by-Step Runner (default): one action at a time, synchronized to the player.
 * - Full Runbook Markdown: the RUNBOOK.md reference, copyable/downloadable for VS Code / Cursor.
 */
export default function StudioRunbookPane({
  runbook,
  player,
  progress,
  onProgressChange,
  onActiveStepChange,
  onTroubleshoot,
}: StudioRunbookPaneProps) {
  const [view, setView] = useState<RunbookView>('runner');
  const [copied, setCopied] = useState(false);
  const markdown = useMemo(() => renderRunbookMarkdown(runbook, progress ?? null), [runbook, progress]);
  const downloadHref = useMemo(
    () => `data:text/markdown;charset=utf-8,${encodeURIComponent(markdown)}`,
    [markdown],
  );
  const empty = runbook.steps.length === 0 && runbook.prerequisites.length === 0;

  if (empty) {
    return (
      <div data-testid="studio-runbook-empty" className="uvai-card p-8 text-center">
        <p className="text-sm font-medium text-slate-600">No runbook steps on this pack yet.</p>
        <p className="mt-1 text-xs text-slate-400">
          The pack has no requirements, action items, or SOP steps to walk through. Re-run the video to
          extract them; nothing is invented here.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="studio-runbook-pane" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div role="tablist" aria-label="Runbook view" className="inline-flex rounded-lg bg-slate-100 p-0.5">
          <button
            type="button"
            role="tab"
            aria-selected={view === 'runner'}
            data-testid="studio-runbook-view-runner"
            onClick={() => setView('runner')}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              view === 'runner' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Step-by-Step Runner
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === 'markdown'}
            data-testid="studio-runbook-view-markdown"
            onClick={() => setView('markdown')}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              view === 'markdown' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Full Runbook Markdown
          </button>
        </div>
        <p className="font-mono text-[11px] text-slate-400">
          {runbook.coverage.anchored} / {runbook.coverage.total} steps anchored to video evidence
        </p>
      </div>

      {view === 'runner' ? (
        <StepRunner
          runbook={runbook}
          player={player}
          progress={progress}
          onProgressChange={onProgressChange}
          onActiveStepChange={onActiveStepChange}
          onTroubleshoot={onTroubleshoot}
        />
      ) : (
        <section aria-label="Full runbook markdown" className="uvai-card flex flex-col gap-2 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="uvai-section-label">{RUNBOOK_MARKDOWN_FILENAME}</p>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                data-testid="studio-runbook-copy"
                className="uvai-btn !px-2.5 !py-1 !text-xs"
                onClick={() => {
                  void navigator.clipboard?.writeText(markdown).then(
                    () => {
                      setCopied(true);
                      window.setTimeout(() => setCopied(false), 1500);
                    },
                    () => undefined,
                  );
                }}
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
              <a
                data-testid="studio-runbook-download"
                href={downloadHref}
                download={RUNBOOK_MARKDOWN_FILENAME}
                className="uvai-btn !px-2.5 !py-1 !text-xs"
              >
                Download
              </a>
            </div>
          </div>
          <pre
            data-testid="studio-runbook-markdown"
            className="max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 font-mono text-[11px] leading-5 text-slate-700"
          >
            {markdown}
          </pre>
          <p className="text-[11px] text-slate-400">
            Reference mode. Paste into VS Code / Cursor or keep it with your docs; Export also ships this
            file as {RUNBOOK_MARKDOWN_FILENAME}.
          </p>
        </section>
      )}
    </div>
  );
}
