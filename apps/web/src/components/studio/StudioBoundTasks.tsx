'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Video } from '@/store/dashboard-types';
import { hashReviewContent, inspectGroundedSpec, type ReviewInspection } from '@/lib/grounded-build-spec';
import { projectStudioBoundTasks, type StudioBoundTask } from '@/lib/studio-bound-tasks';

type Pack = NonNullable<Video['videoPack']>['pack'];

function timestamp(seconds: number): string {
  const whole = Math.floor(seconds);
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const tail = String(whole % 60).padStart(2, '0');
  return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${tail}` : `${minutes}:${tail}`;
}

/** A source-bound planning view. No action or check is executed by this panel. */
export default function StudioBoundTasks({ pack }: { pack?: Pack }) {
  const inspection = useMemo<ReviewInspection>(() => (
    pack ? inspectGroundedSpec(pack) : { status: 'unavailable', issues: [] }
  ), [pack]);
  const view = useMemo(() => projectStudioBoundTasks(inspection), [inspection]);
  const [digest, setDigest] = useState<{ inspection: ReviewInspection; status: 'valid' | 'mismatch' | 'unavailable' } | null>(null);
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    if (inspection.status !== 'available') return;
    let current = true;
    void hashReviewContent(inspection.canonical).then((hash) => {
      if (current) setDigest({ inspection, status: hash === inspection.contentHash ? 'valid' : 'mismatch' });
    }).catch(() => {
      if (current) setDigest({ inspection, status: 'unavailable' });
    });
    return () => { current = false; };
  }, [inspection]);
  const digestStatus = digest?.inspection === inspection ? digest.status : 'checking';

  function exportTasks() {
    if (view.status !== 'available' || digestStatus !== 'valid' || !view.tasks.length) return;
    let url: string | undefined;
    try {
      const blob = new Blob([JSON.stringify({
        version: 'uvai-bound-tasks/v1',
        kind: 'proposed-work',
        ...view,
      }, null, 2)], { type: 'application/json' });
      url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `uvai-tasks-${view.source.videoId}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setExportError('');
    } catch {
      setExportError('The task file could not be downloaded. Please try again.');
    } finally {
      if (url) {
        const downloadUrl = url;
        // Give the browser time to consume the download before releasing it.
        window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
      }
    }
  }

  if (view.status !== 'available') {
    return (
      <section aria-label="Bound tasks" data-testid="studio-bound-tasks" className="uvai-card p-6">
        <h2 className="text-lg font-medium">Every task starts with its source.</h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-600">
          {view.status === 'invalid'
            ? 'The task bindings could not be validated. Review the source issues before continuing.'
            : view.status === 'source-unavailable'
              ? 'The source is unavailable. A usable Video Pack is needed to bind tasks and checks.'
              : 'Run a YouTube video to inspect source-linked tasks, expected outputs, and proposed checks here.'}
        </p>
        <p className="mt-3 text-xs text-slate-500">No tasks have been executed or independently checked by this view.</p>
        {view.issues.length > 0 && (
          <ul className="mt-4 space-y-2 text-xs text-amber-800" aria-label="Source issues">
            {view.issues.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.message}</li>)}
          </ul>
        )}
      </section>
    );
  }

  if (digestStatus !== 'valid') {
    return (
      <section aria-label="Bound tasks" data-testid="studio-bound-tasks" className="uvai-card p-6">
        <h2 className="text-lg font-medium">Checking task bindings</h2>
        <p role="status" className="mt-3 text-sm text-slate-600">
          {digestStatus === 'checking' ? 'Checking exact source and specification content…'
            : digestStatus === 'mismatch' ? 'The content digest does not match. Task display and export are held.'
              : 'Content verification is unavailable. Task display and export are held.'}
        </p>
      </section>
    );
  }
  const blockingIssues = view.issues.filter((issue) => issue.severity === 'blocking');
  return (
    <section aria-label="Bound tasks" data-testid="studio-bound-tasks" className="space-y-4">
      <header className="space-y-3 px-1">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-medium">From source to next action.</h2>
            <p className="mt-1 text-xs text-slate-500">{view.tasks.length} {view.tasks.length === 1 ? 'task' : 'tasks'} bound to this Video Pack</p>
          </div>
          <button type="button" onClick={exportTasks} disabled={!view.tasks.length}
            className="uvai-btn uvai-btn-secondary !px-3 !py-2 !text-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-700">
            Export tasks
          </button>
        </div>
        <p className="text-xs leading-relaxed text-slate-600">
          Source-linked proposals. Actions have not run, outputs have not been generated, and independent checks have not been performed by this view.
        </p>
        {exportError && <p role="alert" className="text-xs text-red-700">{exportError}</p>}
        <details className="text-xs text-slate-500">
          <summary className="cursor-pointer py-1">Source identity</summary>
          <dl className="mt-2 space-y-2 break-all font-mono text-[11px]">
            <div><dt className="font-semibold">Video Pack</dt><dd>{view.source.packId}</dd></div>
            <div><dt className="font-semibold">Source hash</dt><dd>{view.source.sourceHash}</dd></div>
            <div><dt className="font-semibold">Specification hash</dt><dd>{view.contentHash}</dd></div>
          </dl>
        </details>
        {view.issues.some((issue) => issue.severity === 'warning') && (
          <details className="text-xs text-slate-600">
            <summary className="cursor-pointer py-1">Source limitations</summary>
            <ul className="mt-2 list-disc space-y-1 pl-4">
              {view.issues.filter((issue) => issue.severity === 'warning').map((issue, index) => (
                <li key={`${issue.code}-${index}`}>{issue.message}</li>
              ))}
            </ul>
          </details>
        )}
      </header>
      {blockingIssues.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900">
          <p className="font-semibold">Resolve before execution</p>
          <ul className="mt-2 list-disc space-y-1 pl-4">
            {blockingIssues.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.message}</li>)}
          </ul>
        </div>
      )}
      {view.tasks.length === 0 ? <p className="uvai-card text-sm text-slate-600">This specification contains no tasks.</p> : (
        <ol className="space-y-4" aria-label="Source-linked tasks">
          {view.tasks.map((task, index) => <TaskRow key={task.id} task={task} index={index} />)}
        </ol>
      )}
    </section>
  );
}

