'use client';

import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ChevronLeft, ChevronRight, TriangleAlert, XCircle } from 'lucide-react';
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
 * Match the evidence workspace's three-rail desktop composition from 900px.
 * This keeps the selected 990px design target intact while preserving the
 * stacked mobile workspace below that width.
 */
function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 900px)');
    const update = () => setIsDesktop(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isDesktop;
}

type DockKey = 'summary' | 'actions' | 'agents' | 'search';
type TabKey = 'transcript' | DockKey;

export interface DashboardCanvasViewProps {
  video: Video;
  onClose: () => void;
  onExtractEvents?: (videoId: string) => void;
}

export default function DashboardCanvasView({ video, onClose, onExtractEvents }: DashboardCanvasViewProps) {
  const isDesktop = useIsDesktop();
  const [dockTab, setDockTab] = useState<DockKey>('summary');
  const [mobileTab, setMobileTab] = useState<TabKey>('transcript');
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);

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

  const eventCount = video.events?.length ?? 0;
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
    { key: 'summary', label: 'Summary', accent: '#6af2de' },
    { key: 'actions', label: 'Actions', count: eventCount, accent: '#69ccff' },
    { key: 'agents', label: 'Agents', count: agentCount, accent: '#818cf8' },
    { key: 'search', label: 'Search', accent: '#6af2de' },
  ];
  const mobileTabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'transcript', label: 'Transcript' },
    { key: 'summary', label: 'Summary' },
    { key: 'actions', label: 'Actions', count: eventCount },
    { key: 'agents', label: 'Agents', count: agentCount },
    { key: 'search', label: 'Search' },
  ];

  return (
    <div className="flex flex-1 flex-col overflow-hidden" style={{ background: '#0e0e13' }}>
      {/* Top bar */}
      <header
        className="flex-none flex items-center justify-between gap-3 px-4 py-3 flex-wrap"
        style={{ background: 'rgba(25, 25, 31, 0.9)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}
      >
        <button
          onClick={onClose}
          className="flex items-center gap-2 text-sm transition-colors hover:text-white min-h-[44px]"
          style={{ color: 'rgba(248,245,253,0.5)', fontFamily: 'var(--font-heading)', letterSpacing: '0.05em', fontSize: '12px', textTransform: 'uppercase' }}
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to Library
        </button>

        <div className="flex items-center gap-2 flex-wrap">
          <StatusPill video={video} thinAnalysis={thinAnalysis} />
          {pipelineModeLabel(video.pipelineMode) && (
            <span
              className="text-[10px] font-bold uppercase tracking-widest px-3 py-1"
              style={{ background: 'rgba(106,242,222,0.06)', border: '1px solid rgba(106,242,222,0.15)', color: 'rgba(106,242,222,0.85)' }}
            >
              {pipelineModeLabel(video.pipelineMode)}
            </span>
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
              title={!video.quality?.passed ? 'Export requires verified source evidence.' : undefined}
              className="px-4 py-2 font-heading font-bold text-[11px] tracking-wider uppercase transition-[background-color,color,opacity] min-h-[44px] disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]"
              style={{ background: 'rgba(16, 183, 165, 0.9)', color: '#002b26' }}
            >
              Export
            </button>
            {!video.quality?.passed && (
              <span className="max-w-52 text-right text-[10px] text-white/55">
                Export requires verified evidence.
              </span>
            )}
          </div>
        </div>
      </header>

      {isDesktop ? (
        /* ── Desktop: center stage + docked rails ── */
        <div className="flex flex-1 overflow-hidden">
          {/* Left transcript rail */}
          {leftOpen ? (
            <aside
              className="flex-none w-[340px] flex flex-col overflow-hidden"
              style={{ borderRight: '1px solid rgba(255,255,255,0.05)', background: '#0b0b0f' }}
            >
              <RailHeader title="Source & Transcript" onCollapse={() => setLeftOpen(false)} side="left" />
              <div className="flex-1 overflow-y-auto p-3">{transcriptPanel}</div>
            </aside>
          ) : (
            <RailReopen label="Source & Transcript" onClick={() => setLeftOpen(true)} side="left" />
          )}

          {/* Center stage */}
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-4xl p-6">{stage}</div>
          </main>

          {/* Right dock */}
          {rightOpen ? (
            <aside
              className="flex-none w-[380px] flex flex-col overflow-hidden"
              style={{ borderLeft: '1px solid rgba(255,255,255,0.05)', background: '#131318' }}
            >
              <div className="flex-none flex items-center" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex-1 flex overflow-x-auto">
                  {dockTabs.map((t) => (
                    <DockTabButton key={t.key} active={dockTab === t.key} label={t.label} count={t.count} accent={t.accent} onClick={() => setDockTab(t.key)} />
                  ))}
                </div>
                <button
                  onClick={() => setRightOpen(false)}
                  aria-label="Collapse panel"
                  className="flex-none px-3 h-full text-lg transition-colors hover:text-white"
                  style={{ color: 'rgba(248,245,253,0.4)' }}
                >
                  <ChevronRight className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-5">{renderDock(dockTab)}</div>
            </aside>
          ) : (
            <RailReopen label="Panels" onClick={() => setRightOpen(true)} side="right" />
          )}
        </div>
      ) : (
        /* ── Mobile / tablet: stacked with tab switcher ── */
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-none p-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{stage}</div>

          <div className="flex-none flex overflow-x-auto" style={{ background: 'rgba(25,25,31,0.9)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            {mobileTabs.map((t) => (
              <DockTabButton key={t.key} active={mobileTab === t.key} label={t.label} count={t.count} accent="#6af2de" onClick={() => setMobileTab(t.key)} />
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {mobileTab === 'transcript' ? transcriptPanel : renderDock(mobileTab)}
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
      ? 'EVIDENCE VERIFIED'
      : partial
        ? 'EVIDENCE DEGRADED'
        : failed
          ? 'EVIDENCE UNAVAILABLE'
          : video.status.toUpperCase();
  return (
    <span className="flex items-center gap-2" aria-live="polite">
      <span className="text-[10px] font-bold uppercase tracking-widest px-3 py-1" style={{ background: bg, color, borderLeft: `2px solid ${color}` }}>
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
    ['Acquisition', provenance?.acquisitionMethod || unavailable],
    ['Fetched', acquiredAt],
    ['Segments', provenance ? new Intl.NumberFormat().format(provenance.segmentCount) : unavailable],
    ['Timed', provenance ? `${provenance.timedSegmentCount}/${provenance.segmentCount}` : unavailable],
    ['Coverage', provenance?.durationCoverageSeconds != null
      ? `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(provenance.durationCoverageSeconds)} s`
      : unavailable],
  ];

  return (
    <section aria-labelledby="source-provenance-heading" className="rounded-xl border border-white/[0.1] bg-white/[0.025] p-3">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 id="source-provenance-heading" className="font-heading text-[11px] font-bold uppercase tracking-[0.16em] text-white/85">
          Source Provenance
        </h3>
        {provenance?.sourceUrl && (
          <a
            href={provenance.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="min-h-[44px] inline-flex items-center text-[10px] font-bold uppercase tracking-wider text-[#6af2de] underline-offset-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]"
          >
            Inspect Raw
          </a>
        )}
      </div>
      <dl className="space-y-2 text-[11px]">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[88px_minmax(0,1fr)] gap-2">
            <dt className="uppercase tracking-wider text-white/50">{label}</dt>
            <dd className="min-w-0 break-words font-mono text-white/80">{value}</dd>
          </div>
        ))}
      </dl>
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
  active, label, count, accent, onClick,
}: { active: boolean; label: string; count?: number; accent: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="relative px-4 py-4 font-heading text-[11px] tracking-[0.15em] uppercase transition-colors whitespace-nowrap min-h-[44px]"
      style={{
        color: active ? accent : 'rgba(248,245,253,0.4)',
        borderBottom: active ? `2px solid ${accent}` : '2px solid transparent',
        background: active ? `${accent}0d` : 'transparent',
        fontWeight: active ? 700 : 500,
      }}
    >
      {label}
      {count != null && count > 0 && (
        <span className="ml-1.5 text-[9px] font-bold px-1.5 py-0.5 rounded-sm align-top" style={{ background: `${accent}26`, color: accent }}>
          {count}
        </span>
      )}
    </button>
  );
}

function RailHeader({ title, onCollapse, side }: { title: string; onCollapse: () => void; side: 'left' | 'right' }) {
  return (
    <div className="flex-none flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(25,25,31,0.9)' }}>
      <span className="font-heading text-[11px] tracking-[0.2em] uppercase font-bold" style={{ color: '#f8f5fd' }}>{title}</span>
      <button onClick={onCollapse} aria-label={`Collapse ${title}`} className="text-lg transition-colors hover:text-white" style={{ color: 'rgba(248,245,253,0.4)' }}>
        {side === 'left'
          ? <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          : <ChevronRight className="h-4 w-4" aria-hidden="true" />}
      </button>
    </div>
  );
}

function RailReopen({ label, onClick, side }: { label: string; onClick: () => void; side: 'left' | 'right' }) {
  return (
    <button
      onClick={onClick}
      aria-label={`Expand ${label}`}
      className="flex-none w-10 flex items-center justify-center transition-colors hover:text-white"
      style={{
        color: 'rgba(248,245,253,0.5)',
        background: '#0b0b0f',
        [side === 'left' ? 'borderRight' : 'borderLeft']: '1px solid rgba(255,255,255,0.05)',
      }}
    >
      <span className="[writing-mode:vertical-rl] rotate-180 font-heading text-[11px] tracking-[0.2em] uppercase py-4">{label}</span>
    </button>
  );
}
