'use client';

import { useMemo, useState, type ReactNode } from 'react';
import type { Video } from '@/store/dashboard-store';
import { applyTaskEdits, deriveLiveTasks, type LiveTaskEdits } from '@/lib/live-studio-tasks';
import { studioPackExtractedEvents } from '@/lib/studio-pipeline-status';
import {
  LiveChapterRail,
  LiveEvents,
  LiveKeyframes,
  LiveStageList,
  LiveTranscript,
  type LiveStageState,
} from './LiveSourcePanels';
import LiveTaskPanel from './LiveTaskPanel';
import './live-studio.css';

const MOBILE_TABS = [
  { id: 'watch', label: 'Watch' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'more', label: 'Deliverables' },
] as const;
type MobileTab = (typeof MOBILE_TABS)[number]['id'];

export interface LiveStudioWorkspaceProps {
  header: ReactNode;
  player: ReactNode;
  chat: ReactNode;
  deliverables: ReactNode;
  video: Video | undefined;
  /** True while a real extraction or the sample replay is still adding data. */
  live: boolean;
  statusText: string;
  canSeek: boolean;
  onSeek: (seconds: number) => void;
  onSaveTaskEdits: (edits: LiveTaskEdits) => void;
  transcriptEta?: string | null;
  onRetryTranscript?: () => void;
}

export default function LiveStudioWorkspace({
  header,
  player,
  chat,
  deliverables,
  video,
  live,
  statusText,
  canSeek,
  onSeek,
  onSaveTaskEdits,
  transcriptEta = null,
  onRetryTranscript,
}: LiveStudioWorkspaceProps) {
  const [mobileTab, setMobileTab] = useState<MobileTab>('watch');
  const pack = video?.videoPack?.pack;
  const baseTasks = useMemo(() => deriveLiveTasks(pack), [pack]);
  const tasks = useMemo(() => applyTaskEdits(baseTasks, video?.taskEdits), [baseTasks, video?.taskEdits]);
  const segments = pack?.transcript?.segments ?? [];
  const chapters = pack?.chapters ?? [];
  const keyframes = pack?.keyframes ?? [];
  const visualElements = pack?.visual_context?.visual_elements ?? [];
  const extractedEventCount = studioPackExtractedEvents(pack).length;
  const checkCount = tasks.filter((task) => task.check).length;

  const stages = (() => {
    const rows: Array<{ id: string; label: string; present: boolean; detail?: string }> = [
      { id: 'pack', label: 'Pack', present: Boolean(pack), detail: video?.videoPack ? video.videoPack.sourceHash.slice(0, 8) : undefined },
      { id: 'transcript', label: 'Transcript', present: segments.length > 0, detail: segments.length ? String(segments.length) : undefined },
      { id: 'chapters', label: 'Chapters', present: chapters.length > 0, detail: chapters.length ? String(chapters.length) : undefined },
      { id: 'keyframes', label: 'Keyframes', present: keyframes.length > 0, detail: keyframes.length ? String(keyframes.length) : undefined },
      { id: 'events', label: 'Events', present: Boolean(pack), detail: pack ? String(extractedEventCount) : undefined },
      { id: 'tasks', label: 'Tasks', present: tasks.length > 0, detail: tasks.length ? String(tasks.length) : undefined },
      { id: 'checks', label: 'Checks', present: checkCount > 0, detail: checkCount ? String(checkCount) : undefined },
    ];
    const frontier = rows.findIndex((row) => !row.present);
    const failed = !live && video?.status === 'failed';
    return rows.map((row, index): { id: string; label: string; state: LiveStageState; detail?: string } => ({
      id: row.id,
      label: row.label,
      detail: row.detail,
      state: row.present ? 'done' : index === frontier ? (live ? 'active' : failed ? 'failed' : 'idle') : 'idle',
    }));
  })();

  const panelHidden = (tab: MobileTab) => (mobileTab === tab ? undefined : true);
  const settled = !live && stages.every((stage) => stage.state === 'done');
  const sourceMeta = [
    keyframes.length ? `${keyframes.length} frames` : '',
    visualElements.length ? `${visualElements.length} on screen` : '',
  ].filter(Boolean).join(' · ');

  return (
    <main id="main-content" className="live-studio" data-testid="live-studio" data-live={live || undefined}>
      <div className="live-studio__bar">{header}</div>
      <div className="live-studio__status">
        <LiveStageList stages={stages} settled={settled} />
        <p className="live-studio__status-text" role="status" data-testid="live-status">
          {video?.sample ? (
            <span className="uvai-chip live-sample-chip" data-testid="live-sample-label">
              {video.sample.label}
            </span>
          ) : null}
          {statusText}
        </p>
      </div>
      <div className="live-studio__tabs" role="tablist" aria-label="Studio sections">
        {MOBILE_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`live-tab-${tab.id}`}
            aria-selected={mobileTab === tab.id}
            aria-controls={`live-panel-${tab.id}`}
            onClick={() => setMobileTab(tab.id)}
            className="live-studio__tab"
            data-testid={`live-tab-${tab.id}`}
          >
            {tab.label}
            {tab.id === 'tasks' && tasks.length ? <span className="live-studio__tab-count">{tasks.length}</span> : null}
          </button>
        ))}
      </div>
      <div className="live-studio__grid">
        <div className="live-player" data-mobile-hidden={panelHidden('watch')}>{player}</div>
        <div className="live-rail" id="live-panel-watch" data-mobile-hidden={panelHidden('watch')} aria-label="Chapters and transcript">
          <LiveChapterRail chapters={chapters} live={live} canSeek={canSeek} onSeek={onSeek} />
          <LiveTranscript
            segments={segments}
            live={live}
            canSeek={canSeek}
            onSeek={onSeek}
            etaLabel={transcriptEta}
            failureMessage={
              !live && video?.status === 'failed'
                ? video.failure?.message?.trim() || 'Transcript failed.'
                : null
            }
            onRetry={onRetryTranscript}
          />
          <details className="live-extras" data-testid="live-source-extra">
            <summary>Keyframes and events{sourceMeta ? ` · ${sourceMeta}` : ''}</summary>
            <LiveKeyframes keyframes={keyframes} live={live} canSeek={canSeek} onSeek={onSeek} />
            <LiveEvents events={visualElements} live={live} canSeek={canSeek} onSeek={onSeek} />
          </details>
          <details className="live-section live-chat" data-testid="live-chat">
            <summary className="live-section__title">Ask the video</summary>
            <div className="live-chat__body">{chat}</div>
          </details>
        </div>
        <aside className="live-side" id="live-panel-tasks" data-mobile-hidden={panelHidden('tasks')} aria-label="Tasks and dispatch">
          <LiveTaskPanel
            key={video?.id ?? 'none'}
            tasks={tasks}
            baseTasks={baseTasks}
            edits={video?.taskEdits}
            live={live}
            canSeek={canSeek}
            videoId={video?.videoPack?.videoId ?? null}
            jobId={video?.jobId ?? video?.runId ?? video?.videoPack?.packId}
            transcript={video?.transcript}
            onSeek={onSeek}
            onSaveEdits={onSaveTaskEdits}
          />
        </aside>
      </div>
      <details id="live-panel-more" className="live-deliverables" data-testid="live-deliverables" data-mobile-hidden={panelHidden('more')}>
        <summary>Review and build files</summary>
        {deliverables}
      </details>
    </main>
  );
}
