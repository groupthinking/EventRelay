'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  Check,
  CheckCircle2,
  Copy,
  Download,
  ExternalLink,
  FileCode2,
  Layers,
  Play,
  Rocket,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Video as VideoIcon,
} from 'lucide-react';
import { formatSeconds, parseTimestampToSeconds, parseTranscriptSegments } from '@/lib/timestamp';
import { compileLinkedSop, type LinkedSop } from '@/lib/linked-sop';
import { deployHoldReason, pickOfficialTemplate } from '@/lib/official-templates';
import { clsx } from 'clsx';
import Nav from '@/components/Nav';
import { useDashboardStore } from '@/store/dashboard-store';
import {
  actionsFromStudioRun,
  buildScaffoldPackage,
  downloadScaffoldPackage,
} from '@/lib/action-surface';
import {
  pollStudioDeploy,
  pollVideoToActions,
  startStudioDeploy,
  startVideoToActions,
  type VideoToActionsResult,
} from '@/lib/studio-workflow';
import {
  studioRunQuality,
  studioStatusLabel,
  studioStatusMessage,
} from '@/lib/studio-pipeline-status';
import { buildSameRunActInput, MIN_ACT_TRANSCRIPT_CHARS } from '@/lib/video-to-actions-input';
import { VERIFIED_BENCHMARKS, getBenchmarkByYoutubeId } from '@/lib/verified-benchmarks';
import type { ExtractedEvent } from '@/lib/types';

const FIXTURE = 'https://www.youtube.com/watch?v=auJzb1D-fag';

type MainTab = 'plan' | 'canvas' | 'trust';

const PRESET_LABELS: Record<string, string> = {
  'multi-agent-ops': 'AI Agent Operations',
  'nextjs-stripe-launch': 'Next.js + Stripe SaaS',
  'fastapi-rag-pipeline': 'FastAPI RAG Pipeline',
};

function isValidYouTubeId(id: string) {
  return /^[A-Za-z0-9_-]{11}$/.test(id);
}

function getYouTubeId(url: string) {
  const match = url.match(
    /(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=|shorts\/))([^&?/]+)/,
  );
  const candidate = match?.[1] || '';
  return isValidYouTubeId(candidate) ? candidate : '';
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

