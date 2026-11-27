'use client';

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Copy, Download, FileJson, Play, Sparkles } from 'lucide-react';
import { parseTimestampToSeconds, extractYouTubeId } from '@/lib/timestamp';
import { applyPackStackChecks, compileLinkedSop, type LinkedSop } from '@/lib/linked-sop';
import {
  deployHoldReason,
  pickOfficialTemplate,
  stackCheckStatus,
  stackCheckStatusLabel,
  studioStackCheckView,
} from '@/lib/official-templates';
import { clsx } from 'clsx';
import Nav from '@/components/Nav';
import { StudioAuthNavLink } from '@/components/StudioAuthNavLink';
import { ANALYSIS_STOPPED_MESSAGE, dashboardPersistenceSucceeded, useDashboardStore, type Video } from '@/store/dashboard-store';
import GroundedSpecReview from '@/components/GroundedSpecReview';
import {
  actionsFromStudioRun,
  buildStudioShipPackage,
  downloadScaffoldPackage,
  safeProjectName,
} from '@/lib/action-surface';
import { type VideoToActionsResult } from '@/lib/studio-workflow';
import {
  packBuildLiveFailureDetails,
  packBuildLiveOutcomeMessage,
  resolvePackBuildLiveVideoId,
  studioPackBuildLiveSuccessReceiptForSelection,
  verifyPackBuildLive,
  type PackBuildLiveFailureDetails,
} from '@/lib/pack-build-live-client';
import {
  studioActionCard,
  studioCanExport,
  studioCanRetryTranscript,
  studioEventsEmptyMessage,
  studioExportFilename,
  studioExportProRequiredToast,
  studioExportToastMessage,
  studioInvalidHandoffMessage,
  studioPackCitation,
  studioPackExtractedEvents,
  studioPackFormation,
  studioPackIdentity,
  studioResolveAutoSelectedPackId,
  studioPasteOutcomeMessage,
  studioPlayerOverlay,
  studioPlayerPhase,
  studioPromotePackWorkbench,
  studioRunQuality,
  studioShipCta,
  studioStatusMessage,
  studioTranscriptEtaLabel,
  studioTranscriptStage,
} from '@/lib/studio-pipeline-status';
import { useYouTubePlayer } from '@/lib/use-youtube-player';
import {
  applyStudioQueryAutoStart,
  resetStudioQueryAutoStart,
  resolveStudioHandoff,
  studioQueryFromSearchParams,
} from '@/lib/studio-handoff';
import type { VideoPackArchitecture, VideoPackArtifact, VideoPackStackTool } from '@/lib/video-pack-types';
import StudioIdeShell from '@/components/studio/StudioIdeShell';
import StudioIdeChat from '@/components/studio/StudioIdeChat';
import StudioIdeOutput from '@/components/studio/StudioIdeOutput';
import StudioPackTimeline from '@/components/studio/StudioPackTimeline';
import { studioPackTimelineCanSeek } from '@/lib/studio-pack-timeline';
import {
  registerStudioWebMcpTools,
  type StudioWebMcpPackSnapshot,
} from '@/lib/webmcp-studio-tools';
import LiveStudioWorkspace from '@/components/studio/live/LiveStudioWorkspace';
import { identityPackJson } from '@/lib/emit-video-pack';
import {
  SAMPLE_CAPTURED_AT,
  SAMPLE_LABEL,
  SAMPLE_WATCH_URL,
  loadSamplePack,
  replaySamplePack,
} from '@/lib/sample-pack';

const FIXTURE = 'https://www.youtube.com/watch?v=auJzb1D-fag';

function getYouTubeId(url: string) {
  return extractYouTubeId(url) || '';
}

function safeYouTubeWatchHref(rawId: string): string | null {
  const match = /^[A-Za-z0-9_-]{6,20}$/.exec(rawId);
  if (!match) return null;
  const watchUrl = new URL('https://www.youtube.com/watch');
  watchUrl.searchParams.set('v', match[0]);
  return watchUrl.toString();
}

function formatSavedVideoLabel(video: Video): string {
  const raw = video.title?.trim() ?? '';
  const vid = getYouTubeId(video.videoPack?.sourceUrl || video.url || '');
  const fallback = vid ? `YouTube · ${vid}` : 'Saved video';
  if (
    !raw ||
    /^analyzing:\s*/i.test(raw) ||
    /^analysis\s+(?:blocked|stopped)\b/i.test(raw) ||
    /^https?:\/\//i.test(raw)
  ) {
    return fallback;
  }
  return raw;
}

function countLabel(count: number, singular: string, plural = `${singular}s`): string {
  return `${count.toLocaleString()} ${count === 1 ? singular : plural}`;
}

