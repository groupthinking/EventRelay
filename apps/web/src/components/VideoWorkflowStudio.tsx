'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import {
  ChevronRight,
  Download,
  Layers,
  Mic,
  MicOff,
  Monitor,
  PanelRightOpen,
  Play,
  Rocket,
  Save as SaveIcon,
  Search,
  Sparkles,
  X,
  Youtube,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useRealtimeVoice } from '@/hooks/use-realtime-voice';

type OutcomeId = 'app' | 'sop' | 'lesson' | 'research' | 'automation' | 'content';
type RunState = 'idle' | 'working' | 'ready';

const OUTCOMES: Array<{ id: OutcomeId; label: string; description: string }> = [
  { id: 'app', label: 'App', description: 'Product screen or working flow.' },
  { id: 'sop', label: 'SOP', description: 'Repeatable operating steps.' },
  { id: 'lesson', label: 'Lesson', description: 'Guided learning path.' },
  { id: 'research', label: 'Research', description: 'Brief, sources, and calls.' },
  { id: 'automation', label: 'Automation', description: 'Runnable workflow recipe.' },
  { id: 'content', label: 'Content plan', description: 'Scripts and publishing steps.' },
];

const UNSAFE_TERMS = [
  'bomb',
  'explosive',
  'weapon',
  'malware',
  'phishing',
  'ransomware',
  'credential theft',
  'bypass auth',
  'steal',
];

const RESULT_CARDS = [
  {
    title: 'Preview',
    description: 'Open the generated app, SOP, lesson, or brief before export.',
    icon: Monitor,
  },
  {
    title: 'Export',
    description: 'Package the brief, source notes, and handoff files.',
    icon: Download,
  },
  {
    title: 'Deploy',
    description: 'Prepare the Vercel-ready app or automation handoff.',
    icon: Rocket,
  },
  {
    title: 'Save',
    description: 'Save this run and keep the source trail attached.',
    icon: SaveIcon,
  },
];

function getYouTubeId(url: string) {
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=|shorts\/))([^&?/]+)/);
  return match?.[1] || '';
}

function isUnsafeRequest(text: string) {
  const normalized = text.toLowerCase();
  return UNSAFE_TERMS.some((term) => normalized.includes(term));
}

function makeFrameUrls(videoId: string) {
  if (!videoId) return [];
  return [
    `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`,
    `https://img.youtube.com/vi/${videoId}/1.jpg`,
    `https://img.youtube.com/vi/${videoId}/2.jpg`,
    `https://img.youtube.com/vi/${videoId}/3.jpg`,
  ];
}

function OutcomeCard({
  outcome,
  selected,
  onSelect,
}: {
  outcome: (typeof OUTCOMES)[number];
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={clsx(
        'rounded-lg border px-3 py-2 text-left transition-all',
        selected
          ? 'border-slate-950 bg-slate-950 text-white shadow-sm'
          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50',
      )}
    >
      <div className="text-sm font-semibold leading-5">{outcome.label}</div>
      <div className={clsx('mt-1 text-xs leading-4', selected ? 'text-white/70' : 'text-slate-500')}>
        {outcome.description}
      </div>
    </button>
  );
}

function EmptyFrame() {
  return (
    <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white text-slate-600 shadow-sm">
        <Youtube className="h-7 w-7" />
      </div>
      <div>
        <div className="text-base font-semibold text-slate-950">Paste a YouTube link</div>
        <div className="mt-1 max-w-sm text-sm text-slate-500">
          UVAI uses the video, frames, transcript, and speaker context to prepare one useful output.
        </div>
      </div>
    </div>
  );
}

