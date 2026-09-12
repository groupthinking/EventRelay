'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, TriangleAlert, XCircle } from 'lucide-react';
import { useYouTubePlayer } from '@/lib/use-youtube-player';
import { extractYouTubeId, parseTimestampToSeconds, parseTranscriptSegments } from '@/lib/timestamp';
import { useDashboardDetail } from '@/hooks/use-dashboard-detail';
import { isThinDashboardAnalysis } from '@/lib/dashboard-analysis';
import type { PipelineMode, Video } from '@/store/dashboard-types';
import VideoCanvasStage, { type TimelineMarker } from './VideoCanvasStage';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  ActionsPanel,
  AgentsPanel,
  InsightsPanel,
  SearchPanel,
  TranscriptPanel,
} from './panels';

function pipelineModeLabel(mode?: PipelineMode): string | null {
  switch (mode) {
    case 'workflow': return 'Durable workflow';
    case 'live': return 'Live backend';
    case 'serverless': return 'Gemini analysis';
    case 'fallback': return 'Direct analysis';
    case 'handoff': return 'Offline handoff';
    default: return null;
  }
}

/**
 * Reserve the two-pane evidence workspace for screens that can keep the video
 * comfortably readable. Laptop and tablet widths use the stacked workspace.
 */
function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1280px)');
    const update = () => setIsDesktop(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isDesktop;
}

type DockKey = 'transcript' | 'summary' | 'actions' | 'agents' | 'search';

export interface DashboardCanvasViewProps {
  video: Video;
  onClose: () => void;
  onExtractEvents?: (videoId: string) => void;
}