function TaskRow({ task, index }: { task: StudioBoundTask; index: number }) {
  return (
    <li className="uvai-card !p-0 overflow-hidden" data-testid="studio-bound-task">
      <div className="border-b border-slate-100 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
          <span className="font-mono text-slate-500">{String(index + 1).padStart(2, '0')} · {task.id}</span>
          <span className="capitalize text-slate-600">{task.classification} · {task.required ? 'Required' : 'Optional'}</span>
        </div>
        <h3 className="mt-2 !font-sans text-sm font-semibold">{task.title}</h3>
        {task.detail && <p className="mt-2 text-xs leading-relaxed text-slate-600">{task.detail}</p>}
      </div>
      <div className="space-y-4 p-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Source</p>
          {task.citations.length === 0 ? <p className="mt-2 text-xs text-amber-800">No direct source citation. This task needs review.</p> : (
            <ul className="mt-2 space-y-3">
              {task.citations.map((citation, index) => (
                <li key={`${citation.kind}-${citation.index}-${index}`}>
                  <a href={citation.sourceUrl} target="_blank" rel="noopener noreferrer"
                    className="font-mono text-xs text-orange-800 underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2">
                    {timestamp(citation.startSeconds)}–{timestamp(citation.endSeconds)} · {citation.kind === 'transcript' ? 'Spoken source' : 'Visual observation'} ↗
                  </a>
                  <blockquote className="mt-2 border-l-2 border-slate-200 pl-3 text-xs leading-relaxed text-slate-600">{citation.quote}</blockquote>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Expected output & checks</p>
          {task.checks.length === 0 ? <p className="mt-2 text-xs text-amber-800">No acceptance criteria supplied. Define a check before execution.</p> : (
            <ul className="mt-2 space-y-3">
              {task.checks.map((check) => (
                <li key={check.id} className="rounded-lg bg-slate-50 p-3 text-xs">
                  <div className="flex justify-between gap-2"><span className="font-mono text-slate-500">{check.id}</span><span className="font-medium text-amber-800">Not run</span></div>
                  <dl className="mt-2 space-y-1 leading-relaxed text-slate-600">
                    <div><dt className="inline font-medium">Given </dt><dd className="inline">{check.given}</dd></div>
                    <div><dt className="inline font-medium">When </dt><dd className="inline">{check.when}</dd></div>
                    <div><dt className="inline font-medium">Then </dt><dd className="inline">{check.then}</dd></div>
                  </dl>
                </li>
              ))}
            </ul>
          )}
        </div>
        <p className="border-t border-slate-100 pt-3 text-[11px] leading-relaxed text-slate-500">Action: not run · Output: not generated · Independent check: unverified</p>
      </div>
    </li>
  );
}