export default function OneLoopStudio() {
  const searchParams = useSearchParams();
  const [activeBenchmarkId, setActiveBenchmarkId] = useState<string>(VERIFIED_BENCHMARKS[0].id);
  const [url, setUrl] = useState(FIXTURE);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState(
    'Ready — watch the video above, click any chapter timestamp, or paste your own YouTube link.',
  );
  const [actBusy, setActBusy] = useState(false);
  const [deployBusy, setDeployBusy] = useState(false);
  const [workflowActions, setWorkflowActions] = useState<VideoToActionsResult | null>(null);
  const [actRunId, setActRunId] = useState<string | null>(null);
  const [usedSameRun, setUsedSameRun] = useState(false);
  const [deployRunId, setDeployRunId] = useState<string | null>(null);
  const [seekSeconds, setSeekSeconds] = useState<number | null>(null);
  const [completedChecks, setCompletedChecks] = useState<string[]>([]);
  const [mainTab, setMainTab] = useState<MainTab>('plan');
  const [transcriptQuery, setTranscriptQuery] = useState('');
  const [selectedArtifactFile, setSelectedArtifactFile] = useState<string>('DEPLOY.md');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const processVideo = useDashboardStore((s) => s.processVideo);
  const selectVideo = useDashboardStore((s) => s.selectVideo);
  const updateVideo = useDashboardStore((s) => s.updateVideo);
  const selectedVideoId = useDashboardStore((s) => s.selectedVideoId);
  const videos = useDashboardStore((s) => s.videos);
  const selected = videos.find((v) => v.id === selectedVideoId);

  const activeBenchmark = useMemo(() => {
    const byId = VERIFIED_BENCHMARKS.find((b) => b.id === activeBenchmarkId);
    if (byId) return byId;
    const urlYtId = getYouTubeId(url);
    return (urlYtId ? getBenchmarkByYoutubeId(urlYtId) : undefined) || VERIFIED_BENCHMARKS[0];
  }, [activeBenchmarkId, url]);

  const isLiveStoreRun = Boolean(
    selected && ((selected.transcript?.trim().length ?? 0) >= 40 || (selected.events?.length ?? 0) > 0),
  );

  const activeTitle = isLiveStoreRun ? selected!.title : activeBenchmark.title;
  const activeTranscript = isLiveStoreRun ? selected!.transcript || '' : activeBenchmark.transcript;
  const activeEvents = useMemo(
    () => (isLiveStoreRun ? selected!.events || [] : activeBenchmark.events),
    [isLiveStoreRun, selected, activeBenchmark.events],
  );
  const activeSummary = isLiveStoreRun
    ? selected?.insights?.summary || activeBenchmark.summary
    : activeBenchmark.summary;
  const activeTopics = isLiveStoreRun
    ? selected?.insights?.topics || activeBenchmark.topics
    : activeBenchmark.topics;
  const activeProvenance =
    isLiveStoreRun && selected?.provenance ? selected.provenance : activeBenchmark.provenance;
  const activeQuality =
    isLiveStoreRun && selected?.quality ? selected.quality : activeBenchmark.quality;

  const linkedSop: LinkedSop | null = useMemo(() => {
    if (isLiveStoreRun) {
      if (selected?.insights?.linkedSop) return selected.insights.linkedSop;
      if (!selected?.transcript && !(selected?.events?.length)) return null;
      const insightActions = (selected?.insights?.actions || []).flatMap((action) => {
        if (typeof action === 'string') {
          return action.trim() ? [{ title: action.trim() }] : [];
        }
        return action.title?.trim()
          ? [{ title: action.title, description: action.description, category: action.category }]
          : [];
      });
      return compileLinkedSop({
        title: selected?.title,
        summary: selected?.insights?.summary,
        transcript: selected?.transcript,
        events: (selected?.events || []).map((event) => ({
          timestamp: parseTimestampToSeconds(event.timestamp) ?? undefined,
          label: event.title,
          description: event.description,
        })),
        actions: insightActions,
        topics: selected?.insights?.topics,
      });
    }
    return activeBenchmark.linkedSop;
  }, [isLiveStoreRun, selected, activeBenchmark]);

  useEffect(() => {
    setCompletedChecks([]);
  }, [selectedVideoId, activeBenchmarkId]);

  const holdReason = deployHoldReason(linkedSop, completedChecks);
  const officialTemplate = pickOfficialTemplate(linkedSop);

  useEffect(() => {
    useDashboardStore.persist.rehydrate();
  }, []);

  useEffect(() => {
    const q = searchParams.get('video') || searchParams.get('url');
    if (q) {
      setUrl(q);
      const ytId = getYouTubeId(q);
      const matched = ytId ? getBenchmarkByYoutubeId(ytId) : undefined;
      if (matched) setActiveBenchmarkId(matched.id);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!busy) {
      setElapsed(0);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 250);
    return () => window.clearInterval(timer);
  }, [busy]);

  const videoId = useMemo(
    () => getYouTubeId(url) || activeBenchmark.youtubeId,
    [url, activeBenchmark.youtubeId],
  );

  const hasPayload = activeTranscript.trim().length >= 40 || activeEvents.length > 0;
  const runState = busy ? 'working' : hasPayload ? 'ready' : 'idle';
  const quality = studioRunQuality(
    selected?.jobId
      ? { ok: true, status: 200, jobId: selected.jobId }
      : { ok: true, status: 200, pipeline: 'backend' },
    false,
    Boolean(videoId || selected),
    { transcript: activeTranscript, eventCount: activeEvents.length },
  );

  const parsedTranscript = useMemo(
    () => parseTranscriptSegments(activeTranscript),
    [activeTranscript],
  );

  const filteredSegments = useMemo(() => {
    const q = transcriptQuery.trim().toLowerCase();
    const base: Array<{ start: number; duration: number; text: string }> =
      parsedTranscript.segments.length > 0
        ? parsedTranscript.segments.map((s) => ({
            start: s.startTime,
            duration: Math.max(1, s.endTime - s.startTime),
            text: s.text,
          }))
        : activeBenchmark.segments;
    if (!q) return base;
    return base.filter((seg) => seg.text.toLowerCase().includes(q));
  }, [parsedTranscript.segments, activeBenchmark.segments, transcriptQuery]);

  const previewPackage = useMemo(() => {
    const insightActions = (selected?.insights?.actions || []).flatMap((action) => {
      if (typeof action === 'string') {
        return action.trim() ? [{ title: action.trim() }] : [];
      }
      return action.title?.trim() ? [action] : [];
    });
    const actions = actionsFromStudioRun({
      insightActions,
      events: activeEvents,
      workflowActions: workflowActions?.actions,
    });
    return buildScaffoldPackage({
      projectName: activeTitle || 'uvai-project',
      actions,
      projectScaffold: selected?.insights?.project_scaffold,
      linkedSop: linkedSop || undefined,
    });
  }, [selected, activeEvents, workflowActions, activeTitle, linkedSop]);

  const previewFileNames = useMemo(() => Object.keys(previewPackage.files), [previewPackage.files]);

  useEffect(() => {
    if (!previewFileNames.includes(selectedArtifactFile) && previewFileNames.length > 0) {
      setSelectedArtifactFile(
        previewFileNames.includes('DEPLOY.md') ? 'DEPLOY.md' : previewFileNames[0],
      );
    }
  }, [previewFileNames, selectedArtifactFile]);

  const copyText = (key: string, value: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(value);
      setCopiedKey(key);
      window.setTimeout(() => setCopiedKey((curr) => (curr === key ? null : curr)), 1800);
    }
  };

  const selectBenchmark = (benchmarkId: string) => {
    const found = VERIFIED_BENCHMARKS.find((b) => b.id === benchmarkId);
    if (!found) return;
    selectVideo(null);
    setActiveBenchmarkId(found.id);
    setUrl(found.url);
    setSeekSeconds(null);
    setWorkflowActions(null);
    setActRunId(null);
    setMessage(`Now playing: ${found.title}`);
  };

  const analyze = async (event?: FormEvent) => {
    event?.preventDefault();
    const next = url.trim();
    if (!getYouTubeId(next)) {
      setMessage('Please enter a valid YouTube URL.');
      return;
    }
    setBusy(true);
    setWorkflowActions(null);
    setActRunId(null);
    setUsedSameRun(false);
    setMessage('Loading video and extracting action plan…');
    const tick = window.setInterval(() => {
      const id = getYouTubeId(next);
      const matches = useDashboardStore
        .getState()
        .videos.filter((v) => v.url === next || (id !== '' && v.url.includes(id)));
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
        ready
          ? 'Ready — explore the action plan below, run tools, or export your project.'
          : 'Live backend unavailable — showing verified video.',
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Analysis failed.');
    } finally {
      window.clearInterval(tick);
      setBusy(false);
    }
  };

  const act = async () => {
    const next = (selected?.url || url).trim();
    if (!getYouTubeId(next)) {
      setMessage('Analyze a video before running tools.');
      return;
    }
    setActBusy(true);
    setWorkflowActions(null);
    setActRunId(null);
    setMessage("Running agent tools on this video's transcript…");
    try {
      let events = activeEvents;
      const transcript = activeTranscript.trim();
      if (selected && transcript.length >= MIN_ACT_TRANSCRIPT_CHARS && !(events?.length)) {
        try {
          const enriched = await tryExtractEvents({
            transcript,
            videoTitle: activeTitle,
            videoUrl: next,
            videoId: selected.id,
          });
          if (enriched) {
            updateVideo(selected.id, { events: enriched });
            events = enriched;
          }
        } catch {
          // extract-events is optional
        }
      }

      const sopEvents = (linkedSop?.steps || []).map((step) => ({
        type: 'action',
        title: step.title,
        description: step.description,
      }));
      const payload = buildSameRunActInput({
        url: next,
        videoTitle: activeTitle,
        transcript: activeTranscript,
        events: [...(events || []), ...sopEvents],
      });
      setUsedSameRun(Boolean(payload.transcript || payload.events?.length));

      const started = await startVideoToActions(payload);
      if (!started.ok || !started.runId) {
        if (started.status === 401 || started.status === 403) {
          window.location.href = `/login?callbackUrl=${encodeURIComponent('/')}`;
          return;
        }
        setMessage(started.error || started.message || 'Could not start agent tools.');
        return;
      }
      setActRunId(started.runId);
      setMessage(`Agent run ${started.runId} started…`);
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
        setMessage(`Completed — ${polled.result.actionCount} tool result(s) ready.`);
      } else {
        setMessage(polled.error || `Run status: ${polled.runStatus || 'unknown'}.`);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Agent run failed.');
    } finally {
      setActBusy(false);
    }
  };

  const exportPkg = () => {
    if (!hasPayload && !linkedSop?.steps.length) {
      setMessage('Analyze a video before exporting.');
      return;
    }
    downloadScaffoldPackage(previewPackage);
    setMessage(
      officialTemplate
        ? `Exported ${officialTemplate.clone} + SOP and DEPLOY.md (${previewFileNames.length} files).`
        : 'Exported project package (.zip).',
    );
  };

  const deploy = async () => {
    const next = (selected?.url || url).trim();
    if (!getYouTubeId(next)) {
      setMessage('Analyze a video before deploying.');
      return;
    }
    if (holdReason) {
      setMainTab('trust');
      setMessage(holdReason);
      return;
    }
    setDeployBusy(true);
    try {
      const started = await startStudioDeploy({ url: next });
      if (started.status === 401 || started.status === 403) {
        window.location.href = `/login?callbackUrl=${encodeURIComponent('/')}`;
        return;
      }
      if (!started.ok || !started.runId) {
        setMessage(started.error || 'Deploy requires sign-in.');
        return;
      }
      setDeployRunId(started.runId);
      const polled = await pollStudioDeploy(started.runId, { attempts: 20, delayMs: 2000 });
      if (polled.result?.live_url) {
        setMessage(`Deploy ready: ${polled.result.live_url}`);
      } else {
        setMessage(polled.error || `Deploy ${polled.runStatus || 'started'}.`);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Deploy failed.');
    } finally {
      setDeployBusy(false);
    }
  };

  const statusText = busy
    ? `Loading (${elapsed}s) — ${message}`
    : `${studioStatusLabel(quality, runState)} — ${message || studioStatusMessage(quality, runState, 'Analysis', false)}`;

  const wordCount = useMemo(
    () => (activeTranscript.trim() ? activeTranscript.trim().split(/\s+/).length : 0),
    [activeTranscript],
  );

  const stackItems = useMemo(
    () => (linkedSop?.checklist || []).filter((item) => item.source === 'stack'),
    [linkedSop],
  );

  return (
    <div className="flex min-h-screen flex-col bg-[#f5f1e8] text-[#171716]">
      <Nav
        rightSlot={
          <div className="flex items-center gap-2.5">
            <Link
              href="/dashboard"
              className="hidden sm:inline-flex items-center gap-2 rounded-xl border border-[#d8d0c0] bg-white px-4 py-2 text-sm font-semibold text-[#171716] shadow-xs hover:bg-[#faf8f3]"
            >
              <Save className="h-4 w-4 text-[#ff5500]" aria-hidden />
              Library
            </Link>
            <Link
              href={`/login?callbackUrl=${encodeURIComponent('/')}`}
              className="rounded-xl bg-[#171716] px-4 py-2 text-sm font-semibold text-[#f5f1e8] hover:bg-[#2b2b29]"
            >
              Sign in
            </Link>
          </div>
        }
      />

      {/* ── Top Search Bar & Cinema Video Stage (Video.js v10 + LinkedIn Learning Pattern) ── */}
      <section className="border-b border-[#e4decb] bg-[#f5f1e8] pt-6 pb-10">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          {/* Compact Search & URL Bar Directly Above the Main Video Player */}
          <div className="mx-auto max-w-4xl">
            <div className="text-center">
              <h1 className="font-heading text-3xl font-black tracking-tight text-[#171716] sm:text-4xl">
                Turn any video into actions.
              </h1>
            </div>

            <form onSubmit={analyze} className="mt-4">
              <label className="sr-only" htmlFor="youtube-url">
                YouTube URL
              </label>
              <div className="flex flex-col gap-2 rounded-2xl border-2 border-[#171716]/15 bg-white p-2 shadow-md focus-within:border-[#171716] transition-colors sm:flex-row sm:items-center">
                <div className="flex flex-1 items-center gap-3 px-3">
                  <Search className="h-5 w-5 shrink-0 text-[#78746c]" aria-hidden />
                  <input
                    id="youtube-url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="Paste any YouTube URL to load the video, transcript, and action plan…"
                    autoComplete="off"
                    className="min-w-0 flex-1 bg-transparent py-2 text-base font-medium text-[#171716] outline-none placeholder:text-[#8c877e]"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => selectBenchmark(VERIFIED_BENCHMARKS[0].id)}
                    className="rounded-xl border border-[#dcd5c6] bg-[#f7f4ec] px-4 py-2.5 text-sm font-semibold text-[#3d3b37] hover:bg-[#ece6d8]"
                  >
                    Sample
                  </button>
                  <button
                    type="submit"
                    disabled={busy}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-[#ff5500] px-6 py-2.5 text-sm font-bold text-white shadow-xs transition-colors hover:bg-[#e04b00] disabled:opacity-50 sm:flex-none"
                  >
                    <Play className="h-4 w-4 fill-current" aria-hidden />
                    {busy ? `Loading ${elapsed}s` : 'Analyze a video'}
                  </button>
                </div>
              </div>
            </form>

            <p className="mt-2.5 text-center text-xs font-medium text-[#57554f]" role="status">
              {statusText}
            </p>
          </div>

          {/* ── CENTERPIECE: Full-Width 16:9 Cinema Video Player ── */}
          <div className="mt-6 overflow-hidden rounded-3xl border-4 border-[#171716] bg-[#141413] shadow-[0_28px_60px_-15px_rgba(23,23,22,0.3)]">
            {videoId ? (
              <iframe
                title="YouTube source"
                className="aspect-video w-full bg-black"
                src={
                  seekSeconds != null
                    ? `https://www.youtube.com/embed/${videoId}?start=${seekSeconds}&autoplay=1`
                    : `https://www.youtube.com/embed/${videoId}`
                }
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            ) : (
              <div className="flex aspect-video items-center justify-center bg-[#141413] px-6 text-center text-base text-white/70">
                Paste a YouTube link above to start watching.
              </div>
            )}

            {/* Player Chapter Scrubber Bar (Attached to bottom of cinema player) */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 bg-[#171716] px-5 py-3 text-white">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[#ff7733]">
                  Chapters:
                </span>
                {(linkedSop?.steps || []).slice(0, 6).map((step) => {
                  const ts = step.timestamp ?? 0;
                  const active = seekSeconds != null && Math.abs(seekSeconds - ts) < 5;
                  return (
                    <button
                      key={step.id}
                      type="button"
                      onClick={() => setSeekSeconds(ts)}
                      className={clsx(
                        'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors',
                        active
                          ? 'bg-[#ff5500] text-white font-semibold'
                          : 'bg-white/10 text-white/85 hover:bg-white/20',
                      )}
                    >
                      <span className="font-mono font-bold">
                        {step.timestamp != null ? formatSeconds(step.timestamp) : `Step ${step.order}`}
                      </span>
                      <span className="truncate max-w-[160px]">{step.title}</span>
                    </button>
                  );
                })}
              </div>

              <div className="text-xs font-medium text-white/60">
                Sponsored & Grounded by UVAI Video Engine
              </div>
            </div>
          </div>

          {/* ── Familiar 3-Video Course / Playlist Picker Directly Under Player ── */}
          <div className="mt-6">
            <div className="mb-2.5 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#57554f]">
                Featured Verified Videos — Click to Watch & Inspect
              </span>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {VERIFIED_BENCHMARKS.map((bench) => {
                const isSelected = !isLiveStoreRun && activeBenchmark.id === bench.id;
                return (
                  <button
                    key={bench.id}
                    type="button"
                    onClick={() => selectBenchmark(bench.id)}
                    className={clsx(
                      'flex items-center gap-3.5 rounded-2xl border p-3.5 text-left transition-all',
                      isSelected
                        ? 'border-[#171716] bg-white shadow-sm ring-1 ring-[#171716]'
                        : 'border-[#ded7c8] bg-[#faf7f0] hover:border-[#b8b0a0] hover:bg-white',
                    )}
                  >
                    <div
                      className={clsx(
                        'flex h-11 w-14 shrink-0 items-center justify-center rounded-xl font-mono text-xs font-bold',
                        isSelected
                          ? 'bg-[#ff5500] text-white'
                          : 'bg-[#171716] text-[#f5f1e8]',
                      )}
                    >
                      {bench.durationLabel}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-bold text-[#171716]">
                        {PRESET_LABELS[bench.id] || bench.category}
                      </div>
                      <div className="mt-0.5 truncate text-xs text-[#57554f]">
                        {bench.title}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ── Below the Player: Standard 2-Column Media Layout (Main Content + Transcript Sidebar) ── */}
      <main className="mx-auto grid w-full max-w-6xl flex-1 gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)] lg:items-start lg:px-8">
        {/* ── Left Main Column: Video Overview, Action Plan, Code & Checklist ── */}
        <div className="flex flex-col gap-6">
          {/* Video Title, Overview & Action Bar Card */}
          <section className="rounded-2xl border border-[#e2dbcc] bg-white p-6 shadow-xs">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-800">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" aria-hidden />
                  <span>Verified Video Breakdown</span>
                </div>
                <h2 className="mt-2 font-heading text-2xl font-black text-[#171716]">
                  {activeTitle}
                </h2>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => void act()}
                  disabled={actBusy || !hasPayload}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#ff5500] px-5 py-2.5 text-sm font-bold text-white shadow-xs transition-colors hover:bg-[#e04b00] disabled:opacity-40"
                >
                  <Sparkles className="h-4 w-4" aria-hidden />
                  {actBusy ? 'Running tools…' : 'Run tools'}
                </button>
                <button
                  type="button"
                  onClick={exportPkg}
                  disabled={!hasPayload}
                  className="inline-flex items-center gap-2 rounded-xl border border-[#d6cfc0] bg-[#faf8f3] px-4 py-2.5 text-sm font-bold text-[#171716] hover:bg-[#eee9dd] disabled:opacity-40"
                >
                  <Download className="h-4 w-4 text-[#ff5500]" aria-hidden />
                  Export
                </button>
                <button
                  type="button"
                  onClick={() => void deploy()}
                  disabled={deployBusy || !hasPayload || Boolean(holdReason)}
                  title={holdReason || undefined}
                  className="inline-flex items-center gap-2 rounded-xl border border-[#d6cfc0] bg-[#faf8f3] px-4 py-2.5 text-sm font-bold text-[#171716] hover:bg-[#eee9dd] disabled:opacity-40"
                >
                  <Rocket className="h-4 w-4 text-[#171716]" aria-hidden />
                  Deploy
                </button>
              </div>
            </div>

            <p className="mt-4 text-base leading-7 text-[#3d3b37]">{activeSummary}</p>

            {holdReason && (
              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs font-semibold text-amber-900">
                <span>{holdReason}</span>
                <button
                  type="button"
                  onClick={() => setMainTab('trust')}
                  className="font-bold text-[#ff5500] underline"
                >
                  Open Deployment Checklist →
                </button>
              </div>
            )}
          </section>

          {/* Tool Execution Results (#act-results) */}
          {(actRunId || workflowActions) && (
            <section
              id="act-results"
              data-testid="act-results"
              className="rounded-2xl border-2 border-[#ff5500] bg-white p-6 shadow-xs"
            >
              <div className="flex items-center justify-between">
                <h2 className="font-heading text-lg font-bold text-[#171716]">Tool Results</h2>
                {actRunId && (
                  <span className="font-mono text-xs text-[#57554f]">
                    {actRunId}
                    {usedSameRun ? ' · verified transcript' : ''}
                  </span>
                )}
              </div>
              {workflowActions ? (
                <ul className="mt-4 space-y-2.5 text-sm">
                  {workflowActions.actions.length === 0 && (
                    <li className="text-[#57554f]">No tool results from this run.</li>
                  )}
                  {workflowActions.actions.map((action, i) => (
                    <li
                      key={`${action.tool}-${i}`}
                      className="rounded-xl border border-[#e4decb] bg-[#faf8f3] p-3.5"
                    >
                      <span className="font-bold text-[#ff5500]">{action.tool}</span>
                      <span className="text-[#57554f]"> — {action.status}</span>
                      {action.result && (
                        <div className="mt-1 text-base text-[#171716]">{action.result}</div>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-[#57554f]">
                  {actBusy ? 'Running tools…' : 'Waiting for tool results.'}
                </p>
              )}
            </section>
          )}

          {/* Familiar Horizontal Content Tabs */}
          <div
            role="tablist"
            aria-label="Course and project sections"
            className="flex flex-wrap gap-2 border-b border-[#dcd5c6] pb-3"
          >
            <button
              type="button"
              role="tab"
              aria-selected={mainTab === 'plan'}
              onClick={() => setMainTab('plan')}
              className={clsx(
                'inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-colors',
                mainTab === 'plan'
                  ? 'bg-[#171716] text-white'
                  : 'bg-white text-[#57554f] border border-[#ded7c8] hover:text-[#171716]',
              )}
            >
              <Layers className="h-4 w-4" aria-hidden />
              <span>Action Plan & Steps ({linkedSop?.steps.length ?? 0})</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={mainTab === 'canvas'}
              onClick={() => setMainTab('canvas')}
              className={clsx(
                'inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-colors',
                mainTab === 'canvas'
                  ? 'bg-[#171716] text-white'
                  : 'bg-white text-[#57554f] border border-[#ded7c8] hover:text-[#171716]',
              )}
            >
              <FileCode2 className="h-4 w-4" aria-hidden />
              <span>Project Files ({previewFileNames.length})</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={mainTab === 'trust'}
              onClick={() => setMainTab('trust')}
              className={clsx(
                'inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-colors',
                mainTab === 'trust'
                  ? 'bg-[#171716] text-white'
                  : 'bg-white text-[#57554f] border border-[#ded7c8] hover:text-[#171716]',
              )}
            >
              <ShieldCheck className="h-4 w-4" aria-hidden />
              <span>Checklist & Proof</span>
            </button>
          </div>

          {/* TAB 1: Step-by-Step Action Plan & Events */}
          {mainTab === 'plan' && (
            <div className="flex flex-col gap-6">
              {linkedSop && (
                <section className="rounded-2xl border border-[#e2dbcc] bg-white p-6 shadow-xs">
                  <div className="flex items-center justify-between pb-4 border-b border-[#eee8da]">
                    <div>
                      <h2 className="font-heading text-xl font-black text-[#171716]">
                        SOP & Processes
                      </h2>
                      <p className="mt-0.5 text-sm text-[#57554f]">
                        Click any orange timestamp button to jump the video player to that step.
                      </p>
                    </div>
                  </div>

                  <ol className="mt-5 space-y-4">
                    {linkedSop.steps.map((step) => (
                      <li
                        key={step.id}
                        className="rounded-2xl border border-[#e6e0d2] bg-[#faf8f3] p-5 transition-colors hover:border-[#c8c0b0]"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2.5">
                            {step.timestamp != null ? (
                              <button
                                type="button"
                                onClick={() => setSeekSeconds(step.timestamp!)}
                                className="inline-flex items-center gap-1.5 rounded-lg bg-[#ff5500] px-3 py-1 font-mono text-xs font-bold text-white hover:bg-[#e04b00]"
                              >
                                <Play className="h-3 w-3 fill-current" aria-hidden />
                                {formatSeconds(step.timestamp)}
                              </button>
                            ) : (
                              <span className="rounded-lg bg-[#171716] px-2.5 py-1 font-mono text-xs font-bold text-white">
                                Step {step.order}
                              </span>
                            )}
                            <span
                              className={clsx(
                                'rounded-lg px-2.5 py-1 text-xs font-bold',
                                step.processType === 'implied'
                                  ? 'bg-amber-500/15 text-amber-900 border border-amber-500/30'
                                  : 'bg-emerald-500/15 text-emerald-900 border border-emerald-500/30',
                              )}
                            >
                              {step.processLabel ||
                                (step.processType === 'implied'
                                  ? 'Required by intent (unstated)'
                                  : 'Named in video')}
                            </span>
                          </div>
                        </div>

                        <h3 className="mt-3 text-lg font-bold text-[#171716]">{step.title}</h3>
                        {step.description && (
                          <p className="mt-1.5 text-base leading-7 text-[#3d3b37]">
                            {step.description}
                          </p>
                        )}

                        {step.tools && step.tools.length > 0 && (
                          <div className="mt-3.5 flex flex-wrap items-center gap-2 pt-3 border-t border-[#e8e2d4]">
                            <span className="text-xs font-bold text-[#57554f]">
                              Official Docs:
                            </span>
                            {step.tools.map((tool) => (
                              <a
                                key={tool.name}
                                href={tool.docsUrl || tool.officialUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 rounded-lg border border-[#dad3c4] bg-white px-2.5 py-1 text-xs font-bold text-[#171716] hover:border-[#ff5500] hover:text-[#ff5500]"
                              >
                                {tool.name}
                                <ExternalLink className="h-3 w-3" aria-hidden />
                              </a>
                            ))}
                          </div>
                        )}
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              {/* Key Video Events */}
              <section className="rounded-2xl border border-[#e2dbcc] bg-white p-6 shadow-xs">
                <h2 className="font-heading text-xl font-black text-[#171716]">Events</h2>
                <p className="mt-0.5 text-sm text-[#57554f]">
                  Key moments and decisions highlighted in this video.
                </p>
                <ul className="mt-4 space-y-3">
                  {activeEvents.map((event) => {
                    const seconds = parseTimestampToSeconds(event.timestamp);
                    return (
                      <li
                        key={event.id}
                        className="rounded-xl border border-[#e6e0d2] bg-[#faf8f3] p-4"
                      >
                        <div className="flex items-center gap-2.5">
                          {seconds != null && (
                            <button
                              type="button"
                              onClick={() => setSeekSeconds(seconds)}
                              className="rounded-md bg-[#171716] px-2.5 py-0.5 font-mono text-xs font-bold text-white hover:bg-[#ff5500]"
                            >
                              {formatSeconds(seconds)}
                            </button>
                          )}
                          <span className="text-base font-bold text-[#171716]">
                            {event.title}
                          </span>
                        </div>
                        {event.description && (
                          <p className="mt-1.5 text-base leading-relaxed text-[#3d3b37]">
                            {event.description}
                          </p>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </section>
            </div>
          )}

          {/* TAB 2: Project Code Files */}
          {mainTab === 'canvas' && (
            <section className="overflow-hidden rounded-2xl border border-[#e2dbcc] bg-white shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e8e2d4] p-6">
                <div>
                  <h2 className="font-heading text-xl font-black text-[#171716]">
                    Generated Project Package
                  </h2>
                  <p className="mt-0.5 text-sm text-[#57554f]">
                    Preview every file before downloading your `.zip` starter.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      copyText(
                        `file:${selectedArtifactFile}`,
                        previewPackage.files[selectedArtifactFile] || '',
                      )
                    }
                    className="inline-flex items-center gap-1.5 rounded-xl border border-[#d6cfc0] bg-[#faf8f3] px-3.5 py-2 text-xs font-bold text-[#171716] hover:bg-[#eee8da]"
                  >
                    {copiedKey === `file:${selectedArtifactFile}` ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" aria-hidden />
                        Copy File
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={exportPkg}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-[#ff5500] px-4 py-2 text-xs font-bold text-white hover:bg-[#e04b00]"
                  >
                    <Download className="h-3.5 w-3.5" aria-hidden />
                    Download .zip ({previewFileNames.length} files)
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5 border-b border-[#e8e2d4] bg-[#faf8f3] px-6 py-3">
                {previewFileNames.map((fname) => (
                  <button
                    key={fname}
                    type="button"
                    onClick={() => setSelectedArtifactFile(fname)}
                    className={clsx(
                      'rounded-lg px-3 py-1.5 font-mono text-xs font-bold transition-colors',
                      selectedArtifactFile === fname
                        ? 'bg-[#171716] text-white'
                        : 'text-[#57554f] hover:bg-[#ebe5d8] hover:text-[#171716]',
                    )}
                  >
                    {fname}
                  </button>
                ))}
              </div>

              <pre className="max-h-[500px] overflow-auto bg-[#171716] p-6 font-mono text-sm leading-relaxed text-[#f5f1e8]">
                <code>{previewPackage.files[selectedArtifactFile] || ''}</code>
              </pre>
            </section>
          )}

          {/* TAB 3: Deployment Checklist & Verification */}
          {mainTab === 'trust' && (
            <div className="flex flex-col gap-6">
              {stackItems.length > 0 && (
                <section className="rounded-2xl border border-[#e2dbcc] bg-white p-6 shadow-xs">
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#eee8da]">
                    <div>
                      <h2 className="font-heading text-xl font-black text-[#171716]">
                        Stack Deployment Checks
                      </h2>
                      <p className="mt-0.5 text-sm text-[#57554f]">
                        Check off these preflight items to unlock production deployment.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setCompletedChecks(
                          completedChecks.length === stackItems.length
                            ? []
                            : stackItems.map((i) => i.id),
                        )
                      }
                      className="rounded-xl bg-[#171716] px-4 py-2 text-xs font-bold text-white hover:bg-[#ff5500]"
                    >
                      {completedChecks.length === stackItems.length
                        ? 'Reset Checks'
                        : 'Verify All Checks'}
                    </button>
                  </div>

                  <ul className="mt-4 space-y-2.5">
                    {stackItems.map((item) => {
                      const checked = completedChecks.includes(item.id);
                      return (
                        <li
                          key={item.id}
                          className="flex items-center gap-3.5 rounded-xl border border-[#e6e0d2] bg-[#faf8f3] p-4"
                        >
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
                            className="h-4 w-4 accent-[#ff5500]"
                          />
                          <label
                            htmlFor={`check-${item.id}`}
                            className="flex flex-1 items-center justify-between gap-2 text-base font-medium cursor-pointer"
                          >
                            <span
                              className={
                                checked ? 'line-through text-[#8c877e]' : 'text-[#171716]'
                              }
                            >
                              {item.title}
                            </span>
                            {item.href && (
                              <a
                                href={item.href}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs font-bold text-[#ff5500] hover:underline"
                              >
                                Official Guide →
                              </a>
                            )}
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}

              <section className="rounded-2xl border border-[#e2dbcc] bg-white p-6 shadow-xs">
                <h2 className="font-heading text-xl font-black text-[#171716]">
                  Source Verification Details
                </h2>
                <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-xl border border-[#e6e0d2] bg-[#faf8f3] p-4">
                    <dt className="text-xs font-bold uppercase tracking-wider text-[#57554f]">
                      Caption Coverage
                    </dt>
                    <dd className="mt-1 text-base font-bold text-[#171716]">
                      {activeProvenance.timedSegmentCount}/{activeProvenance.segmentCount} Timed
                      Segments ({activeProvenance.durationCoverageSeconds ?? 0}s)
                    </dd>
                  </div>
                  <div className="rounded-xl border border-[#e6e0d2] bg-[#faf8f3] p-4">
                    <dt className="text-xs font-bold uppercase tracking-wider text-[#57554f]">
                      Official Starter
                    </dt>
                    <dd className="mt-1 font-mono text-sm font-bold text-[#ff5500]">
                      {officialTemplate ? officialTemplate.clone : 'Standard TypeScript Scaffold'}
                    </dd>
                  </div>
                </dl>
              </section>
            </div>
          )}
        </div>

        {/* ── Right Sidebar Rail: Named Tools & Interactive Transcript (YouTube / LinkedIn Learning Rail) ── */}
        <aside className="flex flex-col gap-6">
          {/* Named Tools Card */}
          {linkedSop && (
            <section className="rounded-2xl border border-[#e2dbcc] bg-white p-6 shadow-xs">
              <div className="flex items-center justify-between">
                <h2 className="font-heading text-lg font-black text-[#171716]">Named tools</h2>
                <span className="rounded-full bg-[#f5f1e8] px-3 py-1 text-xs font-bold text-[#57554f]">
                  {linkedSop.entities.length} tools
                </span>
              </div>
              <p className="mt-1 text-xs text-[#57554f]">
                Tools mentioned in the video with official documentation links.
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {linkedSop.entities.map((entity) => (
                  <div
                    key={entity.name}
                    className="inline-flex items-center gap-2 rounded-xl border border-[#e2dbcc] bg-[#faf8f3] px-3 py-1.5 text-sm"
                  >
                    <a
                      href={entity.officialUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="font-bold text-[#171716] hover:text-[#ff5500]"
                    >
                      {entity.name}
                    </a>
                    {entity.docsUrl && entity.docsUrl !== entity.officialUrl && (
                      <a
                        href={entity.docsUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded bg-[#e8e2d5] px-1.5 py-0.5 text-[11px] font-bold text-[#3d3b37] hover:text-[#171716]"
                      >
                        Docs
                      </a>
                    )}
                    {entity.timestamps[0] != null && (
                      <button
                        type="button"
                        onClick={() => setSeekSeconds(entity.timestamps[0])}
                        className="rounded bg-[#ff5500]/15 px-1.5 py-0.5 font-mono text-xs font-bold text-[#d94800] hover:bg-[#ff5500] hover:text-white"
                      >
                        {formatSeconds(entity.timestamps[0])}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Interactive Transcript Rail */}
          <section className="rounded-2xl border border-[#e2dbcc] bg-white p-6 shadow-xs">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-heading text-lg font-black text-[#171716]">Transcript</h2>
                <p className="text-xs text-[#57554f]">{wordCount} words · Click to seek video</p>
              </div>
              <button
                type="button"
                onClick={() => copyText('transcript', activeTranscript)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#d6cfc0] bg-[#faf8f3] px-3 py-1.5 text-xs font-bold text-[#171716] hover:bg-[#eee8da]"
              >
                {copiedKey === 'transcript' ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" aria-hidden />
                    Copy
                  </>
                )}
              </button>
            </div>

            <div className="mt-3 flex items-center gap-2 rounded-xl border border-[#dcd5c6] bg-[#faf8f3] px-3 py-2">
              <Search className="h-4 w-4 text-[#78746c]" aria-hidden />
              <input
                type="search"
                value={transcriptQuery}
                onChange={(e) => setTranscriptQuery(e.target.value)}
                placeholder="Search transcript…"
                aria-label="Search transcript"
                className="w-full bg-transparent text-sm font-medium text-[#171716] outline-none placeholder:text-[#8c877e]"
              />
            </div>

            <div className="mt-4 max-h-[560px] space-y-2.5 overflow-y-auto pr-1">
              {filteredSegments.map((seg, idx) => {
                const isCurrent =
                  seekSeconds != null &&
                  seg.start <= seekSeconds &&
                  seekSeconds < seg.start + (seg.duration || 20);
                return (
                  <div
                    key={`${seg.start}-${idx}`}
                    className={clsx(
                      'flex items-start gap-3 rounded-xl p-3.5 transition-colors',
                      isCurrent
                        ? 'bg-[#ff5500]/10 border border-[#ff5500]/40'
                        : 'bg-[#faf8f3] border border-[#ebe5d8] hover:border-[#d0c8b8]',
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => setSeekSeconds(Math.floor(seg.start))}
                      className="mt-0.5 shrink-0 rounded-md bg-[#171716] px-2 py-0.5 font-mono text-xs font-bold text-white hover:bg-[#ff5500]"
                    >
                      {formatSeconds(Math.floor(seg.start))}
                    </button>
                    <p className="text-[15px] leading-6 text-[#262523] font-normal">{seg.text}</p>
                  </div>
                );
              })}
            </div>
          </section>
        </aside>
      </main>
    </div>
  );
}