export default function DashboardCanvasView({ video, onClose, onExtractEvents }: DashboardCanvasViewProps) {
  const isDesktop = useIsDesktop();
  const [dockTab, setDockTab] = useState<DockKey>('summary');
  const dockTabRefs = useRef<Partial<Record<DockKey, HTMLButtonElement | null>>>({});

  useEffect(() => {
    if (isDesktop) return;
    dockTabRefs.current[dockTab]?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'center',
    });
  }, [dockTab, isDesktop]);

  const {
    searchQuery, setSearchQuery, performSearch, searchResults, searchLoading,
    dispatchToAgents, refreshAgentStatus,
  } = useDashboardDetail();

  const [agentBackend, setAgentBackend] = useState(false);
  useEffect(() => {
    let active = true;
    fetch('/api/agents/dispatch')
      .then((r) => r.json())
      .then((d) => { if (active) setAgentBackend(!!d.available); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const videoId = useMemo(() => extractYouTubeId(video.url), [video.url]);
  const player = useYouTubePlayer(videoId);

  const { segments, hasTimings } = useMemo(
    () => parseTranscriptSegments(video.transcript),
    [video.transcript],
  );

  const markers: TimelineMarker[] = useMemo(() => {
    return (video.events || [])
      .map((e) => {
        const seconds = parseTimestampToSeconds(e.timestamp);
        if (seconds == null) return null;
        return { id: e.id, seconds, label: e.title, type: e.type };
      })
      .filter((m): m is TimelineMarker => m !== null);
  }, [video.events]);

  const agentCount = video.agents?.length ?? 0;
  const thinAnalysis = isThinDashboardAnalysis(video);

  // Shared panel renderers (single instance per active layout).
  const transcriptPanel = (
    <div className="space-y-4">
      <ProvenanceSummary video={video} />
      <div className="border-t border-white/[0.08] pt-4">
        <TranscriptPanel
          video={video}
          segments={segments}
          hasTimings={hasTimings}
          currentTime={player.currentTime}
          isPlaying={player.isPlaying}
          onSeek={player.seekTo}
        />
      </div>
    </div>
  );
  const renderDock = (key: DockKey) => {
    switch (key) {
      case 'transcript': return transcriptPanel;
      case 'summary': return <InsightsPanel video={video} />;
      case 'actions': return <ActionsPanel video={video} onExtractEvents={onExtractEvents} />;
      case 'agents': return <AgentsPanel video={video} agentBackend={agentBackend} onDispatch={dispatchToAgents} onRefresh={refreshAgentStatus} />;
      case 'search': return (
        <SearchPanel
          video={video}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          performSearch={performSearch}
          searchResults={searchResults}
          searchLoading={searchLoading}
          onSeek={player.ready ? player.seekTo : undefined}
        />
      );
    }
  };

  const stage = (
    <VideoCanvasStage
      containerRef={player.containerRef}
      videoId={videoId}
      title={video.title}
      currentTime={player.currentTime}
      duration={player.duration}
      isPlaying={player.isPlaying}
      ready={player.ready}
      failed={player.failed}
      markers={markers}
      onSeek={player.seekTo}
    />
  );

  const dockTabs: { key: DockKey; label: string; count?: number; accent: string }[] = [
    { key: 'transcript', label: 'Transcript', accent: '#6af2de' },
    { key: 'summary', label: 'Findings', accent: '#6af2de' },
    { key: 'actions', label: 'Actions', accent: '#69ccff' },
    { key: 'agents', label: 'Agents', count: agentCount, accent: '#818cf8' },
    { key: 'search', label: 'Search', accent: '#6af2de' },
  ];

  return (
    <div className="evidence-workspace flex flex-1 flex-col overflow-hidden">
      {/* Top bar */}
      <header
        className="evidence-command-bar flex flex-none flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6"
      >
        <button
          onClick={onClose}
          className="flex min-h-11 items-center gap-2 rounded-lg px-2 text-sm font-medium text-white/65 transition-colors hover:bg-white/[0.05] hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to Library
        </button>

        <div className="flex items-center gap-2 flex-wrap">
          <StatusPill video={video} thinAnalysis={thinAnalysis} />
          {pipelineModeLabel(video.pipelineMode) && (
            <span className="hidden text-xs text-white/45 sm:inline">{pipelineModeLabel(video.pipelineMode)}</span>
          )}
          <div className="flex flex-col items-end gap-1">
            <button
              onClick={() => {
                if (!video.transcript || !video.quality?.passed) return;
                const blob = new Blob([video.transcript!], { type: 'text/plain' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = `transcript-${video.id}.txt`;
                a.click();
                URL.revokeObjectURL(a.href);
              }}
              disabled={!video.transcript || !video.quality?.passed}
              title={!video.quality?.passed ? 'Export requires verified captions.' : undefined}
              className="evidence-primary-button min-h-11 rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
            >
              Export
            </button>
            {!video.quality?.passed && (
              <span className="max-w-52 text-right text-xs text-white/55">
                Export requires verified captions.
              </span>
            )}
          </div>
        </div>
      </header>

      {isDesktop ? (
        /* ── Wide desktop: video plus one contextual evidence panel ── */
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <main className="min-w-0 flex-1 overflow-y-auto">
            <div className="mx-auto max-w-5xl p-8">{stage}</div>
          </main>
          <aside className="evidence-context-panel flex w-[480px] max-w-[42vw] flex-none flex-col overflow-hidden">
            <div className="flex-none overflow-x-auto border-b border-white/[0.07]">
              <div className="flex min-w-max">
                {dockTabs.map((t) => (
                  <DockTabButton key={t.key} active={dockTab === t.key} label={t.label} count={t.count} accent={t.accent || '#6af2de'} onClick={() => setDockTab(t.key)} />
                ))}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-6">{renderDock(dockTab)}</div>
          </aside>
        </div>
      ) : (
        /* ── Laptop, tablet, and mobile: stacked with one scroll axis ── */
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <div className="flex-none border-b border-white/[0.07] p-4 sm:p-6">
            <div className="mx-auto w-full max-w-3xl">{stage}</div>
          </div>

          <div className="evidence-context-panel evidence-tab-rail flex flex-none overflow-x-auto border-b border-white/[0.07]">
            {dockTabs.map((t) => (
              <DockTabButton
                key={t.key}
                active={dockTab === t.key}
                label={t.label}
                count={t.count}
                accent={t.accent || '#6af2de'}
                onClick={() => setDockTab(t.key)}
                buttonRef={(node) => { dockTabRefs.current[t.key] = node; }}
              />
            ))}
          </div>

          <div className="p-4 sm:p-6">
            {renderDock(dockTab)}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────── small pieces ─────────────────────────── */

function StatusPill({ video, thinAnalysis }: { video: Video; thinAnalysis: boolean }) {
  const evidenceState = video.quality?.state;
  const partial = evidenceState === 'degraded' || (thinAnalysis && video.status === 'complete');
  const failed = video.status === 'failed' || evidenceState === 'failed' || evidenceState === 'unavailable';
  const color = partial ? '#facc15' : failed ? '#ff716c' : evidenceState === 'verified' ? '#22c55e' : '#6af2de';
  const bg = partial ? 'rgba(250,204,21,0.1)' : failed ? 'rgba(255,113,108,0.1)' : evidenceState === 'verified' ? 'rgba(34,197,94,0.1)' : 'rgba(106,242,222,0.1)';
  const label = video.status === 'processing'
    ? 'PROCESSING'
    : evidenceState === 'verified'
      ? 'CAPTIONS VERIFIED'
      : partial
        ? 'CAPTIONS DEGRADED'
        : failed
          ? 'CAPTIONS UNAVAILABLE'
          : video.status.toUpperCase();
  return (
    <span className="flex items-center gap-2" aria-live="polite">
      <span className="rounded-full px-3 py-1 text-xs font-semibold" style={{ background: bg, color, border: `1px solid ${color}40` }}>
        {label}
      </span>
      {video.status === 'processing' && <span className="text-xs font-mono" style={{ color: '#6af2de' }}>{video.progress}%</span>}
    </span>
  );
}

function ProvenanceSummary({ video }: { video: Video }) {
  const provenance = video.provenance;
  const unavailable = 'Unavailable';
  const acquiredAt = provenance?.acquiredAt
    ? new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(provenance.acquiredAt))
    : unavailable;
  const rows = [
    ['Source', provenance?.sourceHost || unavailable],
    ['Fetched', acquiredAt],
    ['Coverage', provenance?.durationCoverageSeconds != null
      ? `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(provenance.durationCoverageSeconds)} s`
      : unavailable],
  ];
  const technicalRows = [
    ['Acquisition', provenance?.acquisitionMethod || unavailable],
    ['Segments', provenance ? new Intl.NumberFormat().format(provenance.segmentCount) : unavailable],
    ['Timed', provenance ? `${provenance.timedSegmentCount}/${provenance.segmentCount}` : unavailable],
  ];

  return (
    <section aria-labelledby="source-provenance-heading" className="rounded-xl border border-white/[0.1] bg-white/[0.025] p-3">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 id="source-provenance-heading" className="font-heading text-sm font-semibold text-white/85">
          Caption source
        </h3>
        {provenance?.sourceUrl && (
          <a
            href={provenance.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-11 items-center text-xs font-medium text-[#6af2de] underline-offset-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]"
          >
            Open source
          </a>
        )}
      </div>
      <dl className="space-y-2 text-xs">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[88px_minmax(0,1fr)] gap-2">
            <dt className="uppercase tracking-wider text-white/50">{label}</dt>
            <dd className="min-w-0 break-words font-mono text-white/80">{value}</dd>
          </div>
        ))}
      </dl>
      <details className="mt-3 border-t border-white/[0.07] pt-3 text-xs text-white/55">
        <summary className="min-h-11 cursor-pointer py-3 font-medium text-white/65">Technical details</summary>
        <dl className="space-y-2 pb-1">
          {technicalRows.map(([label, value]) => (
            <div key={label} className="grid grid-cols-[88px_minmax(0,1fr)] gap-2">
              <dt className="text-white/45">{label}</dt>
              <dd className="min-w-0 break-words font-mono text-white/70">{value}</dd>
            </div>
          ))}
        </dl>
      </details>
      {video.failure && (
        <Alert variant="destructive" className="mt-3">
          <XCircle aria-hidden="true" />
          <AlertTitle>{video.failure.stage} failed</AlertTitle>
          <AlertDescription>{video.failure.message}</AlertDescription>
        </Alert>
      )}
      {(video.quality?.issues.length ?? 0) > 0 && (
        <Alert variant="warning" className="mt-3">
          <TriangleAlert aria-hidden="true" />
          <AlertTitle>Evidence checks</AlertTitle>
          <AlertDescription>
            <ul className="list-disc space-y-1 pl-4">
              {video.quality!.issues.map((issue) => <li key={issue}>{issue}</li>)}
            </ul>
          </AlertDescription>
        </Alert>
      )}
    </section>
  );
}

function DockTabButton({
  active, label, count, accent, onClick, buttonRef,
}: {
  active: boolean;
  label: string;
  count?: number;
  accent: string;
  onClick: () => void;
  buttonRef?: (node: HTMLButtonElement | null) => void;
}) {
  return (
    <button
      ref={buttonRef}
      onClick={onClick}
      className="relative min-h-11 whitespace-nowrap px-4 py-3 text-xs font-medium transition-colors"
      style={{
        color: active ? accent : 'rgba(248,245,253,0.4)',
        borderBottom: active ? `2px solid ${accent}` : '2px solid transparent',
        background: active ? `${accent}0d` : 'transparent',
        fontWeight: active ? 650 : 500,
      }}
    >
      {label}
      {count != null && count > 0 && (
        <span className="ml-1.5 rounded px-1.5 py-0.5 text-[10px] font-bold align-top" style={{ background: `${accent}26`, color: accent }}>
          {count}
        </span>
      )}
    </button>
  );
}
