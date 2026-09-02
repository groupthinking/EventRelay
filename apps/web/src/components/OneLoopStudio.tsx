'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Download, Play, Rocket, Save } from 'lucide-react';
import { formatSeconds, parseTimestampToSeconds } from '@/lib/timestamp';
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
import { identityPackJson } from '@/lib/emit-video-pack';
import {
  studioPackCitation,
  studioPasteOutcomeMessage,
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
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState('Paste a YouTube URL. Transcript and events land here.');
  const [actBusy, setActBusy] = useState(false);
  const [deployBusy, setDeployBusy] = useState(false);
  const [workflowActions, setWorkflowActions] = useState<VideoToActionsResult | null>(null);
  const [actRunId, setActRunId] = useState<string | null>(null);
  const [usedSameRun, setUsedSameRun] = useState(false);
  const [deployRunId, setDeployRunId] = useState<string | null>(null);
  const [seekSeconds, setSeekSeconds] = useState<number | null>(null);
  const [completedChecks, setCompletedChecks] = useState<string[]>([]);

  const processVideo = useDashboardStore((s) => s.processVideo);
  const selectVideo = useDashboardStore((s) => s.selectVideo);
  const updateVideo = useDashboardStore((s) => s.updateVideo);
  const selectedVideoId = useDashboardStore((s) => s.selectedVideoId);
  const videos = useDashboardStore((s) => s.videos);
  const selected = videos.find((v) => v.id === selectedVideoId);
  const linkedSop: LinkedSop | null = useMemo(() => {
    if (selected?.insights?.linkedSop) return selected.insights.linkedSop;
    if (!selected?.transcript && !(selected?.events?.length)) return null;
    const insightActions = (selected?.insights?.actions || []).flatMap((action) => {
      if (typeof action === 'string') {
        return action.trim() ? [{ title: action.trim() }] : [];
      }
      return action.title?.trim() ? [{ title: action.title, description: action.description, category: action.category }] : [];
    });
    return compileLinkedSop({
      transcript: selected?.transcript,
      events: (selected?.events || []).map((event) => ({
        timestamp: parseTimestampToSeconds(event.timestamp) ?? undefined,
        label: event.title,
        description: event.description,
      })),
      actions: insightActions,
      topics: selected?.insights?.topics,
    });
  }, [selected]);

  useEffect(() => {
    setCompletedChecks([]);
  }, [selectedVideoId]);

  const holdReason = deployHoldReason(linkedSop, completedChecks);
  const officialTemplate = pickOfficialTemplate(linkedSop);

  useEffect(() => {
    useDashboardStore.persist.rehydrate();
  }, []);

  useEffect(() => {
    const q = searchParams.get('video') || searchParams.get('url');
    if (q) setUrl(q);
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
    setMessage('Fetching transcript…');
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
          window.location.href = `/login?callbackUrl=${encodeURIComponent('/')}`;
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
    if (actions.length === 0 && !selected?.insights?.project_scaffold && !linkedSop?.steps.length) {
      setMessage('Nothing to export yet — analyze a video first.');
      return;
    }
    const pkg = buildScaffoldPackage({
      projectName: selected?.title || 'uvai-project',
      actions,
      projectScaffold: selected?.insights?.project_scaffold,
      linkedSop: linkedSop || undefined,
    });
    downloadScaffoldPackage(pkg);
    setMessage(
      officialTemplate
        ? `Exported ${officialTemplate.clone} plus SOP and DEPLOY.md.`
        : linkedSop
          ? 'Exported SOP, named tools, and DEPLOY.md from this run.'
          : 'Exported scaffold files (README, tasks.json).',
    );
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

  const statusText = busy
    ? `Working · ${elapsed}s — ${message}`
    : `${studioStatusLabel(quality, runState)} — ${message || studioStatusMessage(quality, runState, 'Analysis', false)}`;

  return (
    <div className="flex min-h-screen flex-col bg-[#0b0c10] text-[#f4f1ea]">
      <Nav
        rightSlot={
          <Link
            href={`/login?callbackUrl=${encodeURIComponent('/')}`}
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
          {selected?.videoPack && (
            <p
              data-testid="video-pack-citation"
              className="break-all font-mono text-[11px] text-white/55"
            >
              {studioPackCitation(selected.videoPack)}
            </p>
          )}
          {(busy || selected?.status === 'processing') && (
            <div className="h-1 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full bg-[#e8b86d] transition-all"
                style={{ width: `${Math.min(95, selected?.progress || 8 + elapsed * 2)}%` }}
              />
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl flex-1 gap-4 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <section className="overflow-hidden rounded-xl border border-white/10 bg-black">
          {videoId ? (
            <iframe
              title="YouTube source"
              className="aspect-video w-full"
              src={
                seekSeconds != null
                  ? `https://www.youtube.com/embed/${videoId}?start=${seekSeconds}`
                  : `https://www.youtube.com/embed/${videoId}`
              }
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
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
          <div className="max-h-[420px] flex-1 overflow-auto px-4 py-3 text-sm leading-6 text-white/80">
            {selected?.transcript?.trim() ||
              (busy ? 'Waiting on captions…' : 'Nothing yet.')}
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-[#11131a] lg:col-span-2">
          <div className="border-b border-white/10 px-4 py-3">
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
              Events
            </h2>
          </div>
          <ul className="divide-y divide-white/5">
            {(selected?.events || []).length === 0 && (
              <li className="px-4 py-4 text-sm text-white/40">
                {busy ? 'Extracting events…' : 'Events show up after Run.'}
              </li>
            )}
            {(selected?.events || []).map((event) => {
              const seconds = parseTimestampToSeconds(event.timestamp);
              return (
              <li key={event.id} className="grid gap-1 px-4 py-3 sm:grid-cols-[7rem_1fr]">
                {seconds != null ? (
                  <button
                    type="button"
                    onClick={() => setSeekSeconds(seconds)}
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

        {linkedSop && (linkedSop.entities.length > 0 || linkedSop.steps.length > 0) && (
          <section className="rounded-xl border border-white/10 bg-[#11131a] lg:col-span-2">
            <div className="border-b border-white/10 px-4 py-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
                Named tools
              </h2>
            </div>
            <div className="flex flex-wrap gap-2 px-4 py-3">
              {linkedSop.entities.length === 0 && (
                <p className="text-sm text-white/40">No catalogued tools in this transcript.</p>
              )}
              {linkedSop.entities.map((entity) => (
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
                      onClick={() => setSeekSeconds(entity.timestamps[0])}
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
              {linkedSop.steps.map((step) => (
                <li key={step.id} className="grid gap-1 px-4 py-3 sm:grid-cols-[7rem_1fr]">
                  {step.timestamp != null ? (
                    <button
                      type="button"
                      onClick={() => setSeekSeconds(step.timestamp!)}
                      className="text-left font-mono text-[11px] text-[#e8b86d]"
                    >
                      {formatSeconds(step.timestamp)}
                    </button>
                  ) : (
                    <div className="font-mono text-[11px] text-white/35">{step.order}</div>
                  )}
                  <div>
                    <div className="text-sm font-medium text-white">{step.title}</div>
                    {step.description && (
                      <div className="mt-0.5 text-sm text-white/55">{step.description}</div>
                    )}
                  </div>
                </li>
              ))}
            </ol>

            {linkedSop.checklist.some((item) => item.source === 'stack') && (
              <>
                <div className="border-t border-white/10 px-4 py-3">
                  <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
                    Stack checks
                  </h2>
                </div>
                <ul className="divide-y divide-white/5">
                  {linkedSop.checklist
                    .filter((item) => item.source === 'stack')
                    .map((item) => {
                      const checked = completedChecks.includes(item.id);
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

        {(actRunId || workflowActions) && (
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
                {actBusy ? 'Running tools…' : 'Waiting for tool results.'}
              </p>
            )}
          </section>
        )}
      </main>

      <footer className="sticky bottom-0 border-t border-white/10 bg-[#11131a]/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3 sm:px-6">
          <button
            type="button"
            onClick={() => void act()}
            disabled={actBusy || !hasPayload}
            className="inline-flex items-center gap-2 rounded-lg bg-[#e8b86d] px-4 py-2 text-sm font-semibold text-[#1a1408] disabled:opacity-40"
          >
            {actBusy ? 'Running tools…' : 'Run tools'}
          </button>
          <button
            type="button"
            onClick={exportPkg}
            disabled={!hasPayload}
            className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm disabled:opacity-40"
          >
            <Download className="h-4 w-4" aria-hidden />
            Export
          </button>
          <button
            type="button"
            onClick={() => void deploy()}
            disabled={deployBusy || !hasPayload || Boolean(holdReason)}
            title={holdReason || undefined}
            className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm disabled:opacity-40"
          >
            <Rocket className="h-4 w-4" aria-hidden />
            Deploy
          </button>
          {holdReason && (
            <p className="basis-full text-xs text-[#e8b86d] sm:basis-auto sm:max-w-xl">
              {holdReason}
            </p>
          )}
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm"
          >
            <Save className="h-4 w-4" aria-hidden />
            Library
          </Link>
        </div>
      </footer>
    </div>
  );
}