function PackWorkbench({
  architecture,
  artifacts,
  tools,
  onExport,
  canExport,
}: {
  architecture: VideoPackArchitecture | null;
  artifacts: VideoPackArtifact[];
  tools: VideoPackStackTool[];
  onExport: () => void;
  canExport: boolean;
}) {
  return (
    <section
      data-testid="pack-workbench"
      className="uvai-card p-4 lg:col-span-2"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--uvai-accent-ink)]">
          From this pack
        </h2>
        <button
          type="button"
          onClick={onExport}
          disabled={!canExport}
          className="uvai-btn inline-flex items-center gap-2 disabled:opacity-40"
        >
          <Download className="h-4 w-4" aria-hidden />
          Export pack
        </button>
      </div>
      {architecture ? (
        <div data-testid="pack-architecture" className="mt-4">
          <h3 className="uvai-section-label">Architecture</h3>
          {architecture.summary ? (
            <p className="mt-2 text-sm text-[var(--uvai-ink-soft)]">{architecture.summary}</p>
          ) : null}
          {architecture.stages.length > 0 ? (
            <ol className="mt-2 space-y-1 text-sm text-[var(--uvai-ink-soft)]">
              {architecture.stages.map((stage) => (
                <li key={stage.id}>
                  <span className="font-medium text-[var(--uvai-ink)]">{stage.name}</span>
                  {stage.description ? ` — ${stage.description}` : ''}
                </li>
              ))}
            </ol>
          ) : null}
          {architecture.mermaid ? (
            <pre className="mt-2 overflow-auto rounded-lg border border-[var(--uvai-border-strong)] bg-[var(--uvai-bg)] p-3 font-mono text-[11px] leading-5 text-[var(--uvai-ink)]">
              {architecture.mermaid}
            </pre>
          ) : null}
        </div>
      ) : null}
      {artifacts.length > 0 ? (
        <ul data-testid="pack-artifacts" className="mt-4 space-y-2">
          {artifacts.map((artifact) => (
            <li
              key={artifact.path_hint}
              className="uvai-doc-row"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate font-mono text-[12px] font-semibold text-[var(--uvai-accent-ink)]">{artifact.path_hint}</div>
                <div className="mt-0.5 truncate text-sm text-[var(--uvai-ink-soft)]">{artifact.purpose}</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-[var(--uvai-ink-faint)]">{artifact.interface}</div>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {tools.length > 0 ? (
        <ul data-testid="pack-stack-tools" className="mt-4 space-y-2">
          {tools.map((tool) => (
            <li key={tool.name} className="uvai-doc-row">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--uvai-ink)]">{tool.name}</p>
                {tool.kind ? <p className="text-xs text-[var(--uvai-ink-faint)]">{tool.kind}</p> : null}
                {tool.evidence ? <p className="text-xs text-[var(--uvai-ink-soft)]">{tool.evidence}</p> : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export type StudioLayout = 'live' | 'classic';

export default function OneLoopStudio({ layout = 'classic' }: { layout?: StudioLayout } = {}) {
  const isLive = layout === 'live';
  const searchParams = useSearchParams();
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState('');
  const runAbortRef = useRef<AbortController | null>(null);
  const sampleAbortRef = useRef<AbortController | null>(null);
  const sampleStartedRef = useRef(false);
  const [sampleRunning, setSampleRunning] = useState(false);
  const [workflowActions, setWorkflowActions] = useState<VideoToActionsResult | null>(null);
  const [workflowActionSelectionId, setWorkflowActionSelectionId] = useState<string | null>(null);
  const [buildBusy, setBuildBusy] = useState(false);
  const [packLiveReceiptUrl, setPackLiveReceiptUrl] = useState<string | null>(null);
  const [packLiveReceiptVideoId, setPackLiveReceiptVideoId] = useState<string | null>(null);
  const [packLiveReceiptYoutubeId, setPackLiveReceiptYoutubeId] = useState<string | null>(null);
  const [packLiveReceiptReasonCode, setPackLiveReceiptReasonCode] = useState<string | null>(null);
  const [completedChecks, setCompletedChecks] = useState<string[]>([]);
  const [preferDirectEmbed, setPreferDirectEmbed] = useState(false);
  const [previewFocusEpoch, setPreviewFocusEpoch] = useState(0);
  const [exportToast, setExportToast] = useState<{ tone: 'success' | 'error'; text: string } | null>(
    null,
  );
  const [buildLiveFailure, setBuildLiveFailure] = useState<PackBuildLiveFailureDetails | null>(
    null,
  );
  const autoStartedKey = useRef<string | null>(null);
  const autoSelectedPackRef = useRef(false);
  const skipMessageResetForIdRef = useRef<string | null>(null);

  const processVideo = useDashboardStore((s) => s.processVideo);
  const addVideo = useDashboardStore((s) => s.addVideo);
  const removeVideo = useDashboardStore((s) => s.removeVideo);
  const selectVideo = useDashboardStore((s) => s.selectVideo);
  const updateVideo = useDashboardStore((s) => s.updateVideo);
  const selectedVideoId = useDashboardStore((s) => s.selectedVideoId);
  const videos = useDashboardStore((s) => s.videos);
  const selected = videos.find((v) => v.id === selectedVideoId);
  const scopedWorkflowActions =
    workflowActionSelectionId === selectedVideoId &&
    getYouTubeId(selected?.url || '') === getYouTubeId(workflowActions?.url || '') &&
    (!url.trim() || getYouTubeId(url) === getYouTubeId(selected?.url || ''))
      ? workflowActions
      : null;
  const scopedPackBuildLiveSuccess = studioPackBuildLiveSuccessReceiptForSelection({
    selectedVideoId,
    receiptVideoId: packLiveReceiptVideoId,
    youtubeVideoId: packLiveReceiptYoutubeId,
    liveUrl: packLiveReceiptUrl,
    reasonCode: packLiveReceiptReasonCode,
  });
  const packFormation = useMemo(
    () => studioPackFormation(selected?.videoPack),
    [selected?.videoPack],
  );
  const linkedSop: LinkedSop | null = useMemo(() => {
    const packTools = packFormation.tools;
    if (selected?.insights?.linkedSop) {
      return applyPackStackChecks(selected.insights.linkedSop, packTools);
    }
    if (!selected?.transcript && !(selected?.events?.length) && packTools.length === 0) return null;
    const insightActions = (selected?.insights?.actions || []).flatMap((action) => {
      if (typeof action === 'string') {
        return action.trim() ? [{ title: action.trim() }] : [];
      }
      return action.title?.trim() ? [{ title: action.title, description: action.description, category: action.category }] : [];
    });
    return applyPackStackChecks(
      compileLinkedSop({
        transcript: selected?.transcript,
        events: (selected?.events || []).map((event) => ({
          timestamp: parseTimestampToSeconds(event.timestamp) ?? undefined,
          label: event.title,
          description: event.description,
        })),
        actions: insightActions,
        topics: selected?.insights?.topics,
        packTools,
      }),
      packTools,
    );
  }, [selected, packFormation.tools]);
  const stackChecks = packFormation.checks;

  useEffect(() => {
    setWorkflowActions(null);
    setWorkflowActionSelectionId(null);
    setCompletedChecks([]);
    setBuildLiveFailure(null);
    setPackLiveReceiptUrl(null);
    setPackLiveReceiptVideoId(null);
    setPackLiveReceiptYoutubeId(null);
    setPackLiveReceiptReasonCode(null);
    setExportToast(null);
    setPreferDirectEmbed(false);
    if (skipMessageResetForIdRef.current === selectedVideoId) {
      skipMessageResetForIdRef.current = null;
    } else if (!runAbortRef.current) {
      setMessage('');
    }
  }, [selectedVideoId]);

  useEffect(() => {
    if (!exportToast) return;
    const timer = window.setTimeout(() => setExportToast(null), 4000);
    return () => window.clearTimeout(timer);
  }, [exportToast]);

  const holdReason = deployHoldReason(linkedSop, completedChecks, 'anonymous');
  const officialTemplate = pickOfficialTemplate(linkedSop);
  const stackCheckViews = stackChecks.map((item) => {
    const status = stackCheckStatus(item, completedChecks, 'anonymous');
    return {
      ...studioStackCheckView(item, completedChecks, 'anonymous'),
      status,
      statusLabel: stackCheckStatusLabel(status),
    };
  });

  useEffect(() => {
    useDashboardStore.persist.rehydrate();
  }, []);

  // A stored completed pack drives the header + transcript without requiring a
  // Saved videos combobox click (#2244). Failed or orphaned runs are never
  // auto-selected on load so /studio always starts calm and clean.
  useEffect(() => {
    if (autoSelectedPackRef.current) return;
    if (
      selectedVideoId ||
      studioQueryFromSearchParams(searchParams) ||
      (isLive && searchParams.get('sample') === '1')
    ) {
      autoSelectedPackRef.current = true;
      return;
    }
    const completeVideos = videos.filter((video) => video.status === 'complete');
    const targetId = studioResolveAutoSelectedPackId({
      selectedVideoId,
      videos: completeVideos,
    });
    if (targetId) {
      autoSelectedPackRef.current = true;
      selectVideo(targetId);
    }
  }, [selectedVideoId, videos, searchParams, selectVideo, isLive]);

  const runAnalysis = useCallback(async (raw: string) => {
    const handoff = resolveStudioHandoff(raw);
    if (!handoff) {
      setMessage('Need a valid YouTube URL.');
      return;
    }
    const next = handoff.watchUrl;
    setUrl(next);
    // Cancel any in-flight run and clear prior errors before starting a new one.
    runAbortRef.current?.abort();
    sampleAbortRef.current?.abort();
    const controller = new AbortController();
    runAbortRef.current = controller;
    const priorIds = new Set(useDashboardStore.getState().videos.map((v) => v.id));
    setBusy(true);
    setExportToast(null);
    setBuildLiveFailure(null);
    setPackLiveReceiptUrl(null);
    setPackLiveReceiptVideoId(null);
    setPackLiveReceiptYoutubeId(null);
    setPackLiveReceiptReasonCode(null);
    setWorkflowActions(null);
    setWorkflowActionSelectionId(null);
    selectVideo(null);
    setMessage('Fetching transcript…');
    const tick = window.setInterval(() => {
      if (controller.signal.aborted || runAbortRef.current !== controller) return;
      const matches = useDashboardStore
        .getState()
        .videos.filter(
          (v) =>
            !priorIds.has(v.id) &&
            (v.url === next || v.url.includes(handoff.videoId)),
        );
      if (matches.length === 0) return;
      selectVideo(matches[0].id);
    }, 250);
    const stopTick = () => window.clearInterval(tick);
    controller.signal.addEventListener('abort', stopTick, { once: true });
    try {
      const id = await processVideo(next, { signal: controller.signal });
      if (runAbortRef.current !== controller) return;
      if (controller.signal.aborted) {
        setMessage(ANALYSIS_STOPPED_MESSAGE);
        return;
      }
      skipMessageResetForIdRef.current = id;
      selectVideo(id);
      const video = useDashboardStore.getState().videos.find((v) => v.id === id);
      const ready =
        (video?.transcript?.trim().length ?? 0) >= 40 || (video?.events?.length ?? 0) > 0;
      if (video?.status === 'failed') {
        setMessage(video.failure?.message?.trim() || 'Analysis failed.');
      } else {
        setMessage(
          studioPasteOutcomeMessage({
            hasUsableTranscript: ready,
            packCitation: video?.videoPack ? studioPackCitation(video.videoPack) : null,
          }),
        );
      }
    } catch (err) {
      if (runAbortRef.current !== controller) return;
      if (controller.signal.aborted) {
        setMessage(ANALYSIS_STOPPED_MESSAGE);
      } else {
        setMessage(err instanceof Error ? err.message : 'Analysis failed.');
      }
    } finally {
      window.clearInterval(tick);
      controller.signal.removeEventListener('abort', stopTick);
      if (runAbortRef.current === controller) {
        runAbortRef.current = null;
        setBusy(false);
      }
    }
  }, [processVideo, selectVideo]);

  const cancelAnalysis = useCallback(() => {
    runAbortRef.current?.abort();
    runAbortRef.current = null;
    sampleAbortRef.current?.abort();
    setBusy(false);
    setMessage(ANALYSIS_STOPPED_MESSAGE);
  }, []);

  const runSample = useCallback(async () => {
    runAbortRef.current?.abort();
    runAbortRef.current = null;
    setBusy(false);
    sampleAbortRef.current?.abort();
    const controller = new AbortController();
    sampleAbortRef.current = controller;
    for (const video of useDashboardStore.getState().videos) {
      if (video.sample) removeVideo(video.id);
    }
    const citation = loadSamplePack();
    const id = crypto.randomUUID();
    addVideo({
      id,
      title: `Sample · ${citation.videoId}`,
      url: SAMPLE_WATCH_URL,
      status: 'processing',
      progress: 0,
      sample: { label: SAMPLE_LABEL, capturedAt: SAMPLE_CAPTURED_AT },
    });
    skipMessageResetForIdRef.current = id;
    selectVideo(id);
    setUrl(SAMPLE_WATCH_URL);
    setExportToast(null);
    setBuildLiveFailure(null);
    setSampleRunning(true);
    setMessage('Replaying the cached sample pack stage by stage…');
    try {
      await replaySamplePack({
        citation,
        signal: controller.signal,
        apply: (patch) => updateVideo(id, patch),
      });
      if (sampleAbortRef.current === controller) {
        setMessage('Sample ready. Select tasks to dispatch, or paste your own URL for a fresh extraction.');
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        console.error('[studio] sample replay failed', error);
      }
      updateVideo(id, {
        status: 'failed',
        failure: {
          stage: 'analysis',
          message: controller.signal.aborted ? ANALYSIS_STOPPED_MESSAGE : 'Sample replay failed.',
          retryable: true,
          failedAt: new Date().toISOString(),
        },
      });
    } finally {
      if (sampleAbortRef.current === controller) {
        sampleAbortRef.current = null;
        setSampleRunning(false);
      }
    }
  }, [addVideo, removeVideo, selectVideo, updateVideo]);

  useEffect(() => {
    if (!isLive || sampleStartedRef.current || searchParams.get('sample') !== '1') return;
    sampleStartedRef.current = true;
    // Next tick: the mount-time rehydrate effect must settle first, or it would
    // normalize the freshly persisted in-progress sample record to failed.
    window.setTimeout(() => void runSample(), 0);
  }, [isLive, searchParams, runSample]);

  const copyPackJson = async () => {
    if (!selected?.videoPack) return;
    try {
      await navigator.clipboard.writeText(identityPackJson(selected.videoPack));
      setExportToast({
        tone: 'success',
        text: `Copied Video Pack JSON · ${selected.videoPack.packId} · sha ${selected.videoPack.sourceHash.slice(0, 12)}`,
      });
    } catch (error) {
      console.warn('[studio] clipboard write failed', error);
      setExportToast({ tone: 'error', text: 'Clipboard is unavailable here. Use Download JSON instead.' });
    }
  };

  const downloadPackJson = () => {
    if (!selected?.videoPack) return;
    const blob = new Blob([identityPackJson(selected.videoPack)], { type: 'application/json' });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = `${selected.videoPack.videoId}.video-pack.json`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(href), 0);
    setExportToast({ tone: 'success', text: `Downloaded ${anchor.download}` });
  };

  useEffect(() => {
    applyStudioQueryAutoStart({
      query: studioQueryFromSearchParams(searchParams),
      startedKey: autoStartedKey,
      start: (watchUrl) => {
        void runAnalysis(watchUrl);
      },
      onResolved: (watchUrl) => {
        setUrl(watchUrl);
      },
      onInvalidQuery: (raw) => {
        setUrl(raw);
        setMessage(studioInvalidHandoffMessage(raw));
      },
    });
    // One-shot kick from ?video= so Home paste starts the live pack path.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    // Release the module-level Strict Mode guard when Studio truly unmounts so
    // re-entering /studio?video= with the same id (re-paste, or retry after a
    // failed run) auto-starts again. Deferred so React's synchronous Strict
    // Mode unmount/remount still sees the guard and does not double-start.
    return () => {
      window.setTimeout(() => resetStudioQueryAutoStart(), 0);
    };
  }, []);

  const analyze = (event?: FormEvent) => {
    event?.preventDefault();
    void runAnalysis(url);
  };

  const transcriptWorking = busy;

  useEffect(() => {
    if (!transcriptWorking) {
      setElapsed(0);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 250);
    return () => window.clearInterval(timer);
  }, [transcriptWorking]);

  const videoId = useMemo(() => getYouTubeId(url || selected?.url || ''), [url, selected?.url]);
  const watchHref = useMemo(() => safeYouTubeWatchHref(videoId), [videoId]);
  // Destructure at the hook call so render reads booleans + a callback ref,
  // not properties of an object that also carries refs (react-hooks/refs).
  const {
    containerRef,
    ready: playerReady,
    failed: playerFailed,
    direct: playerDirect,
    currentTime: playerCurrentTime,
    duration: playerDuration,
    seekTo,
  } = useYouTubePlayer(videoId, { direct: preferDirectEmbed });

  useEffect(() => {
    setPreferDirectEmbed(false);
  }, [videoId]);

  const playerPhase = studioPlayerPhase({
    videoId: videoId || null,
    loaded: playerReady,
    failed: playerFailed,
  });
  const playerOverlay = studioPlayerOverlay(playerPhase);
  // The hook owns the nocookie iframe and its seek ref. The shell only hides
  // the cover; it does not swap in a second iframe.
  const showDirectEmbed = preferDirectEmbed || playerDirect;
  const showErrorCover = !showDirectEmbed && playerPhase === 'error';
  const embedErrorText = studioPlayerOverlay('error');
  const eventCount = studioPackExtractedEvents(selected?.videoPack?.pack).length;
  const promotePack = studioPromotePackWorkbench({
    eventCount,
    hasArchitecture: Boolean(packFormation.architecture),
    artifactCount: packFormation.artifacts.length,
    toolCount: packFormation.tools.length,
  });
  const eventsEmptyMessage = studioEventsEmptyMessage({
    busy: transcriptWorking,
    hasCompletedRun: Boolean(selected && selected.status !== 'processing'),
    eventCount,
    hasTranscript: Boolean(selected?.transcript?.trim()),
    hasArchitecture: Boolean(packFormation.architecture),
    artifactCount: packFormation.artifacts.length,
    toolCount: packFormation.tools.length,
  });
  const hasPayload = studioCanExport({
    transcript: selected?.transcript,
    eventCount,
    hasArchitecture: Boolean(packFormation.architecture),
    artifactCount: packFormation.artifacts.length,
    toolCount: packFormation.tools.length,
    hasLinkedSopSteps: Boolean(linkedSop?.steps.length),
    hasProjectScaffold: Boolean(selected?.insights?.project_scaffold),
  });
  const shipCta = studioShipCta({ canExport: hasPayload, holdReason });
  const runState = busy ? 'working' : selected ? 'ready' : 'idle';
  const quality = studioRunQuality(
    selected?.jobId ? { ok: true, status: 200, jobId: selected.jobId } : null,
    false,
    Boolean(videoId || selected),
    { transcript: selected?.transcript, eventCount },
  );
  const shellPack = selected?.videoPack?.pack;
  const canSeekActiveVideo = studioPackTimelineCanSeek({
    videoId,
    packVideoId: shellPack?.video_id,
  });
  const handleAnalyzeUrl = useCallback(
    (submittedUrl: string) => {
      void runAnalysis(submittedUrl);
    },
    [runAnalysis],
  );

  const exportPkg = async () => {
    const projectLabel = selected ? formatSavedVideoLabel(selected) : 'uvai-project';
    const filename = studioExportFilename(
      safeProjectName(projectLabel),
    );
    const insightActions = (selected?.insights?.actions || []).flatMap((action) => {
      if (typeof action === 'string') {
        return action.trim() ? [{ title: action.trim() }] : [];
      }
      return action.title?.trim() ? [action] : [];
    });
    const actions = actionsFromStudioRun({
      insightActions,
      events: selected?.events,
      workflowActions: scopedWorkflowActions?.actions,
    });
    if (
      actions.length === 0 &&
      !selected?.insights?.project_scaffold &&
      !linkedSop?.steps.length &&
      !packFormation.architecture &&
      packFormation.artifacts.length === 0 &&
      packFormation.tools.length === 0
    ) {
      const toast = studioExportToastMessage({ ok: false, kind: 'empty', filename });
      setExportToast(toast);
      return;
    }
    try {
      const pkg = buildStudioShipPackage({
        projectName: projectLabel,
        actions,
        projectScaffold: selected?.insights?.project_scaffold,
        linkedSop: linkedSop || undefined,
        videoPack: selected?.videoPack
          ? {
              videoId: selected.videoPack.videoId,
              sourceUrl: selected.videoPack.sourceUrl,
              sourceHash: selected.videoPack.sourceHash,
              packId: selected.videoPack.packId,
              visual: selected.videoPack.pack,
              requirements: selected.videoPack.pack.requirements,
            }
          : null,
        transcript: selected?.transcript
          ? { full_text: selected.transcript }
          : selected?.videoPack?.pack.transcript,
        sopSteps: linkedSop?.steps,
      });
      const result = await downloadScaffoldPackage(pkg);
      if (!result.ok) {
        if (result.status === 402 || result.upgradeRequired) {
          setExportToast(studioExportProRequiredToast());
          return;
        }
        const toast = studioExportToastMessage({
          ok: false,
          error: result.error,
        });
        setExportToast(toast);
        return;
      }
      const filename = result.filename || studioExportFilename(pkg.projectName);
      const kind =
        packFormation.architecture || packFormation.artifacts.length > 0
          ? 'pack'
          : linkedSop
            ? 'sop'
            : 'scaffold';
      const toast = officialTemplate
        ? {
            tone: 'success' as const,
            text: `Exported ${officialTemplate.clone} plus SOP and DEPLOY.md. ${filename}`,
          }
        : studioExportToastMessage({ ok: true, kind, filename });
      setExportToast(toast);
    } catch (err) {
      const toast = studioExportToastMessage({
        ok: false,
        error: err instanceof Error ? err.message : 'Export failed.',
        filename,
      });
      setExportToast(toast);
    }
  };

  const runBuildLiveRecovery = (action: PackBuildLiveFailureDetails['actions'][number]) => {
    const watch = (selected?.url || url).trim();
    if (action.id === 'open_hosted') {
      window.open(action.href, '_blank', 'noopener,noreferrer');
      return;
    }
    if (action.id === 'rerun_analysis' && watch) {
      void runAnalysis(watch);
      return;
    }
    if (action.id === 'scroll_pack') {
      document.querySelector('[data-testid="video-pack"]')?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const buildLive = async () => {
    const watchUrl = (selected?.url || url).trim();
    const packVideoId = resolvePackBuildLiveVideoId({
      packVideoId: selected?.videoPack?.videoId,
      watchUrl,
    });
    const origin = typeof window !== 'undefined' ? window.location.origin : undefined;
    if (!packVideoId) {
      const failure = packBuildLiveFailureDetails({
        storedPackMissing: true,
        videoId: getYouTubeId(watchUrl) || undefined,
        origin,
      });
      setBuildLiveFailure(failure);
      setMessage(failure.message);
      return;
    }
    if (!selected?.videoPack) {
      const failure = packBuildLiveFailureDetails({
        reasonCode: 'HOSTED_PACK_NOT_FOUND',
        videoId: packVideoId,
        origin,
        storedPackMissing: true,
      });
      setBuildLiveFailure(failure);
      setMessage(failure.message);
      return;
    }
    setBuildBusy(true);
    const attemptRecordId = selectedVideoId;
    setBuildLiveFailure(null);
    try {
      const built = await verifyPackBuildLive({
        videoId: packVideoId,
        sourceHash: selected.videoPack.sourceHash,
        origin,
      });
      if (useDashboardStore.getState().selectedVideoId !== attemptRecordId) return;
      if (built.ok) {
        setPackLiveReceiptUrl(built.liveUrl);
        setPackLiveReceiptVideoId(attemptRecordId);
        setPackLiveReceiptYoutubeId(packVideoId);
        setPackLiveReceiptReasonCode(built.reasonCode);
        setPreviewFocusEpoch((epoch) => epoch + 1);
        setMessage(packBuildLiveOutcomeMessage(built));
        return;
      }
      const failure = packBuildLiveFailureDetails({
        reasonCode: built.reasonCode,
        message: built.message,
        videoId: packVideoId,
        origin,
      });
      setBuildLiveFailure(failure);
      setMessage(failure.message);
    } catch (err) {
      if (useDashboardStore.getState().selectedVideoId !== attemptRecordId) return;
      const failure = packBuildLiveFailureDetails({
        message: err instanceof Error ? err.message : 'Build live failed.',
        videoId: packVideoId,
        origin,
      });
      setBuildLiveFailure(failure);
      setMessage(failure.message);
    } finally {
      setBuildBusy(false);
    }
  };

  const packIdentity = studioPackIdentity(selected?.videoPack);
  const transcriptStage = studioTranscriptStage({
    busy: transcriptWorking,
    elapsedSeconds: elapsed,
    progress: selected?.progress,
    hasPack: Boolean(selected?.videoPack),
    hasPackIdentity: Boolean(packIdentity),
    hasTranscript: Boolean(selected?.transcript?.trim()),
    hasFailed: !transcriptWorking && selected?.status === 'failed',
  });
  const showTranscriptRetry = studioCanRetryTranscript({
    busy: transcriptWorking,
    hasFailed: selected?.status === 'failed',
    retryable: selected?.failure?.retryable !== false,
    elapsedSeconds: elapsed,
  });
  const statusText = sampleRunning
    ? `Replaying sample · ${selected?.progress ?? 0}% — ${message}`
    : transcriptWorking
    ? `Working · ${elapsed}s — ${transcriptStage.label}. ${studioTranscriptEtaLabel(elapsed)}`
    : message || studioStatusMessage(quality, runState, 'Analysis', false);

  const transcriptWordCount = selected?.transcript
    ? selected.transcript.trim().split(/\s+/).length
    : 0;

  const webMcpSnapshot: StudioWebMcpPackSnapshot = useMemo(
    () => ({
      videoId: selected?.videoPack?.videoId ?? (videoId || null),
      packId: selected?.videoPack?.packId ?? null,
      sourceUrl: selected?.videoPack?.sourceUrl ?? (url.trim() || null),
      sourceHash: selected?.videoPack?.sourceHash ?? null,
      busy: transcriptWorking,
      transcriptWordCount,
      chapterCount: shellPack?.chapters?.length ?? 0,
      actionCount: selected?.videoPack?.pack.action_items?.length ?? 0,
      toolCount: packFormation.tools.length,
      artifactCount: packFormation.artifacts.length,
    }),
    [
      selected?.videoPack,
      shellPack?.chapters?.length,
      videoId,
      url,
      transcriptWorking,
      transcriptWordCount,
      packFormation.tools.length,
      packFormation.artifacts.length,
    ],
  );
  const webMcpSnapshotRef = useRef<StudioWebMcpPackSnapshot>(webMcpSnapshot);
  const webMcpRunRef = useRef(runAnalysis);

  useEffect(() => {
    webMcpSnapshotRef.current = webMcpSnapshot;
  }, [webMcpSnapshot]);

  useEffect(() => {
    webMcpRunRef.current = runAnalysis;
  });

  useEffect(() => {
    const controller = new AbortController();
    void registerStudioWebMcpTools(
      {
        getSnapshot: () => webMcpSnapshotRef.current,
        onLoadUrl: (watchUrl, runImmediately) => {
          setUrl(watchUrl);
          if (runImmediately) {
            void webMcpRunRef.current(watchUrl);
          }
        },
      },
      { signal: controller.signal },
    ).catch((error: unknown) => {
      console.error('WebMCP tool registration failed:', error);
    });
    return () => {
      controller.abort();
    };
  }, []);

  const toolbarNode = (
    <>
      <form
        onSubmit={analyze}
        toolname="run_studio_video_analysis"
        tooldescription="Extract transcript, numbered chapters, events, and runnable deliverables from a YouTube video URL in UVAI Studio"
        className="flex min-w-0 flex-1 items-center gap-2"
        data-testid="studio-ide-url-form"
      >
        <label className="sr-only" htmlFor="youtube-url">
          YouTube URL
        </label>
        <input
          id="youtube-url"
          name="youtubeUrl"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (!busy && message) setMessage('');
          }}
          placeholder="Paste a YouTube link…"
          autoComplete="off"
          className="uvai-input min-w-0 flex-1 font-mono disabled:opacity-40"
        />
        {busy || sampleRunning ? (
          <button
            type="button"
            onClick={cancelAnalysis}
            data-testid="studio-ide-cancel"
            className="uvai-btn uvai-btn-danger shrink-0 !font-semibold"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            data-testid="studio-ide-run"
            className={clsx('uvai-btn shrink-0', !hasPayload && 'uvai-btn-primary')}
          >
            Analyze
          </button>
        )}
      </form>
      {videos.some((video) => video.videoPack) ? (
        <div className="flex min-w-0 items-center gap-1.5" data-testid="studio-ide-packs">
          <select
            id="stored-pack"
            value={selected?.videoPack ? selected.id : ''}
            disabled={busy}
            onChange={(event) => selectVideo(event.target.value || null)}
            aria-label="Saved videos"
            className="uvai-input min-w-0 max-w-48 truncate !py-1.5 !text-xs disabled:opacity-40"
          >
            <option value="">Saved videos</option>
            {videos.filter((video) => video.videoPack).map((video) => (
              <option key={video.id} value={video.id}>
                {formatSavedVideoLabel(video)}
              </option>
            ))}
          </select>
        </div>
      ) : null}
      <div className="flex items-center gap-1.5 sm:border-l sm:border-[var(--uvai-border-strong)] sm:pl-2" role="toolbar" aria-label="Pack actions">
        <button
          type="button"
          onClick={() => void exportPkg()}
          disabled={!shipCta.enabled}
          data-testid="studio-ide-ship"
          title={shipCta.hint}
          className={clsx(
            'uvai-btn inline-flex shrink-0 items-center gap-1.5 disabled:opacity-40',
            shipCta.enabled && hasPayload && 'uvai-btn-primary',
          )}
        >
          <Download className="h-4 w-4" aria-hidden />
          {shipCta.label}
        </button>
        {isLive ? (
          <>
            <button
              type="button"
              onClick={() => void copyPackJson()}
              disabled={!selected?.videoPack}
              data-testid="live-copy-pack"
              aria-label="Copy Video Pack JSON"
              title="Copy the hashed Video Pack JSON"
              className="uvai-btn inline-flex shrink-0 items-center gap-1.5 !px-3 disabled:opacity-40"
            >
              <Copy className="h-4 w-4" aria-hidden />
            </button>
            <button
              type="button"
              onClick={downloadPackJson}
              disabled={!selected?.videoPack}
              data-testid="live-download-pack"
              aria-label="Download Video Pack JSON"
              title="Download the hashed Video Pack JSON"
              className="uvai-btn inline-flex shrink-0 items-center gap-1.5 !px-3 disabled:opacity-40"
            >
              <FileJson className="h-4 w-4" aria-hidden />
            </button>
            {selected?.videoPack ? null : (
              <button
                type="button"
                onClick={() => void runSample()}
                disabled={busy}
                data-testid="live-try-sample"
                className="uvai-btn inline-flex shrink-0 items-center gap-1.5 !px-3 disabled:opacity-40"
              >
                <Sparkles className="h-4 w-4" aria-hidden />
                Try a sample
              </button>
            )}
          </>
        ) : null}
      </div>
      {isLive ? (
        <h1 className="sr-only">Paste a YouTube URL to build a live Video Pack</h1>
      ) : (
        <p className="w-full min-w-0 font-mono text-[11px] leading-snug text-[var(--uvai-ink-faint)]" role="status" data-testid="studio-ide-status">
          {statusText}
        </p>
      )}
      {showTranscriptRetry && !transcriptWorking && selected?.status === 'failed' ? (
        <div className="flex w-full flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--uvai-danger-border)] bg-[var(--uvai-danger-bg)] px-3 py-2 text-xs text-[var(--uvai-danger-ink)]">
          <span className="min-w-0 flex-1 truncate">
            {selected?.failure?.message || 'Extraction stopped before finishing.'}
          </span>
          <button
            type="button"
            data-testid="studio-transcript-retry"
            onClick={() => void runAnalysis(url || selected?.url || '')}
            className="uvai-btn shrink-0 !border-[var(--uvai-danger-border)] !bg-[var(--uvai-surface)] !px-3 !py-1 !text-xs font-medium !text-[var(--uvai-danger-ink)] hover:!opacity-90"
          >
            Retry transcript
          </button>
        </div>
      ) : showTranscriptRetry && transcriptWorking ? (
        <div className="flex w-full flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface-warm)] px-3 py-1.5 text-xs text-[var(--uvai-ink-soft)]">
          <span className="min-w-0 flex-1 truncate">
            Still extracting — this video is taking longer than usual.
          </span>
          <button
            type="button"
            data-testid="studio-transcript-retry"
            onClick={() => void runAnalysis(url || selected?.url || '')}
            className="uvai-btn shrink-0 !px-3 !py-1 !text-xs font-medium"
          >
            Retry transcript
          </button>
        </div>
      ) : null}
    </>
  );

  const playerNode = (
    <div className="studio-video-wrap relative overflow-hidden rounded-lg border border-[var(--uvai-border-strong)] bg-black shadow-sm">
      {videoId ? (
        <div
          key={videoId}
          className="relative mx-auto aspect-video w-full overflow-hidden bg-neutral-950"
        >
              {!showDirectEmbed && !playerReady && !playerFailed ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`https://i.ytimg.com/vi/${encodeURIComponent(videoId)}/hqdefault.jpg`}
                  alt={selected ? `${formatSavedVideoLabel(selected)} preview` : 'YouTube video preview'}
                  data-testid="studio-player-poster"
                  width={480}
                  height={360}
                  fetchPriority="high"
                  decoding="async"
                  onError={(event) => {
                    event.currentTarget.style.display = 'none';
                  }}
                  className="absolute inset-0 h-full w-full object-cover"
                />
              ) : null}
              <div
                ref={containerRef}
                className="relative z-10 h-full w-full"
                data-testid="studio-player"
                title="YouTube source"
              />
              {!showDirectEmbed && playerOverlay && playerPhase === 'loading' && !showErrorCover ? (
                <button
                  type="button"
                  data-testid="studio-player-overlay"
                  onClick={() => setPreferDirectEmbed(true)}
                  aria-label="Play video"
                  className="group absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-black/30 px-4 text-center transition-colors hover:bg-black/20"
                >
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#146ef5] text-white shadow-md transition-transform group-hover:scale-105">
                    <Play className="ml-0.5 h-5 w-5 fill-current" aria-hidden />
                  </span>
                  <span className="rounded-full bg-black/65 px-2.5 py-0.5 text-[11px] font-medium text-white backdrop-blur-sm">
                    {playerOverlay}
                  </span>
                </button>
              ) : showErrorCover ? (
                <div
                  data-testid="studio-player-overlay"
                  className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-neutral-950 px-4 text-center"
                >
                  <p className="max-w-sm text-sm font-medium text-white">{embedErrorText}</p>
                  <div className="flex flex-wrap items-center justify-center gap-2">
                    <button
                      type="button"
                      data-testid="studio-player-retry"
                      onClick={() => setPreferDirectEmbed(true)}
                      className="uvai-btn !bg-white !px-3 !py-1 !text-xs !text-neutral-950"
                    >
                      Retry player
                    </button>
                    {watchHref ? (
                      <a
                        href={watchHref}
                        target="_blank"
                        rel="noreferrer"
                        data-testid="studio-player-open-youtube"
                        className="uvai-btn !px-3 !py-1 !text-xs text-white"
                      >
                        Open on YouTube
                      </a>
                    ) : null}
                  </div>
                </div>
              ) : null}
        </div>
      ) : (
        <div className="flex aspect-video w-full flex-col items-center justify-center gap-3 bg-[var(--uvai-surface)] px-6 text-center text-sm text-[var(--uvai-ink-faint)]">
          <p>Paste a YouTube link above or in chat to load the video.</p>
          <button
            type="button"
            data-testid="studio-try-sample"
            onClick={isLive ? () => void runSample() : () => setUrl(FIXTURE)}
            disabled={busy}
            className="uvai-chip !px-3 !py-1 !text-xs font-medium text-[var(--uvai-ink)] hover:border-[var(--uvai-accent)] disabled:opacity-40"
          >
            Try sample
          </button>
        </div>
      )}
    </div>
  );

  const timelineNode = shellPack ? (
    <StudioPackTimeline
      pack={shellPack}
      canSeek={canSeekActiveVideo}
      onSeek={canSeekActiveVideo ? seekTo : undefined}
      // Selection-scoped: never scale/playhead from a mismatched URL's player.
      currentTime={canSeekActiveVideo ? playerCurrentTime : 0}
      playerDuration={canSeekActiveVideo ? playerDuration : null}
    />
  ) : null;

  const videoPaneNode = (
    <div className="studio-source-stack flex min-w-0 flex-col gap-3">
      {playerNode}
      {timelineNode}
      <div className="studio-steps-bar flex min-w-0 max-w-full flex-wrap items-center justify-between gap-2 px-3 py-1.5">
        <ol
          data-testid="studio-extraction-steps"
          aria-label="Extraction progress"
          className="studio-steps min-w-0 max-w-full flex-1 flex-wrap"
        >
          {(
            [
              { id: 'pack', label: 'Pack' },
              { id: 'captions', label: 'Captions' },
              { id: 'transcript', label: 'Transcript' },
              { id: 'events', label: 'Events' },
              { id: 'ready', label: 'Ready' },
            ] as const
          ).map((step, idx) => {
            const activeIdx =
              transcriptStage.id === 'ready'
                ? 4
                : transcriptStage.id === 'events'
                  ? 3
                  : transcriptStage.id === 'transcript'
                    ? 2
                    : transcriptStage.id === 'captions'
                      ? 1
                      : 0;
            const isDone =
              !transcriptWorking &&
              selected?.status !== 'failed' &&
              Boolean(selected?.videoPack || selected?.transcript?.trim());
            const isFailed = !transcriptWorking && selected?.status === 'failed';
            const stepState = isDone
              ? 'done'
              : isFailed
                ? idx < activeIdx
                  ? 'done'
                  : idx === activeIdx
                    ? 'failed'
                    : 'idle'
                : transcriptWorking
                  ? idx < activeIdx
                    ? 'done'
                    : idx === activeIdx
                      ? 'active'
                      : 'idle'
                  : 'idle';
            return (
              <li key={step.id} data-state={stepState} data-step={step.id}>
                {step.label}
              </li>
            );
          })}
        </ol>
        {watchHref ? (
          <a
            href={watchHref}
            target="_blank"
            rel="noreferrer"
            aria-label="Trouble with this video? Watch it directly on YouTube"
            title="Trouble with this video? Watch it directly on YouTube"
            data-testid="studio-watch-on-youtube"
            className="shrink-0 text-[11px] font-medium text-[var(--uvai-ink-soft)] underline-offset-2 hover:text-[var(--uvai-ink)] hover:underline"
          >
            YouTube ↗
          </a>
        ) : null}
      </div>
      <div className="flex min-w-0 flex-col gap-3">
        {selected?.videoPack ? (
          <div className="uvai-card studio-pack-card min-w-0 max-w-full overflow-hidden p-3">
            <div className="studio-pack-card__head flex min-w-0 flex-wrap items-center justify-between gap-2">
              <p className="uvai-section-label">Extracted pack</p>
              <span className="min-w-0 max-w-full truncate font-mono text-[11px] font-semibold text-[var(--uvai-accent-ink)]">
                {selected.videoPack.sourceHash.slice(0, 12)}…
              </span>
            </div>
            <div className="studio-pack-card__chips mt-2 flex min-w-0 max-w-full flex-wrap items-center gap-1.5 text-[11px] text-[var(--uvai-ink-soft)]">
              {selected.videoPack.pack.action_items?.length ? (
                <span className="max-w-full truncate rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-medium">
                  {countLabel(selected.videoPack.pack.action_items.length, 'action')}
                </span>
              ) : null}
              {selected.videoPack.pack.stack?.tools?.length ? (
                <span className="max-w-full truncate rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-medium">
                  {countLabel(selected.videoPack.pack.stack.tools.length, 'tool')}
                </span>
              ) : null}
              {selected.videoPack.pack.code_snippets?.length ? (
                <span className="max-w-full truncate rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-medium">
                  {countLabel(selected.videoPack.pack.code_snippets.length, 'code file')}
                </span>
              ) : null}
              {transcriptWordCount > 0 ? (
                <span className="max-w-full truncate rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-medium">
                  {countLabel(transcriptWordCount, 'word')}
                </span>
              ) : null}
              {selected.status === 'complete' && !transcriptWorking ? (
                <span className="max-w-full truncate rounded-full border border-[#1E9A80]/45 bg-[#1E9A80]/15 px-2 py-0.5 font-semibold text-[#1E9A80]">
                  Ready
                </span>
              ) : transcriptWorking ? (
                <span className="max-w-full truncate rounded-full border border-[var(--uvai-accent)]/45 bg-[var(--uvai-accent-soft)] px-2 py-0.5 font-semibold text-[var(--uvai-accent-ink)]">
                  Working
                </span>
              ) : selected.status === 'failed' ? (
                <span className="max-w-full truncate rounded-full border border-[var(--uvai-danger-border)] bg-[var(--uvai-danger-bg)] px-2 py-0.5 font-semibold text-[var(--uvai-danger-ink)]">
                  Needs retry
                </span>
              ) : null}
            </div>
            <p className="studio-pack-card__url mt-2 min-w-0 max-w-full truncate text-xs text-[var(--uvai-ink-faint)]">
              {selected.videoPack.sourceUrl}
            </p>
            {selected.videoPack.pack.chapters?.length ? (
              <div className="studio-pack-card__jump mt-3 min-w-0 max-w-full border-t border-[var(--uvai-border)] pt-2.5">
                <p className="uvai-section-label mb-2">Quick jump</p>
                <ol className="flex min-w-0 flex-col gap-1.5">
                  {selected.videoPack.pack.chapters.slice(0, 4).map((chapter, index) => {
                    const canSeekPack = videoId === selected.videoPack?.pack.video_id;
                    return (
                      <li key={`${chapter.topic}-${index}`} className="min-w-0 max-w-full">
                        <button
                          type="button"
                          data-testid={`studio-quick-jump-${index}`}
                          disabled={!canSeekPack}
                          title={
                            canSeekPack
                              ? `Seek to ${chapter.start}s`
                              : 'Run analysis or switch URL back to this pack to seek.'
                          }
                          onClick={() => {
                            if (canSeekPack) seekTo(chapter.start);
                          }}
                          className="flex w-full min-w-0 max-w-full items-center justify-between gap-2 rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-bg)] px-2.5 py-1.5 text-left text-xs transition-colors hover:border-[var(--uvai-border-strong)] hover:bg-[var(--uvai-surface-warm)] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <span className="flex min-w-0 flex-1 items-center gap-2">
                            <span className="shrink-0 font-mono text-[11px] font-semibold text-[var(--uvai-accent-ink)]">
                              {String(index + 1).padStart(2, '0')}
                            </span>
                            <span className="min-w-0 truncate text-[var(--uvai-ink)]">{chapter.topic}</span>
                          </span>
                          <span className="shrink-0 font-mono text-[11px] text-[var(--uvai-ink-faint)]">
                            {chapter.start}s
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ol>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="uvai-card studio-outline-card p-4">
            <p className="uvai-section-label">Workspace outline</p>
            <p className="mt-2 text-sm font-medium text-[var(--uvai-ink)]">
              Video-in, deliverables-out workflow
            </p>
            <ul className="mt-3 space-y-2 text-xs text-[var(--uvai-ink-soft)]">
              <li className="flex items-center gap-2">
                <span className="font-mono text-[11px] text-[var(--uvai-accent-ink)]">01</span>
                <span>Bound tasks linked to spoken timestamps</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="font-mono text-[11px] text-[var(--uvai-accent-ink)]">02</span>
                <span>Numbered chapters, named tools & code files</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="font-mono text-[11px] text-[var(--uvai-accent-ink)]">03</span>
                <span>Interactive chat, Live Preview & Pack Export</span>
              </li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );

  const chatNode = (
    <StudioIdeChat
      videoId={selected?.videoPack?.videoId ?? (videoId || null)}
      packId={selected?.videoPack?.packId ?? null}
      disabled={transcriptWorking}
      isWorking={transcriptWorking}
      statusText={statusText}
      activeStage={transcriptStage.label}
      videoTitle={selected ? formatSavedVideoLabel(selected) : null}
      onSubmitUrl={handleAnalyzeUrl}
      onSeek={canSeekActiveVideo ? seekTo : undefined}
      artifactStreamInputs={{
        busy: transcriptWorking,
        elapsedSeconds: elapsed,
        progress: selected?.progress,
        hasPack: Boolean(selected?.videoPack),
        hasPackIdentity: Boolean(packIdentity),
        hasTranscript: Boolean(selected?.transcript?.trim()),
        hasFailed: !transcriptWorking && selected?.status === 'failed',
        formation: {
          architecture: packFormation.architecture,
          artifacts: packFormation.artifacts,
          tools: packFormation.tools,
        },
      }}
    />
  );

  const outputNode = (
    <StudioIdeOutput
      video={selected}
      eventsEmptyMessage={eventsEmptyMessage}
      stackChecks={stackCheckViews}
      previewVideoId={
        scopedPackBuildLiveSuccess?.youtubeVideoId ??
        selected?.videoPack?.videoId ??
        videoId ??
        null
      }
      previewReady={Boolean(scopedPackBuildLiveSuccess)}
      transcriptEta={transcriptWorking ? studioTranscriptEtaLabel(elapsed) : null}
      showTranscriptRetry={showTranscriptRetry}
      onRetryTranscript={() => void runAnalysis(url || selected?.url || '')}
      onBuildLive={() => void buildLive()}
      buildBusy={buildBusy}
      focusPreviewSignal={previewFocusEpoch}
      initialSection="tasks"
      onSeek={canSeekActiveVideo ? seekTo : undefined}
      reviewActions={(scopedWorkflowActions?.actions ?? []).map((action) => {
        const card = studioActionCard(action);
        return {
          tool: action.tool,
          input: action.input,
          status: action.status,
          result: action.result ?? card.detail,
        };
      })}
      packWorkbench={
        promotePack ? (
          <PackWorkbench
            architecture={packFormation.architecture}
            artifacts={packFormation.artifacts}
            tools={packFormation.tools}
            onExport={() => void exportPkg()}
            canExport={hasPayload}
          />
        ) : undefined
      }
      specReview={
        selected?.videoPack?.pack ? (
          <GroundedSpecReview
            key={selected.id}
            videoId={selected.id}
            pack={selected.videoPack.pack}
            acknowledgment={selected.specReviewAcknowledgment}
            persistenceAvailable={dashboardPersistenceSucceeded()}
            onSeek={videoId === selected.videoPack.pack.video_id ? seekTo : undefined}
            onAcknowledge={(value) => {
              if (useDashboardStore.getState().selectedVideoId !== selected.id) return false;
              updateVideo(selected.id, { specReviewAcknowledgment: value });
              return dashboardPersistenceSucceeded();
            }}
          />
        ) : undefined
      }
    />
  );

  return (
    <div className={clsx('template-studio flex min-h-screen flex-col text-[var(--uvai-ink)]', isLive && 'template-studio--document')}>
      <Nav variant="rail" defaultCollapsed rightSlot={<StudioAuthNavLink />} />

      {isLive ? (
        <LiveStudioWorkspace
          header={toolbarNode}
          player={playerNode}
          chat={chatNode}
          deliverables={outputNode}
          video={selected}
          live={busy || sampleRunning}
          statusText={statusText}
          canSeek={canSeekActiveVideo}
          onSeek={seekTo}
          transcriptEta={transcriptWorking ? studioTranscriptEtaLabel(elapsed) : null}
          onRetryTranscript={() => void runAnalysis(url || selected?.url || '')}
          onSaveTaskEdits={(taskEdits) => {
            if (selected) updateVideo(selected.id, { taskEdits });
          }}
        />
      ) : (
        <StudioIdeShell
          toolbar={toolbarNode}
          videoPane={videoPaneNode}
          chatPane={chatNode}
          outputPane={outputNode}
        />
      )}


      {exportToast ? (
        <div
          data-testid="studio-export-toast"
          role={exportToast.tone === 'error' ? 'alert' : 'status'}
          className={clsx(
            'studio-export-toast',
            exportToast.tone === 'success' ? 'studio-export-toast--success' : 'studio-export-toast--error',
          )}
        >
          {exportToast.text}
        </div>
      ) : null}

      {scopedPackBuildLiveSuccess ? (
        <div
          data-testid="studio-pack-build-live-result"
          role="status"
          className="border-t border-[#146ef5]/35 bg-[var(--uvai-accent-soft)]"
        >
          <div className="mx-auto flex max-w-[1360px] flex-wrap items-center justify-between gap-2 px-4 py-1.5 sm:px-6">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span
                data-testid="studio-pack-build-live-state"
                className="inline-flex rounded-full border border-[#146ef5]/45 bg-[var(--uvai-accent-soft)] px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--uvai-accent-ink)]"
              >
                Ready
              </span>
              <span className="font-medium text-[var(--uvai-ink)]">
                {scopedPackBuildLiveSuccess.jobTitle} · {scopedPackBuildLiveSuccess.subtitle}
              </span>
              <span className="text-[var(--uvai-ink-soft)]">
                YouTube video id{' '}
                <span
                  data-testid="studio-pack-build-live-video-id"
                  className="font-mono text-[var(--uvai-accent-ink)]"
                >
                  {scopedPackBuildLiveSuccess.youtubeVideoId}
                </span>
              </span>
              <span
                data-testid="studio-pack-build-live-reason-code"
                className="font-mono text-[11px] text-[var(--uvai-ink-faint)]"
              >
                {scopedPackBuildLiveSuccess.reasonCode}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                data-testid="studio-pack-build-live-artifact-link"
                href={scopedPackBuildLiveSuccess.artifactPath}
                className="uvai-btn uvai-btn-primary inline-flex w-fit items-center justify-center !py-1 !text-xs"
              >
                Open {scopedPackBuildLiveSuccess.artifactPath}
              </Link>
              <Link
                data-testid="studio-pack-build-live-pro-cta"
                href="/pricing"
                className="uvai-btn inline-flex w-fit items-center justify-center !py-1 !text-xs"
              >
                Unlock Workflow Pro
              </Link>
            </div>
          </div>
        </div>
      ) : null}

      {buildLiveFailure ? (
        <div
          data-testid="studio-build-live-failure"
          role="alert"
          className="border-t border-[var(--uvai-danger-border)] bg-[var(--uvai-danger-bg)]"
        >
          <div className="mx-auto flex max-w-[1360px] flex-wrap items-center justify-between gap-2 px-4 py-1.5 sm:px-6">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-medium text-[var(--uvai-danger-ink)]">{buildLiveFailure.title}</span>
              <span className="text-[var(--uvai-ink-soft)]">{buildLiveFailure.message}</span>
              {buildLiveFailure.reasonCode ? (
                <span className="font-mono text-[11px] text-[var(--uvai-ink-faint)]">
                  {buildLiveFailure.reasonCode}
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              {buildLiveFailure.actions.map((action) =>
                action.id === 'open_hosted' ? (
                  <a
                    key={action.id}
                    href={action.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="studio-build-live-recovery-open-hosted"
                    className="uvai-btn !py-1 !text-xs"
                  >
                    {action.label}
                  </a>
                ) : (
                  <button
                    key={action.id}
                    type="button"
                    data-testid={`studio-build-live-recovery-${action.id}`}
                    onClick={() => runBuildLiveRecovery(action)}
                    className="uvai-btn !py-1 !text-xs"
                  >
                    {action.label}
                  </button>
                ),
              )}
            </div>
          </div>
        </div>
      ) : null}

    </div>
  );
}
