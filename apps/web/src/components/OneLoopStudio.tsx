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
  studioStackCheckView,
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
  pollVideoToActions,
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
  studioShipCta,
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
import type { VideoPackArchitecture, VideoPackArtifact, VideoPackStackTool } from '@/lib/video-pack-types';
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
      return 'border-[var(--uvai-success-border)] bg-[var(--uvai-success-bg)] text-[var(--uvai-success-ink)]';
    case 'HOLD':
      return 'border-[var(--uvai-warn-border)] bg-[var(--uvai-warn-bg)] text-[var(--uvai-warn-ink)]';
    case 'REJECT':
      return 'border-[var(--uvai-danger-border)] bg-[var(--uvai-danger-bg)] text-[var(--uvai-danger-ink)]';
    case 'ESCALATE':
      return 'border-[var(--uvai-violet-border)] bg-[var(--uvai-violet-bg)] text-[var(--uvai-violet-ink)]';
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

function StudioJobStripDestination({
  destination,
}: {
  destination: ReturnType<typeof studioJobStripDestination>;
}) {
  switch (destination.kind) {
    case 'video':
      return (
        <span data-testid="studio-job-video-id" className="text-[var(--uvai-ink-faint)]">
          {destination.label}
        </span>
      );
    case 'studio':
      return (
        <Link
          href={destination.href}
          data-testid="studio-job-self-link"
          className="text-[var(--uvai-ink-faint)] underline decoration-[var(--uvai-border-strong)] underline-offset-2 hover:text-[var(--uvai-ink)]"
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
  const runAbortRef = useRef<AbortController | null>(null);
  const [workflowActions, setWorkflowActions] = useState<VideoToActionsResult | null>(null);
  const [workflowActionSelectionId, setWorkflowActionSelectionId] = useState<string | null>(null);
  const [buildBusy, setBuildBusy] = useState(false);
  const [packLiveReceiptUrl, setPackLiveReceiptUrl] = useState<string | null>(null);
  const [packLiveReceiptVideoId, setPackLiveReceiptVideoId] = useState<string | null>(null);
  const [packLiveReceiptYoutubeId, setPackLiveReceiptYoutubeId] = useState<string | null>(null);
  const [packLiveReceiptReasonCode, setPackLiveReceiptReasonCode] = useState<string | null>(null);
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
  const scopedWorkflowActions = showAgentWorkflowUi &&
    workflowActionSelectionId === selectedVideoId &&
    getYouTubeId(selected?.url || '') === getYouTubeId(workflowActions?.url || '') &&
    (!url.trim() || getYouTubeId(url) === getYouTubeId(selected?.url || ''))
    ? workflowActions
    : null;
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
    setWorkflowActions(null);
    setWorkflowActionSelectionId(null);
    setCompletedChecks([]);
    setApprovedSpecIds([]);
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
    setWorkflowActionSelectionId(null);
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
  const typedVideoId = url.trim() ? getYouTubeId(url) : null;
  const selectedVideoUrlId = getYouTubeId(selected?.url || '');
  const canAct = Boolean(
    showAgentWorkflowUi &&
    selected?.status === 'complete' &&
    selected?.runId &&
    selectedVideoUrlId &&
    (!url.trim() || typedVideoId === selectedVideoUrlId),
  );

  const act = async () => {
    if (!canAct || !selected?.runId) {
      setMessage('Select the analyzed video before reviewing its actions.');
      return;
    }
    const selectionId = selected.id;
    const runId = selected.runId;
    setActBusy(true);
    setWorkflowActions(null);
    setWorkflowActionSelectionId(null);
    setMessage('Loading proposed actions from this run…');
    try {
      const polled = await pollVideoToActions(runId, {
        statusUrl: selected.statusUrl,
        attempts: 24,
        delayMs: 2000,
      });
      if (useDashboardStore.getState().selectedVideoId !== selectionId) return;
      if (polled.status === 401 || polled.status === 403) {
        router.push(`/login?callbackUrl=${encodeURIComponent(CANONICAL_STUDIO_PATH)}`);
        return;
      }
      if (polled.runStatus === 'completed' && polled.result) {
        setWorkflowActions(polled.result);
        setWorkflowActionSelectionId(selectionId);
        setMessage(
          `${polled.result.actionCount} proposed action(s) from this run are ready to review.`,
        );
      } else {
        setMessage(polled.error || `Act status: ${polled.runStatus || 'unknown'}.`);
      }
    } catch (err) {
      if (useDashboardStore.getState().selectedVideoId === selectionId) {
        setMessage(err instanceof Error ? err.message : 'Could not load proposed actions.');
      }
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
  const hasActionsPane = Boolean(scopedWorkflowActions);
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
    <div className="template-studio flex min-h-screen flex-col text-[var(--uvai-ink)]">
      <Nav rightSlot={<StudioAuthNavLink />} />

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
              {!url.trim() ? (
                <button
                  type="button"
                  onClick={() => setUrl(FIXTURE)}
                  disabled={busy}
                  className="uvai-btn !px-2.5 disabled:opacity-40"
                >
                  Sample
                </button>
              ) : null}
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
                  className={clsx('uvai-btn', !hasPayload && 'uvai-btn-primary')}
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
            <div className="flex items-center gap-1.5 sm:border-l sm:border-[var(--uvai-border-strong)] sm:pl-2" role="toolbar" aria-label="Pack actions">
              <button
                type="button"
                onClick={() => void exportPkg()}
                disabled={!shipCta.enabled}
                data-testid="studio-ide-ship"
                title={shipCta.hint}
                className={clsx(
                  'uvai-btn inline-flex items-center gap-1.5 disabled:opacity-40',
                  shipCta.enabled && hasPayload && 'uvai-btn-primary',
                )}
              >
                <Rocket className="h-4 w-4" aria-hidden />
                Ship this
              </button>
              {showAgentWorkflowUi ? (
                <button
                  type="button"
                  data-testid="studio-act-button"
                  onClick={() => void act()}
                  disabled={actBusy || !canAct}
                  title={canAct
                    ? 'Review proposed actions from the selected video run.'
                    : 'Select an analyzed video matching the URL first.'}
                  className="uvai-btn disabled:opacity-40"
                >
                  {actBusy ? 'Loading…' : 'Review this run'}
                </button>
              ) : null}
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
                className="uvai-btn text-[var(--uvai-ink-soft)] disabled:opacity-40"
              >
                {buildBusy ? 'Building…' : 'Build live'}
              </button>
            </div>
            <p className="w-full font-mono text-[11px]" style={{ color: 'var(--uvai-ink-faint)' }} role="status" data-testid="studio-ide-status">
              {statusText}
            </p>
            {showTranscriptRetry ? (
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
            ) : null}
          </>
        }
        videoPane={
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 lg:items-start">
            <div className="relative overflow-hidden rounded-lg border border-[var(--uvai-border-strong)] bg-black shadow-sm lg:col-span-8">
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
                      className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[var(--uvai-surface)] px-6 text-center"
                    >
                      <p className="text-sm text-[var(--uvai-ink-soft)]">{playerOverlay}</p>
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
                <div className="flex aspect-video items-center justify-center bg-[var(--uvai-surface)] px-6 text-center text-sm text-[var(--uvai-ink-faint)]">
                  Paste a link above. The video plays here while we pull the transcript.
                </div>
              )}
            </div>
            <div className="flex flex-col gap-3 lg:col-span-4">
              {selected?.videoPack ? (
                <div className="uvai-card p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="uvai-section-label">Extracted pack</p>
                    <span className="font-mono text-[11px] font-semibold text-[var(--uvai-accent-ink)]">
                      {selected.videoPack.sourceHash.slice(0, 12)}…
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5 text-[11px] text-[var(--uvai-ink-soft)]">
                    {selected.videoPack.pack.action_items?.length ? (
                      <span className="rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-medium">
                        {selected.videoPack.pack.action_items.length} actions
                      </span>
                    ) : null}
                    {selected.videoPack.pack.stack?.tools?.length ? (
                      <span className="rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-medium">
                        {selected.videoPack.pack.stack.tools.length} tools
                      </span>
                    ) : null}
                    {selected.videoPack.pack.code_snippets?.length ? (
                      <span className="rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-medium">
                        {selected.videoPack.pack.code_snippets.length} code files
                      </span>
                    ) : null}
                    {transcriptWordCount > 0 ? (
                      <span className="rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-medium">
                        {transcriptWordCount.toLocaleString()} words
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 truncate text-xs text-[var(--uvai-ink-faint)]">{selected.videoPack.sourceUrl}</p>
                  {selected.videoPack.pack.chapters?.length ? (
                    <div className="mt-4 border-t border-[var(--uvai-border)] pt-3">
                      <p className="uvai-section-label mb-2">Quick jump</p>
                      <ol className="flex flex-col gap-1.5">
                        {selected.videoPack.pack.chapters.slice(0, 4).map((chapter, index) => (
                          <li key={`${chapter.topic}-${index}`}>
                            <button
                              type="button"
                              onClick={() => seekTo(chapter.start)}
                              className="flex w-full items-center justify-between gap-2 rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-bg)] px-2.5 py-1.5 text-left text-xs transition-colors hover:border-[var(--uvai-border-strong)] hover:bg-[var(--uvai-surface-warm)]"
                            >
                              <span className="flex min-w-0 items-center gap-2">
                                <span className="font-mono text-[11px] font-semibold text-[var(--uvai-accent-ink)]">
                                  {String(index + 1).padStart(2, '0')}
                                </span>
                                <span className="truncate text-[var(--uvai-ink)]">{chapter.topic}</span>
                              </span>
                              <span className="shrink-0 font-mono text-[11px] text-[var(--uvai-ink-faint)]">
                                {chapter.start}s
                              </span>
                            </button>
                          </li>
                        ))}
                      </ol>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="uvai-card p-4">
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
                      <span>Interactive agent chat, Build live & Ship export</span>
                    </li>
                  </ul>
                </div>
              )}
            </div>
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
            eventsEmptyMessage={eventsEmptyMessage}
            stackChecks={stackCheckViews}
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
        }
      />


      {exportToast ? (
        <div
          data-testid="studio-export-toast"
          role={exportToast.tone === 'error' ? 'alert' : 'status'}
          className={clsx(
            'fixed bottom-4 left-1/2 z-40 w-[min(36rem,calc(100%-2rem))] -translate-x-1/2 rounded-lg border px-4 py-3 text-sm shadow-lg',
            exportToast.tone === 'success'
              ? 'border-[#146ef5]/50 bg-[#111a2e]/95 text-[#e8f0ff]'
              : 'border-red-500/45 bg-[#241012]/95 text-red-200',
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
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:px-6">
            <div className="flex flex-wrap items-start gap-2">
              <span
                data-testid="studio-pack-build-live-state"
                className="inline-flex rounded-full border border-[#146ef5]/45 bg-[var(--uvai-accent-soft)] px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--uvai-accent-ink)]"
              >
                Ready
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--uvai-ink)]">
                  {scopedPackBuildLiveSuccess.jobTitle} · {scopedPackBuildLiveSuccess.subtitle}
                </p>
                <p className="mt-1 text-sm text-[var(--uvai-ink-soft)]">
                  YouTube video id{' '}
                  <span
                    data-testid="studio-pack-build-live-video-id"
                    className="font-mono text-[var(--uvai-accent-ink)]"
                  >
                    {scopedPackBuildLiveSuccess.youtubeVideoId}
                  </span>
                </p>
                <p
                  data-testid="studio-pack-build-live-reason-code"
                  className="mt-1 font-mono text-[11px] text-[var(--uvai-ink-faint)]"
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
          className="border-t border-[var(--uvai-danger-border)] bg-[var(--uvai-danger-bg)]"
        >
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:px-6">
            <div>
              <p className="text-sm font-medium text-[var(--uvai-danger-ink)]">{buildLiveFailure.title}</p>
              <p className="mt-1 text-sm text-[var(--uvai-ink-soft)]">{buildLiveFailure.message}</p>
              {buildLiveFailure.reasonCode ? (
                <p className="mt-1 font-mono text-[11px] text-[var(--uvai-ink-faint)]">
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
