'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Download, GitPullRequest, Play, Rocket } from 'lucide-react';
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
import { useDashboardStore } from '@/store/dashboard-store';
import {
  actionsFromStudioRun,
  buildScaffoldPackage,
  downloadScaffoldPackage,
  safeProjectName,
} from '@/lib/action-surface';
import {
  pollStudioDeploy,
  pollVideoToActions,
  startStudioDeploy,
  startVideoToActions,
  type VideoToActionsResult,
} from '@/lib/studio-workflow';
import { identityPackJson } from '@/lib/emit-video-pack';
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
  studioPackCitation,
  studioPackFormation,
  studioPasteOutcomeMessage,
  studioPlayerOverlay,
  studioPlayerPhase,
  studioPromotePackWorkbench,
  studioRunQuality,
  studioStatusLabel,
  studioStatusMessage,
  studioTranscriptEtaLabel,
  studioTranscriptStage,
  studioVerifiedLiveUrl,
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

const FIXTURE = 'https://www.youtube.com/watch?v=auJzb1D-fag';

function gateDecisionChipClass(decision: GateDecision): string {
  switch (decision) {
    case 'PASS':
      return 'border-emerald-400/40 bg-emerald-950/50 text-emerald-200';
    case 'HOLD':
      return 'border-[#e8b86d]/40 bg-[#1a1408] text-[#e8b86d]';
    case 'REJECT':
      return 'border-red-400/40 bg-[#2a1212] text-red-100';
    case 'ESCALATE':
      return 'border-violet-400/40 bg-violet-950/40 text-violet-200';
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
      className="rounded-xl border border-[#e8b86d]/30 bg-[#11131a] p-4 lg:col-span-2"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-[#e8b86d]">
          From this pack
        </h2>
        <button
          type="button"
          onClick={onExport}
          disabled={!canExport}
          className="inline-flex items-center gap-2 rounded-lg border border-[#e8b86d]/40 px-3 py-1.5 text-sm text-[#e8b86d] disabled:opacity-40"
        >
          <Download className="h-4 w-4" aria-hidden />
          Export pack
        </button>
      </div>
      {architecture ? (
        <div data-testid="pack-architecture" className="mt-4">
          <h3 className="text-[11px] uppercase tracking-[0.16em] text-white/35">Architecture</h3>
          {architecture.summary ? (
            <p className="mt-2 text-sm text-white/70">{architecture.summary}</p>
          ) : null}
          {architecture.stages.length > 0 ? (
            <ol className="mt-2 space-y-1 text-sm text-white/80">
              {architecture.stages.map((stage) => (
                <li key={stage.id}>
                  <span className="font-medium text-white">{stage.name}</span>
                  {stage.description ? ` — ${stage.description}` : ''}
                </li>
              ))}
            </ol>
          ) : null}
          {architecture.mermaid ? (
            <pre className="mt-2 overflow-auto rounded-lg bg-black/40 p-3 font-mono text-[11px] leading-5 text-white/65">
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
              className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm"
            >
              <div className="font-mono text-[12px] text-[#e8b86d]">{artifact.path_hint}</div>
              <div className="mt-1 text-white/80">{artifact.purpose}</div>
              <div className="mt-1 font-mono text-[11px] text-white/55">{artifact.interface}</div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export default function OneLoopStudio({
  showAgentWorkflowUi,
}: {
  showAgentWorkflowUi: boolean;
}) {
  const searchParams = useSearchParams();
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState('Paste a YouTube URL. Transcript and events land here.');
  const [actBusy, setActBusy] = useState(false);
  const [deployBusy, setDeployBusy] = useState(false);
  const [workflowActions, setWorkflowActions] = useState<VideoToActionsResult | null>(null);
  const [actRunId, setActRunId] = useState<string | null>(null);
  const [usedSameRun, setUsedSameRun] = useState(false);
  const [deployRunId, setDeployRunId] = useState<string | null>(null);
  const [deployReceiptUrl, setDeployReceiptUrl] = useState<string | null>(null);
  const [deployReceiptVideoId, setDeployReceiptVideoId] = useState<string | null>(null);
  const [gateReceipt, setGateReceipt] = useState<StudioGateReceiptView | null>(null);
  const [completedChecks, setCompletedChecks] = useState<string[]>([]);
  const [approvedSpecIds, setApprovedSpecIds] = useState<string[]>([]);
  const [openingPrs, setOpeningPrs] = useState(false);
  const [playerEpoch, setPlayerEpoch] = useState(0);
  const [exportToast, setExportToast] = useState<{ tone: 'success' | 'error'; text: string } | null>(
    null,
  );
  const autoStartedKey = useRef<string | null>(null);

  const processVideo = useDashboardStore((s) => s.processVideo);
  const selectVideo = useDashboardStore((s) => s.selectVideo);
  const updateVideo = useDashboardStore((s) => s.updateVideo);
  const selectedVideoId = useDashboardStore((s) => s.selectedVideoId);
  const videos = useDashboardStore((s) => s.videos);
  const selected = videos.find((v) => v.id === selectedVideoId);
  const scopedDeployReceipt = studioDeployReceiptForSelection({
    selectedVideoId,
    receiptVideoId: deployReceiptVideoId,
    liveUrl: deployReceiptUrl,
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

  const runAnalysis = async (raw: string) => {
    const handoff = resolveStudioHandoff(raw);
    if (!handoff) {
      setMessage('Need a valid YouTube URL.');
      return;
    }
    const next = handoff.watchUrl;
    setUrl(next);
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
      const id = await processVideo(next);
      selectVideo(id);
      const video = useDashboardStore.getState().videos.find((v) => v.id === id);
      const ready =
        (video?.transcript?.trim().length ?? 0) >= 40 || (video?.events?.length ?? 0) > 0;
      setMessage(
        studioPasteOutcomeMessage({
          hasUsableTranscript: ready,
          packCitation: video?.videoPack ? studioPackCitation(video.videoPack) : null,
        }),
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Analysis failed.');
    } finally {
      window.clearInterval(tick);
      setBusy(false);
    }
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
          window.location.href = `/login?callbackUrl=${encodeURIComponent(CANONICAL_STUDIO_PATH)}`;
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

  const exportPkg = () => {
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
      const pkg = buildScaffoldPackage({
        projectName: selected?.title || 'uvai-project',
        actions,
        projectScaffold: selected?.insights?.project_scaffold,
        linkedSop: linkedSop || undefined,
        packFormation: {
          architecture: packFormation.architecture,
          artifacts: packFormation.artifacts,
          tools: packFormation.tools,
        },
      });
      downloadScaffoldPackage(pkg);
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
    try {
      const started = await startStudioDeploy({
        url: next,
        transcript: usableProvidedTranscript(selected?.transcript),
      });
      if (started.status === 401 || started.status === 403) {
        window.location.href = `/login?callbackUrl=${encodeURIComponent(CANONICAL_STUDIO_PATH)}`;
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
      const backendReason = polled.error || polled.result?.message || null;
      const gated = evaluateStudioDeployTransition({
        transitionId: started.runId,
        runId: started.runId,
        jobId: polled.result?.jobId,
        liveUrl: polled.result?.live_url,
        runStatus: polled.runStatus,
        kind: polled.result?.kind,
        backendReason,
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
          error: polled.error,
          kind: polled.result?.kind,
          message: polled.result?.message,
          jobId: polled.result?.jobId,
          jobStatus: polled.result?.jobStatus,
        }),
      );
    } catch (err) {
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

  const transcriptStage = studioTranscriptStage({
    busy: transcriptWorking,
    elapsedSeconds: elapsed,
    progress: selected?.progress,
    hasPack: Boolean(selected?.videoPack),
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

  return (
    <div className="flex min-h-screen flex-col bg-[#0b0c10] text-[#f4f1ea]">
      <Nav
        rightSlot={
          <Link
            href={`/login?callbackUrl=${encodeURIComponent(CANONICAL_STUDIO_PATH)}`}
            className="rounded-full border border-white/15 px-4 py-1.5 text-sm text-white/80 hover:bg-white/5"
          >
            Sign in
          </Link>
        }
      />

      <header className="border-b border-white/10 bg-[#11131a]">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-5 sm:px-6">
          <div>
            <h1 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
              Paste a YouTube URL
            </h1>
            <p className="mt-1 text-sm text-white/55">
              Transcript, events, and tools stay on this page.
            </p>
          </div>
          <form onSubmit={analyze} className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
            <label className="sr-only" htmlFor="youtube-url">
              YouTube URL
            </label>
            <input
              id="youtube-url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={FIXTURE}
              autoComplete="off"
              className="min-w-0 flex-1 rounded-lg border border-white/15 bg-[#0b0c10] px-4 py-3 font-mono text-sm text-white outline-none focus:border-[#e8b86d]"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setUrl(FIXTURE)}
                className="rounded-lg border border-white/15 px-3 py-3 text-sm text-white/70 hover:bg-white/5"
              >
                Sample
              </button>
              <button
                type="submit"
                disabled={busy}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#e8b86d] px-5 py-3 text-sm font-semibold text-[#1a1408] disabled:opacity-50 sm:flex-none"
              >
                <Play className="h-4 w-4" aria-hidden />
                {busy ? `Running ${elapsed}s` : 'Run'}
              </button>
            </div>
          </form>
          <p className="font-mono text-xs text-[#e8b86d]/90" role="status">
            {statusText}
          </p>
          {gateReceipt ? (
            <div
              data-testid="studio-gate-receipt"
              role="status"
              className="mt-2 flex flex-wrap items-start gap-2 rounded-lg border border-white/10 bg-black/30 px-3 py-2"
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
                <p data-testid="studio-gate-reason" className="text-sm text-white/80">
                  {gateReceipt.reason}
                </p>
                {scopedDeployReceipt ? (
                  <p className="mt-1">
                    <a
                      data-testid="studio-gate-live-url"
                      href={scopedDeployReceipt}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="break-all text-sm text-[#e8b86d] underline"
                    >
                      {scopedDeployReceipt}
                    </a>
                  </p>
                ) : null}
                <p className="mt-1 break-all font-mono text-[11px] text-white/45">
                  <span data-testid="studio-gate-receipt-id">{gateReceipt.receiptId}</span>
                  {' · '}
                  <span data-testid="studio-gate-receipt-hash">{gateReceipt.receiptHash}</span>
                  {' · '}
                  {gateReceipt.version}
                </p>
              </div>
            </div>
          ) : null}
          {selected?.videoPack && (
            <p
              data-testid="video-pack-citation"
              className="break-all font-mono text-[11px] text-white/55"
            >
              {studioPackCitation(selected.videoPack)}
            </p>
          )}
          {transcriptWorking && (
            <div className="h-1 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full bg-[#e8b86d] transition-all"
                style={{ width: `${Math.min(95, selected?.progress || 8 + elapsed * 2)}%` }}
              />
            </div>
          )}
        </div>
      </header>

      <main
        data-testid="studio-main"
        className="mx-auto grid w-full max-w-6xl flex-1 gap-4 px-4 py-6 pb-28 sm:px-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]"
      >
        <section className="relative overflow-hidden rounded-xl border border-white/10 bg-black">
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
                  className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#14151c] px-6 text-center"
                >
                  <p className="text-sm text-white/80">{playerOverlay}</p>
                  {playerPhase === 'error' ? (
                    <div className="flex flex-wrap items-center justify-center gap-2">
                      <button
                        type="button"
                        data-testid="studio-player-retry"
                        onClick={() => setPlayerEpoch((epoch) => epoch + 1)}
                        className="rounded-lg border border-[#e8b86d]/40 px-3 py-1.5 text-sm text-[#e8b86d]"
                      >
                        Retry player
                      </button>
                      <a
                        href={`https://www.youtube.com/watch?v=${videoId}`}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-white/70"
                      >
                        Open on YouTube
                      </a>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </>
          ) : (
            <div className="flex aspect-video items-center justify-center bg-[#14151c] px-6 text-center text-sm text-white/40">
              Paste a link. The video plays here while we pull the transcript.
            </div>
          )}
        </section>

        <section className="flex min-h-[280px] flex-col rounded-xl border border-white/10 bg-[#11131a]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
              Transcript
            </h2>
            {selected?.transcript ? (
              <span className="font-mono text-[11px] text-white/35">
                {selected.transcript.trim().split(/\s+/).length} words
              </span>
            ) : null}
          </div>
          {(transcriptStage.id !== 'idle' || showTranscriptRetry) && (
            <div
              data-testid="studio-transcript-stage"
              className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-4 py-2"
            >
              <div>
                <p className="text-sm text-white/80">{transcriptStage.label}</p>
                {transcriptWorking && !selected?.transcript && (
                  <p className="font-mono text-[11px] text-white/40">
                    {studioTranscriptEtaLabel(elapsed)}
                  </p>
                )}
              </div>
              {showTranscriptRetry ? (
                <button
                  type="button"
                  data-testid="studio-transcript-retry"
                  onClick={() => void runAnalysis(url || selected?.url || '')}
                  className="rounded-lg border border-[#e8b86d]/40 px-3 py-1.5 text-sm text-[#e8b86d]"
                >
                  Retry transcript
                </button>
              ) : null}
            </div>
          )}
          <div className="max-h-[420px] flex-1 overflow-auto px-4 py-3 text-sm leading-6 text-white/80">
            {selected?.transcript?.trim() ||
              (transcriptWorking
                ? 'Waiting on captions — no invented text.'
                : selected?.status === 'failed'
                  ? selected.failure?.message || 'Transcript failed.'
                  : 'Nothing yet.')}
          </div>
        </section>

        {promotePack ? (
          <PackWorkbench
            architecture={packFormation.architecture}
            artifacts={packFormation.artifacts}
            onExport={exportPkg}
            canExport={hasPayload}
          />
        ) : null}

        <section className="rounded-xl border border-white/10 bg-[#11131a] lg:col-span-2">
          <div className="border-b border-white/10 px-4 py-3">
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
              Events
            </h2>
          </div>
          <ul className="divide-y divide-white/5">
            {(selected?.events || []).length === 0 && (
              <li data-testid="studio-events-empty" className="px-4 py-4 text-sm text-white/40">
                {studioEventsEmptyMessage({
                  busy: busy || selected?.status === 'processing',
                  hasCompletedRun: selected != null && selected.status !== 'processing' && !busy,
                  eventCount: 0,
                  hasTranscript: Boolean(selected?.transcript?.trim()),
                  hasArchitecture: Boolean(packFormation.architecture),
                  artifactCount: packFormation.artifacts.length,
                  toolCount: packFormation.tools.length,
                })}
              </li>
            )}
            {(selected?.events || []).map((event) => {
              const seconds = parseTimestampToSeconds(event.timestamp);
              return (
              <li key={event.id} className="grid gap-1 px-4 py-3 sm:grid-cols-[7rem_1fr]">
                {seconds != null ? (
                  <button
                    type="button"
                    onClick={() => seekTo(seconds)}
                    className="text-left font-mono text-[11px] uppercase tracking-wider text-[#e8b86d]"
                  >
                    {formatSeconds(seconds)}
                  </button>
                ) : (
                  <div className="font-mono text-[11px] uppercase tracking-wider text-[#e8b86d]">
                    {event.type}
                  </div>
                )}
                <div>
                  <div className="text-sm font-medium text-white">{event.title}</div>
                  {event.description && (
                    <div className="mt-0.5 text-sm text-white/55">{event.description}</div>
                  )}
                </div>
              </li>
              );
            })}
          </ul>
        </section>

        {linkedSop && (linkedSop.entities.length > 0 || linkedSop.steps.length > 0 || packFormation.tools.length > 0) && (
          <section className="rounded-xl border border-white/10 bg-[#11131a] lg:col-span-2">
            <div className="border-b border-white/10 px-4 py-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
                Named tools
              </h2>
            </div>
            <div className="flex flex-wrap gap-2 px-4 py-3">
              {supplementalEntities.length === 0 && packFormation.tools.length === 0 && (
                <p className="text-sm text-white/40">No catalogued tools in this transcript.</p>
              )}
              {packFormation.tools.map((tool) => (
                <span
                  key={`pack-${tool.name}`}
                  className="inline-flex items-center gap-2 rounded-full border border-[#e8b86d]/30 bg-[#e8b86d]/10 px-3 py-1.5 text-sm"
                >
                  <span className="font-medium text-white">{tool.name}</span>
                </span>
              ))}
              {supplementalEntities.map((entity) => (
                <span
                  key={entity.name}
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-sm"
                >
                  <a
                    href={entity.officialUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-white hover:text-[#e8b86d]"
                  >
                    {entity.name}
                  </a>
                  {entity.docsUrl && entity.docsUrl !== entity.officialUrl && (
                    <a
                      href={entity.docsUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[11px] uppercase tracking-wider text-white/45 hover:text-[#e8b86d]"
                    >
                      docs
                    </a>
                  )}
                  {entity.timestamps[0] != null && (
                    <button
                      type="button"
                      onClick={() => seekTo(entity.timestamps[0])}
                      className="font-mono text-[11px] text-[#e8b86d]"
                    >
                      {formatSeconds(entity.timestamps[0])}
                    </button>
                  )}
                </span>
              ))}
            </div>

            <div className="border-t border-white/10 px-4 py-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
                SOP
              </h2>
            </div>
            <ol className="divide-y divide-white/5">
              {linkedSop.steps.length === 0 && (
                <li className="px-4 py-3 text-sm text-white/40">No ordered SOP in this run.</li>
              )}
              {linkedSop.steps.map((step) => {
                const approved = approvedSpecIds.includes(step.id);
                return (
                <li key={step.id} className="grid gap-1 px-4 py-3 sm:grid-cols-[7rem_1fr]">
                  {step.timestamp != null ? (
                    <button
                      type="button"
                      onClick={() => seekTo(step.timestamp!)}
                      className="text-left font-mono text-[11px] text-[#e8b86d]"
                    >
                      {formatSeconds(step.timestamp)}
                    </button>
                  ) : (
                    <div className="font-mono text-[11px] text-white/35">{step.order}</div>
                  )}
                  <div>
                    <label className="mb-1 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.12em] text-white/45">
                      <input
                        type="checkbox"
                        checked={approved}
                        onChange={() =>
                          setApprovedSpecIds((current) =>
                            current.includes(step.id)
                              ? current.filter((id) => id !== step.id)
                              : [...current, step.id],
                          )
                        }
                        className="h-3.5 w-3.5 accent-[#e8b86d]"
                      />
                      Approved for PR
                    </label>
                    <div className="text-sm font-medium text-white">{step.title}</div>
                    {step.description && (
                      <div className="mt-0.5 text-sm text-white/55">{step.description}</div>
                    )}
                  </div>
                </li>
                );
              })}
            </ol>

            {stackChecks.length > 0 && (
              <>
                <div className="border-t border-white/10 px-4 py-3">
                  <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
                    Stack checks
                  </h2>
                </div>
                <ul className="divide-y divide-white/5">
                  {stackChecks.map((item) => {
                      const checked = completedChecks.includes(item.id);
                      const status = stackCheckStatus(item, completedChecks, 'anonymous');
                      return (
                      <li key={item.id} className="flex items-start gap-3 px-4 py-3 text-sm">
                        <input
                          id={`check-${item.id}`}
                          type="checkbox"
                          checked={checked}
                          onChange={() => {
                            setCompletedChecks((current) =>
                              current.includes(item.id)
                                ? current.filter((id) => id !== item.id)
                                : [...current, item.id],
                            );
                          }}
                          className="mt-1 h-4 w-4 accent-[#e8b86d]"
                        />
                        <label htmlFor={`check-${item.id}`} className="min-w-0 flex-1">
                          {item.href ? (
                            <a
                              href={item.href}
                              target="_blank"
                              rel="noreferrer"
                              className="text-white hover:text-[#e8b86d]"
                            >
                              {item.title}
                            </a>
                          ) : (
                            <span className="text-white">{item.title}</span>
                          )}
                          <div className="mt-0.5 text-[11px] uppercase tracking-[0.12em] text-white/40">
                            {stackCheckStatusLabel(status)}
                          </div>
                        </label>
                      </li>
                      );
                    })}
                </ul>
              </>
            )}
          </section>
        )}

        {selected?.videoPack && (
          <section
            data-testid="video-pack"
            className="rounded-xl border border-white/10 bg-[#11131a] p-4 lg:col-span-2"
          >
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
              Video pack
            </h2>
            <p className="mt-3 break-all font-mono text-sm text-white/80">
              {studioPackCitation(selected.videoPack)}
            </p>
            <dl className="mt-3 grid gap-2 font-mono text-[11px] text-white/55 sm:grid-cols-2">
              <div>
                <dt className="uppercase tracking-[0.16em] text-white/35">source_url</dt>
                <dd className="mt-1 break-all text-white/80">{selected.videoPack.sourceUrl}</dd>
              </div>
              <div>
                <dt className="uppercase tracking-[0.16em] text-white/35">source_hash</dt>
                <dd className="mt-1 break-all text-white/80">{selected.videoPack.sourceHash}</dd>
              </div>
            </dl>
            {!promotePack && packFormation.architecture && (
              <div data-testid="pack-architecture" className="mt-4">
                <h3 className="text-[11px] uppercase tracking-[0.16em] text-white/35">
                  Architecture
                </h3>
                {packFormation.architecture.summary && (
                  <p className="mt-2 text-sm text-white/70">{packFormation.architecture.summary}</p>
                )}
                {packFormation.architecture.stages.length > 0 && (
                  <ol className="mt-2 space-y-1 text-sm text-white/80">
                    {packFormation.architecture.stages.map((stage) => (
                      <li key={stage.id}>
                        <span className="font-medium text-white">{stage.name}</span>
                        {stage.description ? ` — ${stage.description}` : ''}
                      </li>
                    ))}
                  </ol>
                )}
                {packFormation.architecture.mermaid && (
                  <pre className="mt-2 overflow-auto rounded-lg bg-black/40 p-3 font-mono text-[11px] leading-5 text-white/65">
                    {packFormation.architecture.mermaid}
                  </pre>
                )}
              </div>
            )}
            {!promotePack && packFormation.artifacts.length > 0 && (
              <ul data-testid="pack-artifacts" className="mt-4 space-y-2">
                {packFormation.artifacts.map((artifact) => (
                  <li
                    key={artifact.path_hint}
                    className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm"
                  >
                    <div className="font-mono text-[12px] text-[#e8b86d]">{artifact.path_hint}</div>
                    <div className="mt-1 text-white/80">{artifact.purpose}</div>
                    <div className="mt-1 font-mono text-[11px] text-white/55">{artifact.interface}</div>
                  </li>
                ))}
              </ul>
            )}
            <pre
              data-testid="video-pack-json"
              className="mt-3 overflow-auto rounded-lg bg-black/40 p-3 font-mono text-[11px] leading-5 text-white/75"
            >
              {identityPackJson(selected.videoPack)}
            </pre>
          </section>
        )}

        {selected?.insights && (
          <section className="rounded-xl border border-white/10 bg-[#11131a] p-4 lg:col-span-2">
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
              Summary
            </h2>
            <p className="mt-3 text-sm leading-6 text-white/80">{selected.insights.summary}</p>
          </section>
        )}

        {showAgentWorkflowUi && (actRunId || workflowActions) && (
          <section
            id="act-results"
            data-testid="act-results"
            className="rounded-xl border border-[#e8b86d]/30 bg-[#e8b86d]/5 p-4 lg:col-span-2"
          >
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-[#e8b86d]">
              Tool results
            </h2>
            {actRunId && (
              <p className="mt-2 font-mono text-[11px] text-white/40">
                {actRunId}
                {usedSameRun ? ' · this transcript' : ''}
              </p>
            )}
            {workflowActions ? (
              <ul className="mt-3 space-y-2 text-sm">
                {workflowActions.actions.length === 0 && (
                  <li className="text-white/50">No tool results from this run.</li>
                )}
                {workflowActions.actions.map((action, i) => {
                  const card = studioActionCard(action);
                  return (
                    <li
                      key={`${action.tool}-${i}`}
                      data-testid="studio-action-card"
                      className="rounded-lg border border-white/10 bg-black/20 px-3 py-2"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium text-white">{card.title}</span>
                        <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#e8b86d]">
                          {card.statusLabel}
                        </span>
                      </div>
                      <p className="mt-1 text-white/70">{card.detail}</p>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-white/60">
                {actBusy ? 'Running tools…' : 'Waiting for tool results.'}
              </p>
            )}
          </section>
        )}
      </main>

      {exportToast ? (
        <div
          data-testid="studio-export-toast"
          role={exportToast.tone === 'error' ? 'alert' : 'status'}
          className={clsx(
            'fixed bottom-20 left-1/2 z-40 w-[min(36rem,calc(100%-2rem))] -translate-x-1/2 rounded-lg border px-4 py-3 text-sm shadow-lg',
            exportToast.tone === 'success'
              ? 'border-[#e8b86d]/40 bg-[#1a1408] text-[#e8b86d]'
              : 'border-red-400/40 bg-[#2a1212] text-red-100',
          )}
        >
          {exportToast.text}
        </div>
      ) : null}

      <footer className="sticky bottom-0 border-t border-white/10 bg-[#11131a]/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3 sm:px-6">
          {showAgentWorkflowUi && (
            <button
              type="button"
              onClick={() => void act()}
              disabled={actBusy || !hasPayload}
              className="inline-flex items-center gap-2 rounded-lg bg-[#e8b86d] px-4 py-2 text-sm font-semibold text-[#1a1408] disabled:opacity-40"
            >
              {actBusy ? 'Running tools…' : 'Run tools'}
            </button>
          )}
          <button
            type="button"
            onClick={exportPkg}
            disabled={!hasPayload}
            className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm disabled:opacity-40"
          >
            <Download className="h-4 w-4" aria-hidden />
            {promotePack ? 'Export pack' : 'Export'}
          </button>
          <button
            type="button"
            data-testid="studio-deploy-button"
            onClick={() => void deploy()}
            disabled={deployBusy || !hasPayload || Boolean(holdReason)}
            title={holdReason || studioDeployEnabledHint(Boolean(scopedDeployReceipt))}
            className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm disabled:opacity-40"
          >
            <Rocket className="h-4 w-4" aria-hidden />
            {deployBusy ? 'Attempting deploy…' : studioDeployButtonLabel(Boolean(scopedDeployReceipt))}
          </button>
          <button
            type="button"
            data-testid="studio-open-prs-button"
            onClick={() => void openApprovedSpecsPrs()}
            disabled={openingPrs || approvedSpecIds.length === 0}
            title={approvedSpecIds.length === 0 ? 'Approve at least one SOP spec first.' : undefined}
            className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm disabled:opacity-40"
          >
            <GitPullRequest className="h-4 w-4" aria-hidden />
            {openingPrs ? 'Opening PRs…' : `Open GitHub PRs (${approvedSpecIds.length})`}
          </button>
          {holdReason && (
            <p className="basis-full text-xs text-[#e8b86d] sm:basis-auto sm:max-w-xl">
              {holdReason}
            </p>
          )}
        </div>
      </footer>
    </div>
  );
}
