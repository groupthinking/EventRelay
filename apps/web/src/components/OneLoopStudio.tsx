'use client';

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Download, GitPullRequest, Hammer, Play, Rocket } from 'lucide-react';
import { formatSeconds, parseTimestampToSeconds, extractYouTubeId } from '@/lib/timestamp';
import { applyPackStackChecks, compileLinkedSop, type LinkedSop } from '@/lib/linked-sop';
import {
  deployHoldReason,
  pickOfficialTemplate,
  stackCheckStatus,
  stackCheckStatusLabel,
} from '@/lib/official-templates';
import { clsx } from 'clsx';
import Nav from '@/components/Nav';
import { StudioAuthNavLink } from '@/components/StudioAuthNavLink';
import { dashboardPersistenceSucceeded, useDashboardStore } from '@/store/dashboard-store';
import GroundedSpecReview from '@/components/GroundedSpecReview';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field';
import {
  actionsFromStudioRun,
  buildStudioShipPackage,
  downloadScaffoldPackage,
  safeProjectName,
} from '@/lib/action-surface';
import {
  pollStudioDeploy,
  pollVideoToActions,
  probeStudioDeployLiveUrl,
  startStudioDeploy,
  startVideoToActions,
  studioDeployPollResidual,
  type VideoToActionsResult,
} from '@/lib/studio-workflow';
import {
  packBuildLiveFailureDetails,
  packBuildLiveOutcomeMessage,
  resolvePackBuildLiveVideoId,
  studioPackBuildLiveSuccessReceiptForSelection,
  studioPackLiveReceiptForSelection,
  verifyPackBuildLive,
  type PackBuildLiveFailureDetails,
} from '@/lib/pack-build-live-client';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import { identityPackJson } from '@/lib/emit-video-pack';
import {
  studioDedupeSopStepsAgainstEvents,
  studioOutlineSectionToPane,
  studioPaneToOutlineSection,
  studioResolveActivePane,
  studioSummaryIsRedundant,
  studioTranscriptSummaryLabel,
  studioWorkbenchTabs,
  type StudioPaneId,
} from '@/lib/studio-workbench-panes';
import {
  studioActionCard,
  studioCanExport,
  studioCanRetryTranscript,
  studioDeployButtonLabel,
  studioDeployEnabledHint,
  studioDeployOutcomeMessage,
  studioDeployReceiptForSelection,
  studioEventsEmptyMessage,
  studioExportFilename,
  studioExportToastMessage,
  studioFormationSupplementalEntities,
  studioInvalidHandoffMessage,
  studioJobStripDestination,
  studioPackCitation,
  studioPackFormation,
  studioPackIdentity,
  studioResolveAutoSelectedPackId,
  studioPasteOutcomeMessage,
  studioPlayerOverlay,
  studioPlayerPhase,
  studioPromotePackWorkbench,
  studioRunQuality,
  studioStatusLabel,
  studioStatusMessage,
  studioTranscriptBody,
  studioTranscriptEtaLabel,
  studioTranscriptStage,
  studioVerifiedLiveUrl,
  studioWorkbenchEmptyView,
} from '@/lib/studio-pipeline-status';
import { useYouTubePlayer } from '@/lib/use-youtube-player';
import {
  buildSameRunActInput,
  MIN_ACT_TRANSCRIPT_CHARS,
  usableProvidedTranscript,
} from '@/lib/video-to-actions-input';
import {
  applyStudioQueryAutoStart,
  resetStudioQueryAutoStart,
  resolveStudioHandoff,
  studioQueryFromSearchParams,
} from '@/lib/studio-handoff';
import {
  evaluateStudioDeployTransition,
  studioDeployAttemptTransitionId,
  studioGateReceiptView,
  type GateDecision,
  type StudioGateReceiptView,
} from '@/lib/gate-transition';
import { CANONICAL_STUDIO_PATH } from '@/lib/auth-paths';
import type { ExtractedEvent } from '@/lib/types';
import type { VideoPackArchitecture, VideoPackArtifact } from '@/lib/video-pack-types';
import { openGitHubPrsForApprovedSpecs } from '@/app/studio/actions';
import StudioIdeShell from '@/components/studio/StudioIdeShell';
import StudioIdeChat from '@/components/studio/StudioIdeChat';
import StudioIdeOutput from '@/components/studio/StudioIdeOutput';
import {
  chaptersFromPack,
  sopStepsFromPack,
} from '@/lib/emit-app-builder-sandbox';

const FIXTURE = 'https://www.youtube.com/watch?v=auJzb1D-fag';

function gateDecisionChipClass(decision: GateDecision): string {
  switch (decision) {
    case 'PASS':
      return 'border-emerald-300 bg-emerald-50 text-emerald-700';
    case 'HOLD':
      return 'border-amber-300 bg-amber-50 text-amber-700';
    case 'REJECT':
      return 'border-red-300 bg-red-50 text-red-700';
    case 'ESCALATE':
      return 'border-violet-300 bg-violet-50 text-violet-700';
    default: {
      const _exhaustive: never = decision;
      return _exhaustive;
    }
  }
}