export default function VideoWorkflowStudio() {
  const [videoUrl, setVideoUrl] = useState('');
  const [selectedOutcome, setSelectedOutcome] = useState<OutcomeId>('app');
  const [prompt, setPrompt] = useState('Turn this video into a polished workflow I can review, export, and deploy.');
  const [runState, setRunState] = useState<RunState>('idle');
  const [unsafeRedirect, setUnsafeRedirect] = useState(false);
  const [developerOpen, setDeveloperOpen] = useState(false);

  const audioRef = useRef<HTMLAudioElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const realtime = useRealtimeVoice(audioRef);

  const videoId = useMemo(() => getYouTubeId(videoUrl), [videoUrl]);
  const frameUrls = useMemo(() => makeFrameUrls(videoId), [videoId]);
  const selectedOutcomeLabel = OUTCOMES.find((outcome) => outcome.id === selectedOutcome)?.label || 'Workflow';
  const hasVideo = Boolean(videoId);
  const isWorking = runState === 'working';
  const resultReady = runState === 'ready';
  const voiceConnecting = realtime.status === 'connecting';
  const voiceEngaged = realtime.isActive || voiceConnecting;
  const voiceLabel = voiceConnecting ? 'Voice connecting' : realtime.isActive ? 'Voice on' : 'Voice off';

  const statusLabel = resultReady ? 'Ready' : isWorking ? 'Working' : 'Idle';
  const statusMessage = unsafeRedirect
    ? 'Safe alternative prepared. Harmful instructions stay out of the output.'
    : resultReady
      ? `${selectedOutcomeLabel} package ready for preview, export, deploy, or save.`
      : isWorking
        ? `Building the ${selectedOutcomeLabel.toLowerCase()} from the current source.`
        : 'Ready when the source and outcome are set.';

  const disconnectRealtime = realtime.disconnect;

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      disconnectRealtime();
    };
  }, [disconnectRealtime]);

  const runWorkflow = (event?: FormEvent) => {
    event?.preventDefault();
    if (timerRef.current) clearTimeout(timerRef.current);

    const unsafe = isUnsafeRequest(prompt);
    setUnsafeRedirect(unsafe);
    setRunState('working');

    timerRef.current = setTimeout(() => {
      setRunState('ready');
    }, 900);
  };

  const handleResultAction = () => {
    if (!resultReady) {
      runWorkflow();
    }
  };

  return (
    <div className="min-h-screen bg-[#f6f7f9] text-slate-950">
      <audio ref={audioRef} className="hidden" autoPlay />

      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-5 py-3 lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-sm font-black text-white">
              U
            </div>
            <div>
              <div className="text-sm font-bold leading-4">UVAI</div>
              <div className="text-xs text-slate-500">Video to workflow</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-1 rounded-full border border-slate-200 bg-slate-50 p-1 text-sm text-slate-600 md:flex">
            <Link href="/" className="rounded-full bg-white px-4 py-1.5 font-medium text-slate-950 shadow-sm">
              Studio
            </Link>
            <Link href="/dashboard" className="rounded-full px-4 py-1.5 hover:bg-white hover:text-slate-950">
              Dashboard
            </Link>
            <Link href="/prototype" className="rounded-full px-4 py-1.5 hover:bg-white hover:text-slate-950">
              Prototype
            </Link>
          </nav>

          <button
            type="button"
            onClick={() => runWorkflow()}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-blue-600/20 transition hover:bg-blue-700"
          >
            <Sparkles className="h-4 w-4" />
            Run workflow
          </button>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1440px] gap-5 px-5 py-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.75fr)] lg:px-8">
        <section className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <form onSubmit={runWorkflow} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
              <label className="sr-only" htmlFor="video-url">
                Paste a YouTube link
              </label>
              <input
                id="video-url"
                value={videoUrl}
                onChange={(event) => setVideoUrl(event.target.value)}
                placeholder="Paste a YouTube link"
                className="h-12 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              />
              <button
                type="submit"
                className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                <Play className="h-4 w-4" />
                Run
              </button>
            </form>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3">
              <div>
                <h1 className="text-xl font-semibold text-slate-950 md:text-2xl">Turn video into finished work</h1>
                <p className="mt-1 text-sm text-slate-500">
                  Paste a source, describe the outcome, and leave with a package you can use.
                </p>
              </div>
            </div>

            <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
              {hasVideo ? (
                <iframe
                  src={`https://www.youtube.com/embed/${videoId}`}
                  title="YouTube video preview"
                  className="aspect-video w-full border-0"
                  allowFullScreen
                />
              ) : (
                <EmptyFrame />
              )}
            </div>

            <div className="mt-4 grid grid-cols-4 gap-2">
              {(frameUrls.length ? frameUrls : [null, null, null, null]).map((frame, index) => (
                <div
                  key={frame ?? `empty-frame-${index}`}
                  className="aspect-video overflow-hidden rounded-lg border border-slate-200 bg-slate-100"
                >
                  {frame ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={frame} alt={`Source frame ${index + 1}`} className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-slate-400">Frame {index + 1}</div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1">Frames, transcript, and speaker context</span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1">No speaker voice cloning</span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1">Source trail kept with output</span>
            </div>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-950">What should this become?</h2>
                <p className="text-sm text-slate-500">Choose the output, then describe what useful looks like.</p>
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                <button
                  type="button"
                  onClick={voiceEngaged ? realtime.stop : realtime.start}
                  className={clsx(
                    'inline-flex items-center gap-2 rounded-md px-2 py-1 text-xs font-semibold transition',
                    voiceEngaged ? 'bg-blue-600 text-white' : 'bg-white text-slate-700 hover:bg-slate-100',
                  )}
                >
                  {voiceEngaged ? <Mic className="h-3.5 w-3.5" /> : <MicOff className="h-3.5 w-3.5" />}
                  {voiceLabel}
                </button>
                {realtime.isActive && (
                  <button type="button" onClick={realtime.toggleMute} className="text-xs font-medium text-slate-500 hover:text-slate-900">
                    {realtime.status === 'muted' ? 'Resume' : 'Mute'}
                  </button>
                )}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
              {OUTCOMES.map((outcome) => (
                <OutcomeCard
                  key={outcome.id}
                  outcome={outcome}
                  selected={selectedOutcome === outcome.id}
                  onSelect={() => setSelectedOutcome(outcome.id)}
                />
              ))}
            </div>

            <form onSubmit={runWorkflow} className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
              <label className="sr-only" htmlFor="result-prompt">
                Describe the result
              </label>
              <input
                id="result-prompt"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                className="h-12 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-950 outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              />
              <button
                type="submit"
                className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 text-sm font-semibold text-white shadow-sm shadow-blue-600/20 transition hover:bg-blue-700"
              >
                Build result
                <ChevronRight className="h-4 w-4" />
              </button>
            </form>

            <div className="mt-3 flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 md:flex-row md:items-center md:justify-between">
              <span>{statusMessage}</span>
              <span
                className={clsx(
                  'inline-flex w-fit rounded-full px-2 py-1 font-semibold',
                  resultReady && 'bg-emerald-100 text-emerald-700',
                  isWorking && 'bg-blue-100 text-blue-700',
                  runState === 'idle' && 'bg-white text-slate-500',
                )}
              >
                {statusLabel}
              </span>
            </div>

            {unsafeRedirect && (
              <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                This request was redirected into a safe planning workflow. UVAI can create a risk review,
                training summary, or benign operations checklist instead of harmful instructions.
              </div>
            )}
          </section>
        </section>

        <aside className="space-y-5">
          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-slate-950">Result package</h2>
                <p className="mt-1 text-sm text-slate-500">Preview, export, deploy, or save the generated package.</p>
              </div>
            </div>

            <div className="grid gap-3">
              {RESULT_CARDS.map((card) => {
                const Icon = card.icon;
                return (
                  <button
                    key={card.title}
                    type="button"
                    onClick={handleResultAction}
                    className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-left transition hover:border-slate-300 hover:bg-white"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-white text-slate-700 shadow-sm">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-slate-950">{card.title}</div>
                        <div className="mt-1 text-xs leading-5 text-slate-500">{card.description}</div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <button
              type="button"
              onClick={() => setDeveloperOpen((open) => !open)}
              className="flex w-full items-center justify-between text-left text-sm font-semibold text-slate-950"
            >
              <span className="inline-flex items-center gap-2">
                <PanelRightOpen className="h-4 w-4 text-slate-500" />
                Developer details
              </span>
              {developerOpen ? <X className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
            </button>

            {developerOpen && (
              <div className="mt-3 max-h-52 space-y-2 overflow-y-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-200">
                {realtime.events.length ? (
                  realtime.events.map((event) => (
                    <div key={event.id} className="flex items-start gap-2 border-b border-white/10 pb-2 last:border-0 last:pb-0">
                      <Search className="mt-0.5 h-3.5 w-3.5 flex-none text-blue-300" />
                      <div className="min-w-0">
                        <div className="font-mono text-[11px] text-blue-200">{event.type}</div>
                        <div className="text-slate-300">{event.label}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center gap-2 text-slate-400">
                    <Layers className="h-4 w-4" />
                    Voice events appear here when the toggle is on.
                  </div>
                )}
              </div>
            )}

            {realtime.error && <div className="mt-3 text-xs text-rose-600">{realtime.error}</div>}
          </section>
        </aside>
      </main>
    </div>
  );
}
