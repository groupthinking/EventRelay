'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Download, Play, Rocket, Save } from 'lucide-react';
import { clsx } from 'clsx';
import Nav from '@/components/Nav';
import { useDashboardStore } from '@/store/dashboard-store';
import {
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
import type { ExtractedEvent } from '@/lib/types';

const FIXTURE = 'https://www.youtube.com/watch?v=auJzb1D-fag';

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
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Paste a YouTube URL to transcribe and extract events.');
  const [actBusy, setActBusy] = useState(false);
  const [deployBusy, setDeployBusy] = useState(false);
  const [workflowActions, setWorkflowActions] = useState<VideoToActionsResult | null>(null);
  const [actRunId, setActRunId] = useState<string | null>(null);
  const [usedSameRun, setUsedSameRun] = useState(false);
  const [deployRunId, setDeployRunId] = useState<string | null>(null);

  const processVideo = useDashboardStore((s) => s.processVideo);
  const selectVideo = useDashboardStore((s) => s.selectVideo);
  const updateVideo = useDashboardStore((s) => s.updateVideo);
  const selectedVideoId = useDashboardStore((s) => s.selectedVideoId);
  const videos = useDashboardStore((s) => s.videos);
  const selected = videos.find((v) => v.id === selectedVideoId);

  useEffect(() => {
    useDashboardStore.persist.rehydrate();
  }, []);

  useEffect(() => {
    const q = searchParams.get('video') || searchParams.get('url');
    if (q && !url) setUrl(q);
  }, [searchParams, url]);

  const videoId = useMemo(() => getYouTubeId(url), [url]);
  const hasPayload =
    (selected?.transcript?.trim().length ?? 0) >= 40 || (selected?.events?.length ?? 0) > 0;
  const runState = busy ? 'working' : selected ? 'ready' : 'idle';
  const quality = studioRunQuality(
    selected?.jobId ? { ok: true, status: 200, jobId: selected.jobId } : null,
    false,
    Boolean(videoId || selected),
    { transcript: selected?.transcript, eventCount: selected?.events?.length ?? 0 },
  );

  const analyze = async (event?: FormEvent) => {
    event?.preventDefault();
    const next = url.trim();
    if (!getYouTubeId(next)) {
      setMessage('Need a valid YouTube URL.');
      return;
    }
    setBusy(true);
    setWorkflowActions(null);
    setActRunId(null);
    setUsedSameRun(false);
    setMessage('Running the live pipeline…');
    const tick = window.setInterval(() => {
      const live = useDashboardStore
        .getState()
        .videos.find((v) => v.url === next || v.url.includes(getYouTubeId(next)));
      if (live) selectVideo(live.id);
    }, 250);
    try {
      const id = await processVideo(next);
      selectVideo(id);
      const video = useDashboardStore.getState().videos.find((v) => v.id === id);
      const ready =
        (video?.transcript?.trim().length ?? 0) >= 40 || (video?.events?.length ?? 0) > 0;
      setMessage(
        ready
          ? 'Transcript and events are on this page. Act, export, or save from here.'
          : 'Pipeline finished without a usable transcript. Try another public video.',
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

      const payload = buildSameRunActInput({
        url: next,
        videoTitle: selected?.title,
        transcript: selected?.transcript,
        events,
      });
      setUsedSameRun(Boolean(payload.transcript || payload.events?.length));

      const started = await startVideoToActions(payload);
      if (!started.ok || !started.runId) {
        if (started.status === 401 || started.status === 403) {
          window.location.href = `/login?callbackUrl=${encodeURIComponent('/')}`;
          return;
        }
        setMessage(started.error || 'Could not start Act.');
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
    const actions = (selected?.insights?.actions || []).map((a) => ({
      title: a.title,
      description: a.description,
      category: a.category,
      estimatedMinutes: a.estimatedMinutes,
    }));
    if (actions.length === 0 && !selected?.insights?.project_scaffold) {
      setMessage('Nothing to export yet — analyze a video first.');
      return;
    }
    const pkg = buildScaffoldPackage({
      projectName: selected?.title || 'uvai-project',
      actions,
      projectScaffold: selected?.insights?.project_scaffold,
    });
    downloadScaffoldPackage(pkg);
    setMessage('Exported scaffold files (README, tasks.json).');
  };

  const deploy = async () => {
    const next = (selected?.url || url).trim();
    if (!getYouTubeId(next)) {
      setMessage('Analyze a video before deploy.');
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
        setMessage(started.error || 'Deploy needs sign-in.');
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

  return (
    <div className="min-h-screen bg-surface-950 text-white">
      <Nav
        subtitle="Analyze"
        rightSlot={
          <Link
            href={`/login?callbackUrl=${encodeURIComponent('/')}`}
            className="text-sm text-white/60 hover:text-white"
          >
            Sign in
          </Link>
        }
      />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-300">UVAI</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight">Video to action</h1>
        <p className="mt-2 max-w-2xl text-sm text-white/55">
          Paste a YouTube URL. You get a transcript, typed events, then you act — on this page.
        </p>

        <form onSubmit={analyze} className="mt-8 flex flex-col gap-3 sm:flex-row">
          <label className="sr-only" htmlFor="youtube-url">
            YouTube URL
          </label>
          <input
            id="youtube-url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={FIXTURE}
            className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm outline-none focus:border-teal-400/60"
          />
          <button
            type="submit"
            disabled={busy}
            className={clsx(
              'inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold',
              'bg-teal-400 text-slate-950 disabled:opacity-50',
            )}
          >
            <Play className="h-4 w-4" aria-hidden />
            {busy ? 'Analyzing…' : 'Analyze'}
          </button>
        </form>

        <p className="mt-4 text-sm text-white/70" role="status">
          <span className="font-semibold text-white/90">
            {studioStatusLabel(quality, runState)}
          </span>
          {' — '}
          {message || studioStatusMessage(quality, runState, 'Analysis', false)}
        </p>

        {selected?.status === 'processing' && (
          <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full bg-teal-400 transition-all"
              style={{ width: `${Math.min(100, selected.progress || 5)}%` }}
            />
          </div>
        )}

        {videoId && (
          <div className="mt-8 overflow-hidden rounded-2xl border border-white/10 bg-black">
            <iframe
              title="YouTube source"
              className="aspect-video w-full"
              src={`https://www.youtube.com/embed/${videoId}`}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        )}

        {selected && (
          <section className="mt-8 grid gap-6 lg:grid-cols-2">
            <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-white/50">Transcript</h2>
              <p className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-sm leading-6 text-white/80">
                {selected.transcript?.trim() || 'No transcript yet.'}
              </p>
            </article>
            <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-white/50">Events</h2>
              <ul className="mt-3 max-h-72 space-y-2 overflow-auto text-sm">
                {(selected.events || []).length === 0 && (
                  <li className="text-white/50">No events yet.</li>
                )}
                {(selected.events || []).map((event) => (
                  <li key={event.id} className="rounded-lg border border-white/5 px-3 py-2">
                    <div className="text-xs uppercase tracking-wide text-teal-300/80">{event.type}</div>
                    <div className="font-medium">{event.title}</div>
                    {event.description && (
                      <div className="text-white/55">{event.description}</div>
                    )}
                  </li>
                ))}
              </ul>
            </article>
          </section>
        )}

        {selected?.insights && (
          <section className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-white/50">Summary</h2>
            <p className="mt-3 text-sm leading-6 text-white/80">{selected.insights.summary}</p>
            {(selected.insights.actions?.length ?? 0) > 0 && (
              <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-white/70">
                {selected.insights.actions.map((action) => (
                  <li key={action.title}>{action.title}</li>
                ))}
              </ul>
            )}
          </section>
        )}

        {(actRunId || workflowActions) && (
          <section
            id="act-results"
            data-testid="act-results"
            className="mt-6 rounded-2xl border border-teal-400/20 bg-teal-400/5 p-5"
          >
            <h2 className="text-sm font-semibold uppercase tracking-wide text-teal-200">
              Act results
            </h2>
            {actRunId && (
              <p className="mt-2 text-xs text-white/50">
                Run {actRunId}
                {usedSameRun ? " · this run's transcript" : ''}
              </p>
            )}
            {workflowActions ? (
              <ul className="mt-3 space-y-2 text-sm">
                {workflowActions.actions.length === 0 && (
                  <li className="text-white/50">No tool results from this run.</li>
                )}
                {workflowActions.actions.map((action, i) => (
                  <li key={`${action.tool}-${i}`}>
                    <span className="font-medium">{action.tool}</span>
                    <span className="text-white/50"> — {action.status}</span>
                    {action.result && <div className="text-white/70">{action.result}</div>}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-white/60">
                {actBusy ? 'Running tools on this page…' : 'Waiting for tool results on this page.'}
              </p>
            )}
          </section>
        )}

        <div className="mt-8 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void act()}
            disabled={actBusy || !hasPayload}
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 px-4 py-2 text-sm disabled:opacity-40"
          >
            {actBusy ? 'Acting…' : 'Act'}
          </button>
          <button
            type="button"
            onClick={exportPkg}
            disabled={!hasPayload}
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 px-4 py-2 text-sm disabled:opacity-40"
          >
            <Download className="h-4 w-4" aria-hidden />
            Export
          </button>
          <button
            type="button"
            onClick={() => void deploy()}
            disabled={deployBusy || !hasPayload}
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 px-4 py-2 text-sm disabled:opacity-40"
          >
            <Rocket className="h-4 w-4" aria-hidden />
            Deploy
          </button>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 px-4 py-2 text-sm"
          >
            <Save className="h-4 w-4" aria-hidden />
            Library
          </Link>
        </div>
        {(actRunId || deployRunId) && (
          <p className="mt-3 text-xs text-white/40">
            {actRunId ? `Act run ${actRunId}` : null}
            {actRunId && deployRunId ? ' · ' : null}
            {deployRunId ? `Deploy run ${deployRunId}` : null}
          </p>
        )}
      </main>
    </div>
  );
}