function getYouTubeId(url: string) {
  return extractYouTubeId(url) || '';
}

function toSpecBranch(videoId: string, stepId: string): string {
  const slug = `${videoId || 'video'}-${stepId}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48);
  return `spec/${slug || 'approved'}`;
}

function mapExtractedEvents(raw: unknown[], videoId: string): ExtractedEvent[] {
  return raw
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .map((item, i) => {
      const priority = typeof item.priority === 'string' ? item.priority : '';
      return {
        id: `evt_${videoId}_${i}`,
        type: (typeof item.type === 'string' ? item.type : 'topic') as ExtractedEvent['type'],
        title: typeof item.title === 'string' ? item.title : 'Event',
        description: typeof item.description === 'string' ? item.description : undefined,
        timestamp: typeof item.timestamp === 'string' ? item.timestamp : undefined,
        confidence: priority === 'high' ? 0.95 : priority === 'medium' ? 0.75 : 0.5,
      };
    });
}

/** Session-gated enrich. 401/403 means anonymous — Act still proceeds. */
async function tryExtractEvents(input: {
  transcript: string;
  videoTitle?: string;
  videoUrl: string;
  videoId: string;
}): Promise<ExtractedEvent[] | null> {
  const res = await fetch('/api/extract-events', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      transcript: input.transcript,
      videoTitle: input.videoTitle,
      videoUrl: input.videoUrl,
    }),
    signal: AbortSignal.timeout(45_000),
  });
  if (res.status === 401 || res.status === 403) return null;
  const extraction = (await res.json().catch(() => null)) as {
    success?: boolean;
    data?: { events?: unknown[] };
  } | null;
  if (!extraction?.success || !Array.isArray(extraction.data?.events)) return null;
  const events = mapExtractedEvents(extraction.data.events, input.videoId);
  return events.length > 0 ? events : null;
}

function PackWorkbench({
  architecture,
  artifacts,
  onExport,
  canExport,
}: {
  architecture: VideoPackArchitecture | null;
  artifacts: VideoPackArtifact[];
  onExport: () => void;
  canExport: boolean;
}) {
  return (
    <section
      data-testid="pack-workbench"
      className="uvai-card p-4 lg:col-span-2"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">
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
            <p className="mt-2 text-sm text-slate-600">{architecture.summary}</p>
          ) : null}
          {architecture.stages.length > 0 ? (
            <ol className="mt-2 space-y-1 text-sm text-slate-700">
              {architecture.stages.map((stage) => (
                <li key={stage.id}>
                  <span className="font-medium text-slate-900">{stage.name}</span>
                  {stage.description ? ` — ${stage.description}` : ''}
                </li>
              ))}
            </ol>
          ) : null}
          {architecture.mermaid ? (
            <pre className="mt-2 overflow-auto rounded-lg bg-slate-900 p-3 font-mono text-[11px] leading-5 text-slate-200">
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
                <div className="truncate font-mono text-[12px] font-semibold text-blue-700">{artifact.path_hint}</div>
                <div className="mt-0.5 truncate text-sm text-slate-700">{artifact.purpose}</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-slate-400">{artifact.interface}</div>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function StudioJobStripDestination({
  destination,
}: {
  destination: ReturnType<typeof studioJobStripDestination>;
}) {
  switch (destination.kind) {
    case 'video':
      return (
        <span data-testid="studio-job-video-id" className="text-slate-500">
          {destination.label}
        </span>
      );
    case 'studio':
      return (
        <Link
          href={destination.href}
          data-testid="studio-job-self-link"
          className="text-slate-500 underline decoration-slate-300 underline-offset-2 hover:text-slate-700"
        >
          {destination.label}
        </Link>
      );
    default: {
      const _exhaustive: never = destination;
      return _exhaustive;
    }
  }
}

export default function OneLoopStudio({
  showAgentWorkflowUi,
}: {
  showAgentWorkflowUi: boolean;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState('Paste a YouTube URL. Transcript and events land here.');
  const [actBusy, setActBusy] = useState(false);
  const [deployBusy, setDeployBusy] = useState(false);
  const runAbortRef = useRef<AbortController | null>(null);
  const [workflowActions, setWorkflowActions] = useState<VideoToActionsResult | null>(null);
  const [actRunId, setActRunId] = useState<string | null>(null);
  const [usedSameRun, setUsedSameRun] = useState(false);
  const [deployRunId, setDeployRunId] = useState<string | null>(null);
  const [deployReceiptUrl, setDeployReceiptUrl] = useState<string | null>(null);
  const [deployReceiptVideoId, setDeployReceiptVideoId] = useState<string | null>(null);
  const [buildBusy, setBuildBusy] = useState(false);
  const [packLiveReceiptUrl, setPackLiveReceiptUrl] = useState<string | null>(null);
  const [packLiveReceiptVideoId, setPackLiveReceiptVideoId] = useState<string | null>(null);
  const [packLiveReceiptYoutubeId, setPackLiveReceiptYoutubeId] = useState<string | null>(null);
  const [packLiveReceiptReasonCode, setPackLiveReceiptReasonCode] = useState<string | null>(null);
  const [gateReceipt, setGateReceipt] = useState<StudioGateReceiptView | null>(null);
  const [completedChecks, setCompletedChecks] = useState<string[]>([]);
  const [approvedSpecIds, setApprovedSpecIds] = useState<string[]>([]);
  const [openingPrs, setOpeningPrs] = useState(false);
  const [playerEpoch, setPlayerEpoch] = useState(0);
  const [exportToast, setExportToast] = useState<{ tone: 'success' | 'error'; text: string } | null>(
    null,
  );
  const [buildLiveFailure, setBuildLiveFailure] = useState<PackBuildLiveFailureDetails | null>(
    null,
  );
  const autoStartedKey = useRef<string | null>(null);
  const autoSelectedPackRef = useRef(false);
  const [requestedPane, setRequestedPane] = useState<StudioPaneId | null>(null);
  const [transcriptExpanded, setTranscriptExpanded] = useState(false);

  const processVideo = useDashboardStore((s) => s.processVideo);
  const selectVideo = useDashboardStore((s) => s.selectVideo);
  const updateVideo = useDashboardStore((s) => s.updateVideo);
  const removeVideo = useDashboardStore((s) => s.removeVideo);
  const selectedVideoId = useDashboardStore((s) => s.selectedVideoId);
  const videos = useDashboardStore((s) => s.videos);
  const selected = videos.find((v) => v.id === selectedVideoId);
  const scopedDeployReceipt = studioDeployReceiptForSelection({
    selectedVideoId,
    receiptVideoId: deployReceiptVideoId,
    liveUrl: deployReceiptUrl,
  });
  const scopedPackLiveUrl = studioPackLiveReceiptForSelection({
    selectedVideoId,
    receiptVideoId: packLiveReceiptVideoId,
    liveUrl: packLiveReceiptUrl,
  });
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
  const supplementalEntities = studioFormationSupplementalEntities(
    packFormation.tools,
    linkedSop?.entities,
  );

  useEffect(() => {
    setCompletedChecks([]);
    setApprovedSpecIds([]);
    setDeployReceiptUrl(null);
    setDeployReceiptVideoId(null);
    setGateReceipt(null);
    setBuildLiveFailure(null);
    setPackLiveReceiptUrl(null);
    setPackLiveReceiptVideoId(null);
    setPackLiveReceiptYoutubeId(null);
    setPackLiveReceiptReasonCode(null);
    // A new row opens on the default Video pane with the transcript collapsed.
    setRequestedPane(null);
    setTranscriptExpanded(false);
  }, [selectedVideoId]);

  useEffect(() => {
    if (!exportToast) return;
    const timer = window.setTimeout(() => setExportToast(null), 4000);
    return () => window.clearTimeout(timer);
  }, [exportToast]);

  const holdReason = deployHoldReason(linkedSop, completedChecks, 'anonymous');
  const officialTemplate = pickOfficialTemplate(linkedSop);

  useEffect(() => {
    useDashboardStore.persist.rehydrate();
  }, []);

  // A stored pack must drive the header + transcript without a Stored packs
  // combobox click (#2244). Once, after rehydration, point the selection at the
  // newest row that already has pack identity — unless a selection or a
  // `?video=` handoff already owns the row. This is display-only: it selects an
  // existing row and never starts extraction.
  useEffect(() => {
    if (autoSelectedPackRef.current) return;
    if (selectedVideoId || studioQueryFromSearchParams(searchParams)) {
      autoSelectedPackRef.current = true;
      return;
    }
    const targetId = studioResolveAutoSelectedPackId({ selectedVideoId, videos });
    if (targetId) {
      autoSelectedPackRef.current = true;
      selectVideo(targetId);
    }
  }, [selectedVideoId, videos, searchParams, selectVideo]);

  const runAnalysis = async (raw: string) => {
    const handoff = resolveStudioHandoff(raw);
    if (!handoff) {
      setMessage('Need a valid YouTube URL.');
      return;
    }
    const next = handoff.watchUrl;
    setUrl(next);
    // Cancel any in-flight run before starting a new one.
    runAbortRef.current?.abort();
    const controller = new AbortController();
    runAbortRef.current = controller;
    setBusy(true);
    setWorkflowActions(null);
    setActRunId(null);
    setUsedSameRun(false);
    setMessage('Fetching transcript…');
    const tick = window.setInterval(() => {
      const matches = useDashboardStore
        .getState()
        .videos.filter((v) => v.url === next || v.url.includes(handoff.videoId));
      if (matches.length === 0) return;
      selectVideo(matches[0].id);
    }, 250);
    try {
      const id = await processVideo(next, { signal: controller.signal });
      if (controller.signal.aborted) {
        setMessage('Analysis cancelled.');
        return;
      }
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
      if (controller.signal.aborted) {
        setMessage('Analysis cancelled.');
      } else {
        setMessage(err instanceof Error ? err.message : 'Analysis failed.');
      }
    } finally {
      window.clearInterval(tick);
      if (runAbortRef.current === controller) {
        runAbortRef.current = null;
        setBusy(false);
      }
    }
  };

  const cancelAnalysis = useCallback(() => {
    runAbortRef.current?.abort();
    setMessage('Cancelling analysis…');
  }, []);

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

  const transcriptWorking = busy || selected?.status === 'processing';

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
  // Destructure at the hook call so render reads booleans + a callback ref,
  // not properties of an object that also carries refs (react-hooks/refs).
  const { containerRef, ready: playerReady, failed: playerFailed, seekTo } =
    useYouTubePlayer(videoId);

  const playerPhase = studioPlayerPhase({
    videoId: videoId || null,
    loaded: playerReady,
    failed: playerFailed,
  });
  const playerOverlay = studioPlayerOverlay(playerPhase);
  const eventCount = selected?.events?.length ?? 0;
  const promotePack = studioPromotePackWorkbench({
    eventCount,
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
  const runState = busy ? 'working' : selected ? 'ready' : 'idle';
  const quality = studioRunQuality(
    selected?.jobId ? { ok: true, status: 200, jobId: selected.jobId } : null,
    false,
    Boolean(videoId || selected),
    { transcript: selected?.transcript, eventCount: selected?.events?.length ?? 0 },
  );
  const workbenchEmpty = studioWorkbenchEmptyView({
    busy: transcriptWorking,
    hasSelection: Boolean(selected),
    hasVideoPack: Boolean(selected?.videoPack),
    analysisReady: quality === 'live',
    failed: selected?.status === 'failed',
    failureMessage: selected?.failure?.message,
  });
  const resultReadyShell = Boolean(selected?.videoPack?.pack);
  const shellPack = selected?.videoPack?.pack;
  const shellChapters = useMemo(
    () => (shellPack ? chaptersFromPack(shellPack.chapters) : []),
    [shellPack],
  );
  const shellSopSteps = useMemo(() => {
    if (!shellPack) return [];
    const transcript = shellPack.transcript
      ? {
          full_text: shellPack.transcript.full_text,
          language: 'language' in shellPack.transcript ? shellPack.transcript.language : null,
          segments: shellPack.transcript.segments,
        }
      : null;
    return sopStepsFromPack({ requirements: shellPack.requirements, transcript });
  }, [shellPack]);
  const selectShellPane = useCallback((sectionId: string) => {
    const pane = studioOutlineSectionToPane(sectionId);
    if (pane) setRequestedPane(pane);
  }, []);
  const canAttemptBuildLive = Boolean(
    getYouTubeId(url || selected?.url || '') && (selected || url.trim()),
  );

  const act = async () => {
    const next = (selected?.url || url).trim();
    if (!getYouTubeId(next)) {
      setMessage('Analyze a video before acting.');
      return;
    }
    setActBusy(true);
    setWorkflowActions(null);
    setActRunId(null);
    setMessage('Acting on this run\'s transcript…');
    try {
      let events = selected?.events;
      const transcript = selected?.transcript?.trim() || '';
      if (selected && transcript.length >= MIN_ACT_TRANSCRIPT_CHARS && !(events?.length)) {
        try {
          const enriched = await tryExtractEvents({
            transcript,
            videoTitle: selected.title,
            videoUrl: next,
            videoId: selected.id,
          });
          if (enriched) {
            updateVideo(selected.id, { events: enriched });
            events = enriched;
          }
        } catch {
          // extract-events is optional; Act still uses the Analyze transcript.
        }
      }

      const sopEvents = (linkedSop?.steps || []).map((step) => ({
        type: 'action',
        title: step.title,
        description: step.description,
      }));
      const payload = buildSameRunActInput({
        url: next,
        videoTitle: selected?.title,
        transcript: selected?.transcript,
        events: [...(events || []), ...sopEvents],
      });
      setUsedSameRun(Boolean(payload.transcript || payload.events?.length));

      const started = await startVideoToActions(payload);
      if (!started.ok || !started.runId) {
        if (started.status === 401 || started.status === 403) {
          router.push(`/login?callbackUrl=${encodeURIComponent(CANONICAL_STUDIO_PATH)}`);
          return;
        }
        setMessage(started.error || started.message || 'Could not start Act.');
        return;
      }
      setActRunId(started.runId);
      setMessage(
        payload.transcript
          ? `Act ${started.runId} started on this run's transcript.`
          : `Act ${started.runId} started.`,
      );
      const polled = await pollVideoToActions(started.runId, {
        statusUrl: started.statusUrl,
        attempts: 24,
        delayMs: 2000,
      });
      if (polled.runStatus === 'completed' && polled.result) {
        setWorkflowActions(polled.result);
        const sameRun =
          polled.result.usedProvidedTranscript ??
          Boolean(payload.transcript || payload.events?.length);
        setUsedSameRun(sameRun);
        setMessage(
          `Act completed — ${polled.result.actionCount} tool result(s) on this page.`,
        );
      } else {
        setMessage(polled.error || `Act status: ${polled.runStatus || 'unknown'}.`);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Act failed.');
    } finally {
      setActBusy(false);
    }
  };

  const exportPkg = async () => {
    const filename = studioExportFilename(
      safeProjectName(selected?.title || 'uvai-project'),
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
      workflowActions: workflowActions?.actions,
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
        projectName: selected?.title || 'uvai-project',
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
        if (result.status === 402 && result.checkoutUrl) {
          setExportToast({ tone: 'error', text: 'Workspace ZIP exports require Pro. Redirecting to checkout…' });
          window.location.href = result.checkoutUrl;
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

  const deploy = async () => {
    const next = (selected?.url || url).trim();
    if (!getYouTubeId(next)) {
      setMessage('Analyze a video before deploy.');
      return;
    }
    if (holdReason) {
      setMessage(holdReason);
      return;
    }
    setDeployBusy(true);
    const attemptVideoId = selectedVideoId ?? null;
    setDeployReceiptUrl(null);
    setDeployReceiptVideoId(attemptVideoId);
    setGateReceipt(null);
    try {
      const started = await startStudioDeploy({ url: next });
      if (useDashboardStore.getState().selectedVideoId !== attemptVideoId) return;
      if (started.status === 401 || started.status === 403) {
        router.push(`/login?callbackUrl=${encodeURIComponent(CANONICAL_STUDIO_PATH)}`);
        return;
      }
      if (started.gate) {
        setGateReceipt(started.gate);
        setMessage(started.gate.reason);
        return;
      }
      if (!started.ok || !started.runId) {
        const backendReason = started.error || started.message || 'Deploy needs sign-in.';
        const gated = evaluateStudioDeployTransition({
          transitionId: studioDeployAttemptTransitionId({ videoId: attemptVideoId }),
          kind: 'handoff',
          backendReason,
          authority: { actor: 'anonymous' },
        });
        setGateReceipt(studioGateReceiptView(gated, { backendReason }));
        setMessage(backendReason);
        return;
      }
      setDeployRunId(started.runId);
      const polled = await pollStudioDeploy(started.runId);
      if (useDashboardStore.getState().selectedVideoId !== attemptVideoId) return;
      const backendReason = studioDeployPollResidual(polled);
      const liveCandidate = polled.result?.live_url?.trim() ?? '';
      const deploymentHttpProbe = liveCandidate
        ? (await probeStudioDeployLiveUrl(liveCandidate)).probe
        : undefined;
      const gated = evaluateStudioDeployTransition({
        transitionId: started.runId,
        runId: started.runId,
        jobId: polled.result?.jobId,
        liveUrl: polled.result?.live_url,
        runStatus: polled.runStatus,
        kind: polled.result?.kind,
        backendReason,
        deploymentHttpProbe,
        authority: { actor: 'anonymous' },
      });
      setGateReceipt(studioGateReceiptView(gated, { backendReason }));
      const liveUrl = gated.decision === 'PASS' ? polled.result?.live_url : undefined;
      setDeployReceiptUrl(studioVerifiedLiveUrl(liveUrl));
      setDeployReceiptVideoId(attemptVideoId);
      setMessage(
        studioDeployOutcomeMessage({
          liveUrl,
          runStatus: polled.runStatus,
          error: backendReason || polled.error,
          kind: polled.result?.kind,
          message: polled.result?.message,
          jobId: polled.result?.jobId,
          jobStatus: polled.result?.jobStatus,
        }),
      );
    } catch (err) {
      if (useDashboardStore.getState().selectedVideoId !== attemptVideoId) return;
      const backendReason = studioDeployOutcomeMessage({
        error: err instanceof Error ? err.message : 'Deploy failed.',
        runStatus: 'failed',
      });
      const gated = evaluateStudioDeployTransition({
        transitionId: studioDeployAttemptTransitionId({ videoId: attemptVideoId }),
        kind: 'handoff',
        backendReason,
        authority: { actor: 'anonymous' },
      });
      setGateReceipt(studioGateReceiptView(gated, { backendReason }));
      setMessage(backendReason);
    } finally {
      setDeployBusy(false);
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

  const openApprovedSpecsPrs = async () => {
    if (!linkedSop || linkedSop.steps.length === 0) {
      setMessage('Analyze a video with SOP steps before opening GitHub pull requests.');
      return;
    }
    const sourceVideoId = getYouTubeId(selected?.url || url || '');
    const specs = linkedSop.steps.map((step) => ({
      id: step.id,
      title: step.title,
      body: [step.description || '', step.quote ? `\nQuote: ${step.quote}` : ''].join('').trim(),
      head: toSpecBranch(sourceVideoId, step.id),
      base: 'main',
      approved: approvedSpecIds.includes(step.id),
    }));
    setOpeningPrs(true);
    try {
      const result = await openGitHubPrsForApprovedSpecs(specs);
      if (!result.ok) {
        setMessage(result.error || 'Could not open GitHub pull requests for approved specs.');
        return;
      }
      setMessage(`Opened or updated ${result.pullRequests.length} GitHub pull request(s) for approved specs.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not open GitHub pull requests.');
    } finally {
      setOpeningPrs(false);
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
    hasFailed: selected?.status === 'failed',
  });
  const showTranscriptRetry = studioCanRetryTranscript({
    busy: transcriptWorking,
    hasFailed: selected?.status === 'failed',
    retryable: selected?.failure?.retryable !== false,
    elapsedSeconds: elapsed,
  });
  const statusText = transcriptWorking
    ? `Working · ${elapsed}s — ${transcriptStage.label}. ${studioTranscriptEtaLabel(elapsed)}`
    : `${studioStatusLabel(quality, runState)} — ${message || studioStatusMessage(quality, runState, 'Analysis', false)}`;

  // ── Single-pane workbench model (layout only) ──────────────────────────────
  // In the Result Ready shell we show one main pane at a time (Cursor-style),
  // not the whole pack stacked into one enormous scroll. The classic (no-pack)
  // path keeps stacking, so `paneVisible` is a no-op there.
  const inWorkbench = resultReadyShell && Boolean(selected?.videoPack);
  const dedupedSopSteps = studioDedupeSopStepsAgainstEvents(
    selected?.events ?? [],
    linkedSop?.steps ?? [],
  );
  const hasWorkflowPane = Boolean(
    linkedSop && (linkedSop.entities.length > 0 || linkedSop.steps.length > 0 || packFormation.tools.length > 0),
  );
  const summaryText = selected?.insights?.summary ?? '';
  const summaryRedundant = studioSummaryIsRedundant(summaryText, [
    ...(selected?.events ?? []).map((event) => event.title),
    ...dedupedSopSteps.map((step) => step.title),
  ]);
  const hasSummaryPane = Boolean(summaryText.trim()) && !summaryRedundant;
  const hasTranscriptPane =
    Boolean(selected?.transcript?.trim()) || transcriptWorking || showTranscriptRetry;
  const hasActionsPane = Boolean(showAgentWorkflowUi && (actRunId || workflowActions));
  const workbenchTabs = studioWorkbenchTabs({
    hasTranscript: hasTranscriptPane,
    hasActions: hasActionsPane,
    hasEvents: eventCount > 0,
    hasWorkflow: hasWorkflowPane,
    hasSpec: Boolean(selected?.videoPack?.pack),
    hasSummary: hasSummaryPane,
    hasPack: Boolean(selected?.videoPack),
  });
  const activePane = studioResolveActivePane(requestedPane, workbenchTabs);
  const paneVisible = (pane: StudioPaneId) => !inWorkbench || activePane === pane;
  const transcriptWordCount = selected?.transcript
    ? selected.transcript.trim().split(/\s+/).length
    : 0;

  return (
    <div className="flex min-h-screen flex-col bg-[#f2f5f9] text-slate-900">
      <Nav tone="light" rightSlot={<StudioAuthNavLink />} />

      <StudioIdeShell
        toolbar={
          <>
            <form onSubmit={analyze} className="flex min-w-0 flex-1 items-center gap-2" data-testid="studio-ide-url-form">
              <label className="sr-only" htmlFor="youtube-url">
                YouTube URL
              </label>
              <input
                id="youtube-url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder={FIXTURE}
                autoComplete="off"
                className="uvai-input min-w-0 flex-1 font-mono disabled:opacity-40"
              />
              <button
                type="button"
                onClick={() => setUrl(FIXTURE)}
                disabled={busy}
                className="uvai-btn !px-2.5 disabled:opacity-40"
              >
                Sample
              </button>
              {busy ? (
                <button
                  type="button"
                  onClick={cancelAnalysis}
                  data-testid="studio-ide-cancel"
                  className="uvai-btn uvai-btn-danger !font-semibold"
                >
                  Cancel
                </button>
              ) : (
                <button
                  type="submit"
                  data-testid="studio-ide-run"
                  className="uvai-btn uvai-btn-primary"
                >
                  Run
                </button>
              )}
            </form>
            {videos.some((video) => video.videoPack) ? (
              <div className="flex items-center gap-1.5" data-testid="studio-ide-packs">
                <select
                  id="stored-pack"
                  value={selected?.videoPack ? selected.id : ''}
                  disabled={busy}
                  onChange={(event) => selectVideo(event.target.value || null)}
                  aria-label="Stored packs"
                  className="uvai-input max-w-44 truncate !py-1.5 !text-xs disabled:opacity-40"
                >
                  <option value="">Stored packs</option>
                  {videos.filter((video) => video.videoPack).map((video) => (
                    <option key={video.id} value={video.id}>{video.title}</option>
                  ))}
                </select>
                {selected?.videoPack ? (
                  <button
                    type="button"
                    onClick={() => removeVideo(selected.id)}
                    disabled={busy}
                    aria-label="Delete this pack"
                    title="Delete this pack"
                    data-testid="studio-ide-delete-pack"
                    className="uvai-btn uvai-btn-danger !px-2.5 !py-1.5 disabled:opacity-40"
                  >
                    ✕
                  </button>
                ) : null}
              </div>
            ) : null}
            <div className="flex items-center gap-1.5" role="toolbar" aria-label="Pack actions">
              <button
                type="button"
                onClick={exportPkg}
                disabled={!hasPayload}
                data-testid="studio-ide-export"
                className="uvai-btn disabled:opacity-40"
              >
                Export
              </button>
              <button
                type="button"
                data-testid="studio-build-live-button"
                onClick={() => void buildLive()}
                disabled={buildBusy || !canAttemptBuildLive}
                title={
                  selected?.videoPack
                    ? `Compile the stored Video Pack for ${selected.videoPack.videoId}.`
                    : canAttemptBuildLive
                      ? 'Verify pack health and open the hosted app, or get recovery steps if the pack is missing.'
                      : 'Paste a YouTube URL and run analysis first.'
                }
                className="uvai-btn uvai-btn-primary disabled:opacity-40"
              >
                {buildBusy ? 'Building…' : 'Build live'}
              </button>
              <button
                type="button"
                data-testid="studio-deploy-button"
                onClick={() => void deploy()}
                disabled={deployBusy || !hasPayload || Boolean(holdReason)}
                aria-describedby="studio-preflight-hint"
                title={holdReason || studioDeployEnabledHint(Boolean(scopedDeployReceipt))}
                className="uvai-btn disabled:opacity-40"
              >
                {deployBusy ? 'Checking preflight…' : 'Check preflight'}
              </button>
            </div>
            <p id="studio-preflight-hint" className="w-full text-[11px] text-slate-400">
              {studioDeployEnabledHint(Boolean(scopedDeployReceipt))}
            </p>
            <p className="w-full font-mono text-[11px] text-slate-500" role="status" data-testid="studio-ide-status">
              {statusText}
            </p>
            {gateReceipt ? (
              <div
                data-testid="studio-gate-receipt"
                role="status"
                className="uvai-card flex w-full flex-wrap items-start gap-2 px-3 py-2.5"
              >
                <span
                  data-testid="studio-gate-decision"
                  className={clsx(
                    'inline-flex rounded-full border px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em]',
                    gateDecisionChipClass(gateReceipt.decision),
                  )}
                >
                  {gateReceipt.decision}
                </span>
                <div className="min-w-0 flex-1">
                  <p data-testid="studio-gate-reason" className="text-sm text-slate-800">
                    {gateReceipt.reason}
                  </p>
                  <p className="text-sm text-slate-500">
                    {gateReceipt.version === 'eventrelay.gate-receipt.v2'
                      ? 'Server decision. Later stages require separate Loop approval.'
                      : 'Local diagnostic only — not an authorization receipt.'}
                  </p>
                  <p className="mt-1 font-mono text-[11px] text-slate-400">
                    <span data-testid="studio-gate-receipt-id">{gateReceipt.receiptId}</span>
                    {' · '}
                    <span data-testid="studio-gate-receipt-hash">{gateReceipt.receiptHash}</span>
                    {' · '}
                    {gateReceipt.version}
                  </p>
                  {gateReceipt.transitionId ? (
                    <p className="break-all text-sm text-slate-400">
                      Transition: {gateReceipt.transitionId}
                      {' · '}
                      {gateReceipt.retained ? 'Receipt retained' : 'Receipt not retained'}
                    </p>
                  ) : null}
                  {scopedDeployReceipt ? (
                    <p className="mt-1">
                      <a
                        data-testid="studio-gate-live-url"
                        href={scopedDeployReceipt}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="break-all text-sm text-blue-700 underline"
                      >
                        {scopedDeployReceipt}
                      </a>
                    </p>
                  ) : null}
                </div>
              </div>
            ) : null}
          </>
        }
        videoPane={
          <div className="flex flex-col gap-3">
            <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-slate-900 shadow-sm">
              {videoId ? (
                <>
                  <div key={`${videoId}-${playerEpoch}`} className="aspect-video w-full">
                    <div
                      ref={containerRef}
                      className="h-full w-full"
                      data-testid="studio-player"
                      title="YouTube source"
                    />
                  </div>
                  {playerOverlay ? (
                    <div
                      data-testid="studio-player-overlay"
                      className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-slate-50 px-6 text-center"
                    >
                      <p className="text-sm text-slate-700">{playerOverlay}</p>
                      {playerPhase === 'error' ? (
                        <div className="flex flex-wrap items-center justify-center gap-2">
                          <button
                            type="button"
                            data-testid="studio-player-retry"
                            onClick={() => setPlayerEpoch((epoch) => epoch + 1)}
                            className="uvai-btn uvai-btn-primary"
                          >
                            Retry player
                          </button>
                          <a
                            href={`https://www.youtube.com/watch?v=${videoId}`}
                            target="_blank"
                            rel="noreferrer"
                            className="uvai-btn"
                          >
                            Open on YouTube
                          </a>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="flex aspect-video items-center justify-center bg-slate-100 px-6 text-center text-sm text-slate-500">
                  Paste a link above. The video plays here while we pull the transcript.
                </div>
              )}
            </div>
            {selected?.videoPack ? (
              <div className="uvai-card p-3">
                <p className="uvai-section-label">Video pack</p>
                <p className="mt-1.5 font-mono text-[11px] text-slate-500">
                  <span className="font-semibold text-amber-700">{selected.videoPack.sourceHash.slice(0, 12)}…</span>
                </p>
                <p className="mt-0.5 truncate text-xs text-slate-400">{selected.videoPack.sourceUrl}</p>
              </div>
            ) : null}
          </div>
        }
        chatPane={
          <StudioIdeChat
            videoId={selected?.videoPack?.videoId ?? videoId ?? null}
            packId={selected?.videoPack?.packId ?? null}
            disabled={busy}
          />
        }
        outputPane={
          <StudioIdeOutput
            video={selected}
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
        }
      />


      {exportToast ? (
        <div
          data-testid="studio-export-toast"
          role={exportToast.tone === 'error' ? 'alert' : 'status'}
          className={clsx(
            'fixed bottom-20 left-1/2 z-40 w-[min(36rem,calc(100%-2rem))] -translate-x-1/2 rounded-lg border px-4 py-3 text-sm shadow-lg',
            exportToast.tone === 'success'
              ? 'border-amber-300 bg-amber-50 text-amber-800'
              : 'border-red-300 bg-red-50 text-red-800',
          )}
        >
          {exportToast.text}
        </div>
      ) : null}

      {scopedPackBuildLiveSuccess ? (
        <div
          data-testid="studio-pack-build-live-result"
          role="status"
          className="border-t border-amber-200 bg-amber-50/80"
        >
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:px-6">
            <div className="flex flex-wrap items-start gap-2">
              <span
                data-testid="studio-pack-build-live-state"
                className="inline-flex rounded-full border border-amber-300 bg-white px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-amber-700"
              >
                Ready
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-900">
                  {scopedPackBuildLiveSuccess.jobTitle} · {scopedPackBuildLiveSuccess.subtitle}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  YouTube video id{' '}
                  <span
                    data-testid="studio-pack-build-live-video-id"
                    className="font-mono text-amber-700"
                  >
                    {scopedPackBuildLiveSuccess.youtubeVideoId}
                  </span>
                </p>
                <p
                  data-testid="studio-pack-build-live-reason-code"
                  className="mt-1 font-mono text-[11px] text-slate-400"
                >
                  {scopedPackBuildLiveSuccess.reasonCode}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                data-testid="studio-pack-build-live-artifact-link"
                href={scopedPackBuildLiveSuccess.artifactPath}
                className="uvai-btn uvai-btn-primary inline-flex w-fit items-center justify-center"
              >
                Open {scopedPackBuildLiveSuccess.artifactPath}
              </Link>
              <Link
                data-testid="studio-pack-build-live-pro-cta"
                href="/#get-pro"
                className="uvai-btn inline-flex w-fit items-center justify-center"
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
          className="border-t border-red-200 bg-red-50/80"
        >
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:px-6">
            <div>
              <p className="text-sm font-medium text-red-800">{buildLiveFailure.title}</p>
              <p className="mt-1 text-sm text-red-700/85">{buildLiveFailure.message}</p>
              {buildLiveFailure.reasonCode ? (
                <p className="mt-1 font-mono text-[11px] text-red-600/60">
                  {buildLiveFailure.reasonCode}
                </p>
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
                    className="uvai-btn"
                  >
                    {action.label}
                  </a>
                ) : (
                  <button
                    key={action.id}
                    type="button"
                    data-testid={`studio-build-live-recovery-${action.id}`}
                    onClick={() => runBuildLiveRecovery(action)}
                    className="uvai-btn"
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
