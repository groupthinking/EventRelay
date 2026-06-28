'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import {
  ChevronRight,
  CheckCircle2,
  Clipboard,
  Download,
  FileText,
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
  Video,
  X,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useRealtimeVoice } from '@/hooks/use-realtime-voice';
import {
  studioRunQuality,
  studioStatusLabel,
  studioStatusMessage,
  type StudioPipelineCheck,
  type StudioRunQuality,
} from '@/lib/studio-pipeline-status';

type OutcomeId = 'app' | 'sop' | 'lesson' | 'research' | 'automation' | 'content';
type RunState = 'idle' | 'working' | 'ready';
type ResultAction = 'preview' | 'export' | 'deploy' | 'save';

const DEFAULT_PROMPT = 'Turn this video into a polished workflow I can review, export, and deploy.';

interface GeneratedPackage {
  title: string;
  summary: string;
  primaryOutput: string;
  sourceNotes: string[];
  deliverables: string[];
  nextSteps: string[];
  evidence: string[];
  safetyNote?: string;
  createdAt: string;
}

type PipelineCheck = StudioPipelineCheck & {
  backend?: {
    configured?: boolean;
    available?: boolean;
    host?: string | null;
    reason?: string;
  };
};

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

const RESULT_CARDS: Array<{
  id: ResultAction;
  title: string;
  description: string;
  icon: typeof Monitor;
}> = [
  {
    id: 'preview',
    title: 'Preview',
    description: 'Open the generated app, SOP, lesson, or brief before export.',
    icon: Monitor,
  },
  {
    id: 'export',
    title: 'Export',
    description: 'Package the brief, source notes, and handoff files.',
    icon: Download,
  },
  {
    id: 'deploy',
    title: 'Deploy',
    description: 'Prepare the Vercel-ready app or automation handoff.',
    icon: Rocket,
  },
  {
    id: 'save',
    title: 'Save',
    description: 'Save this run and keep the source trail attached.',
    icon: SaveIcon,
  },
];

const OUTPUT_COPY: Record<OutcomeId, { noun: string; deliverables: string[]; nextSteps: string[] }> = {
  app: {
    noun: 'working app brief',
    deliverables: ['Responsive screen map', 'Component checklist', 'Vercel handoff notes'],
    nextSteps: ['Confirm the target user journey', 'Scaffold the first route and component states', 'Run lint, build, and browser smoke checks'],
  },
  sop: {
    noun: 'operating procedure',
    deliverables: ['Role-by-role SOP', 'Acceptance checklist', 'Exception handling notes'],
    nextSteps: ['Assign an owner', 'Run the process once on a real example', 'Store the final SOP with the source trail'],
  },
  lesson: {
    noun: 'lesson package',
    deliverables: ['Learning outline', 'Practice tasks', 'Assessment prompts'],
    nextSteps: ['Confirm learner level', 'Add examples from the video', 'Package as a repeatable lesson'],
  },
  research: {
    noun: 'research brief',
    deliverables: ['Source-backed summary', 'Open questions', 'Decision memo'],
    nextSteps: ['Verify source claims', 'Separate facts from assumptions', 'Share the recommendation with stakeholders'],
  },
  automation: {
    noun: 'automation recipe',
    deliverables: ['Trigger and action map', 'Required integrations', 'Failure and retry notes'],
    nextSteps: ['Choose the first trigger', 'Connect the service accounts', 'Test the workflow with one safe input'],
  },
  content: {
    noun: 'content plan',
    deliverables: ['Channel plan', 'Draft script angles', 'Publishing checklist'],
    nextSteps: ['Pick the primary audience', 'Generate the first draft', 'Schedule review and publish steps'],
  },
};

function getYouTubeId(url: string) {
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=|shorts\/))([^&?/]+)/);
  return match?.[1] || '';
}

function currentVideoUrlForLink(videoUrl: string) {
  const id = getYouTubeId(videoUrl);
  if (!id) return '/dashboard';
  const normalized = videoUrl.trim() || `https://www.youtube.com/watch?v=${id}`;
  return `/dashboard?video=${encodeURIComponent(normalized)}`;
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

function buildPackage({
  videoId,
  videoUrl,
  outcome,
  prompt,
  unsafe,
  pipelineCheck,
}: {
  videoId: string;
  videoUrl: string;
  outcome: OutcomeId;
  prompt: string;
  unsafe: boolean;
  pipelineCheck?: PipelineCheck | null;
}): GeneratedPackage {
  const copy = OUTPUT_COPY[outcome];
  const cleanPrompt = unsafe
    ? 'Create a benign safety review and educational workflow instead of harmful instructions.'
    : prompt.trim() || 'Turn this video into a useful workflow package.';
  const sourceLabel = videoId ? `YouTube source ${videoId}` : 'Pending source URL';
  const backendHost = pipelineCheck?.backend?.host;
  const backendReason = pipelineCheck?.backend?.reason;
  const pipelineState = pipelineStateLabel(pipelineCheck, unsafe);

  return {
    title: `${copy.noun[0].toUpperCase()}${copy.noun.slice(1)} from video`,
    summary: `${sourceLabel} is packaged as a ${copy.noun}. The source is visible, the request is turned into concrete deliverables, and backend readiness is checked before handoff.`,
    primaryOutput: cleanPrompt,
    sourceNotes: [
      videoUrl ? `Source URL: ${videoUrl}` : 'No source URL entered yet.',
      videoId ? 'Preview and thumbnail evidence are attached.' : 'Add a valid YouTube URL to attach video evidence.',
      'Speaker audio is used for context only; no voice cloning is performed.',
      pipelineState,
      backendHost ? `Backend target: ${backendHost}${backendReason ? ` (${backendReason})` : ''}` : 'Backend target was not available for this run.',
    ],
    deliverables: copy.deliverables,
    nextSteps: copy.nextSteps,
    evidence: [
      videoId ? 'Video preview loaded' : 'Video preview pending',
      frameUrlsForPackage(videoId),
      pipelineEvidenceLabel(pipelineCheck),
      unsafe ? 'Safety gate applied' : 'Safety gate passed',
    ],
    safetyNote: unsafe
      ? 'Unsafe instructions were converted into a benign planning and risk-review package.'
      : undefined,
    createdAt: new Date().toISOString(),
  };
}

function pipelineStateLabel(pipelineCheck: PipelineCheck | null | undefined, unsafe: boolean) {
  if (!pipelineCheck) {
    return unsafe
      ? 'Pipeline was not called because the request was redirected for safety.'
      : 'Local package prepared while source evidence is attached.';
  }

  if (pipelineCheck.pipeline === 'local-fallback') {
    return 'Pipeline returned a local fallback handoff while automatic execution waits on backend or provider configuration.';
  }

  if (pipelineCheck.ok) {
    return `Pipeline checked successfully${pipelineCheck.pipeline ? ` (${pipelineCheck.pipeline})` : ''}.`;
  }

  return `Pipeline checked and returned ${pipelineCheck.status}${pipelineCheck.message ? `: ${pipelineCheck.message}` : '.'}`;
}

function pipelineEvidenceLabel(pipelineCheck: PipelineCheck | null | undefined) {
  if (pipelineCheck?.pipeline === 'local-fallback') return 'Local fallback handoff created';
  if (pipelineCheck?.ok) return 'Pipeline response received';
  return 'Fallback package created';
}

function frameUrlsForPackage(videoId: string) {
  return videoId ? 'Thumbnail frames attached' : 'Thumbnail frames pending';
}

function packageToText(pkg: GeneratedPackage) {
  return [
    pkg.title,
    '',
    pkg.summary,
    '',
    `Primary request: ${pkg.primaryOutput}`,
    '',
    'Source notes:',
    ...pkg.sourceNotes.map((note) => `- ${note}`),
    '',
    'Deliverables:',
    ...pkg.deliverables.map((item) => `- ${item}`),
    '',
    'Evidence:',
    ...pkg.evidence.map((item) => `- ${item}`),
    '',
    'Next steps:',
    ...pkg.nextSteps.map((item) => `- ${item}`),
    pkg.safetyNote ? ['', `Safety: ${pkg.safetyNote}`] : [],
  ].flat().join('\n');
}

function downloadPackage(pkg: GeneratedPackage) {
  const blob = new Blob([JSON.stringify(pkg, null, 2)], { type: 'application/json' });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = `uvai-package-${new Date(pkg.createdAt).getTime()}.json`;
  anchor.click();
  URL.revokeObjectURL(href);
}

function readSavedPackages() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem('uvai.savedPackages') || '[]');
    return Array.isArray(parsed) ? parsed as GeneratedPackage[] : [];
  } catch {
    return [];
  }
}

/**
 * Renders a selectable output category card.
 *
 * @param outcome - The outcome shown in the card.
 * @param selected - Whether the card is currently selected.
 * @param onSelect - Called when the card is clicked.
 */
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
      aria-pressed={selected}
      className={clsx(
        'rounded-lg border px-3 py-2 text-left transition-colors',
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

/**
 * Displays a placeholder panel prompting the user to paste a YouTube link.
 */
function EmptyFrame() {
  return (
    <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white text-slate-600 shadow-sm">
        <Video className="h-7 w-7" aria-hidden="true" />
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

/**
 * Renders the Video Workflow Studio interface.
 */
export default function VideoWorkflowStudio() {
  const [videoUrl, setVideoUrl] = useState('');
  const [selectedOutcome, setSelectedOutcome] = useState<OutcomeId>('app');
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [runState, setRunState] = useState<RunState>('idle');
  const [unsafeRedirect, setUnsafeRedirect] = useState(false);
  const [developerOpen, setDeveloperOpen] = useState(false);
  const [activeAction, setActiveAction] = useState<ResultAction>('preview');
  const [generatedPackage, setGeneratedPackage] = useState<GeneratedPackage | null>(null);
  const [saveCount, setSaveCount] = useState(0);
  const [actionMessage, setActionMessage] = useState('Build a result to unlock preview, export, deploy, and save.');
  const [runQuality, setRunQuality] = useState<StudioRunQuality>('idle');

  const audioRef = useRef<HTMLAudioElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const videoUrlRef = useRef('');
  const promptRef = useRef(DEFAULT_PROMPT);
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

  const statusLabel = studioStatusLabel(runQuality, runState);
  const statusMessage = studioStatusMessage(
    runQuality,
    runState,
    selectedOutcomeLabel,
    unsafeRedirect,
  );
  const dashboardHandoffUrl = currentVideoUrlForLink(videoUrl);

  const disconnectRealtime = realtime.disconnect;

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      disconnectRealtime();
    };
  }, [disconnectRealtime]);

  const runWorkflow = async (event?: FormEvent) => {
    event?.preventDefault();
    if (timerRef.current) clearTimeout(timerRef.current);

    const currentVideoUrl = videoUrlRef.current || videoUrl;
    const currentPrompt = promptRef.current || prompt;
    const currentVideoId = getYouTubeId(currentVideoUrl);
    const unsafe = isUnsafeRequest(currentPrompt);
    setUnsafeRedirect(unsafe);
    setRunState('working');
    setRunQuality('idle');
    setActionMessage(unsafe ? 'Preparing a safe alternative package.' : 'Checking backend readiness (async kickoff).');

    let pipelineCheck: PipelineCheck | null = null;
    if (!unsafe && currentVideoId) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 12_000);
      try {
        const response = await fetch('/api/pipeline', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: currentVideoUrl,
            async: true,
            outcome: selectedOutcome,
            prompt: currentPrompt,
            project_type: selectedOutcome === 'app' ? 'web' : selectedOutcome,
            deployment_target: 'vercel',
          }),
          signal: controller.signal,
        });
        const payload = await response.json().catch(() => ({}));
        const jobId = typeof payload.job_id === 'string' ? payload.job_id : undefined;
        pipelineCheck = {
          ok: response.ok,
          status: response.status,
          pipeline: typeof payload.pipeline === 'string' ? payload.pipeline : undefined,
          jobId,
          backend: payload.backend && typeof payload.backend === 'object' ? payload.backend : undefined,
          message: typeof payload.error === 'string'
            ? payload.error
            : typeof payload.detail === 'string'
              ? payload.detail
              : typeof payload.result?.message === 'string'
                ? payload.result.message
                : undefined,
        };
      } catch (error) {
        pipelineCheck = {
          ok: false,
          status: 0,
          message: error instanceof Error && error.name === 'AbortError'
            ? 'Backend check timed out.'
            : error instanceof Error
              ? error.message
              : 'Backend check failed.',
        };
      } finally {
        clearTimeout(timeout);
      }
    }

    const quality = studioRunQuality(pipelineCheck, unsafe, Boolean(currentVideoId));

    timerRef.current = setTimeout(() => {
      const nextPackage = buildPackage({
        videoId: currentVideoId,
        videoUrl: currentVideoUrl,
        outcome: selectedOutcome,
        prompt: currentPrompt,
        unsafe,
        pipelineCheck,
      });
      setGeneratedPackage(nextPackage);
      setRunQuality(quality);
      setRunState('ready');
      setActiveAction('preview');
      setActionMessage(
        quality === 'live'
          ? 'Backend accepted the job. This package is a planning draft — open Dashboard for live analysis.'
          : 'Planning draft only. Studio does not run the full agent pipeline; use Dashboard for live results.',
      );
    }, unsafe ? 250 : 100);
  };

  const handleResultAction = (action: ResultAction) => {
    setActiveAction(action);
    if (!resultReady) {
      runWorkflow();
      return;
    }

    if (!generatedPackage) return;

    if (action === 'export') {
      downloadPackage(generatedPackage);
      setActionMessage('Export downloaded as a JSON package.');
      return;
    }

    if (action === 'save') {
      const saved = readSavedPackages();
      const nextSaved = [generatedPackage, ...saved].slice(0, 12);
      window.localStorage.setItem('uvai.savedPackages', JSON.stringify(nextSaved));
      setSaveCount(nextSaved.length);
      setActionMessage(`Saved locally. ${nextSaved.length} package${nextSaved.length === 1 ? '' : 's'} available in this browser.`);
      return;
    }

    setActionMessage(
      action === 'deploy'
        ? 'Deploy handoff prepared. Connect the backend pipeline when BACKEND_URL is healthy for automatic deployment.'
        : 'Preview is open with source notes, deliverables, and next steps.',
    );
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
              <span className="ml-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-600">Preview</span>
            </Link>
            <Link href="/dashboard/agents" className="rounded-full px-4 py-1.5 hover:bg-white hover:text-slate-950">
              Agents
            </Link>
          </nav>

          <button
            type="button"
            onClick={() => runWorkflow()}
            aria-busy={isWorking || undefined}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-blue-600/20 transition-colors hover:bg-blue-700"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Run workflow
          </button>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1440px] gap-5 px-5 py-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.75fr)] lg:px-8">
        <div className="lg:col-span-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="text-sm text-slate-600">
              <span className="font-semibold text-slate-950">Studio</span> builds local planning drafts.
              {' '}
              <span className="font-semibold text-slate-950">Dashboard</span> runs the live agent pipeline (transcript, actions, agents).
              {' '}
              <span className="font-semibold text-slate-950">Prototype</span> is a design walkthrough — not connected to production APIs.
            </div>
            <Link
              href={dashboardHandoffUrl}
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-100"
            >
              Open live analysis
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        <section className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <form onSubmit={runWorkflow} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
              <label className="sr-only" htmlFor="video-url">
                Paste a YouTube link
              </label>
              <input
                id="video-url"
                type="url"
                inputMode="url"
                autoComplete="off"
                spellCheck={false}
                value={videoUrl}
                onChange={(event) => {
                  videoUrlRef.current = event.target.value;
                  setVideoUrl(event.target.value);
                }}
                placeholder="e.g. https://youtube.com/watch?v=…"
                className="h-12 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-950 outline-none transition-[background-color,border-color,box-shadow] placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              />
              <button
                type="submit"
                aria-busy={isWorking || undefined}
                className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
              >
                <Play className="h-4 w-4" aria-hidden="true" />
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
                  loading="lazy"
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
                    <img
                      src={frame}
                      alt={`Source frame ${index + 1}`}
                      width={320}
                      height={180}
                      loading="lazy"
                      className="h-full w-full object-cover"
                    />
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
                  aria-pressed={voiceEngaged}
                  className={clsx(
                    'inline-flex items-center gap-2 rounded-md px-2 py-1 text-xs font-semibold transition-colors',
                    voiceEngaged ? 'bg-blue-600 text-white' : 'bg-white text-slate-700 hover:bg-slate-100',
                  )}
                >
                  {voiceEngaged ? <Mic className="h-3.5 w-3.5" aria-hidden="true" /> : <MicOff className="h-3.5 w-3.5" aria-hidden="true" />}
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
                onChange={(event) => {
                  promptRef.current = event.target.value;
                  setPrompt(event.target.value);
                }}
                placeholder="e.g. Build a working app I can deploy to Vercel"
                autoComplete="off"
                className="h-12 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-950 outline-none transition-[background-color,border-color,box-shadow] placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              />
              <button
                type="submit"
                aria-busy={isWorking || undefined}
                className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 text-sm font-semibold text-white shadow-sm shadow-blue-600/20 transition-colors hover:bg-blue-700"
              >
                Build result
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </form>

            <div
              role="status"
              aria-live="polite"
              className="mt-3 flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 md:flex-row md:items-center md:justify-between"
            >
              <span>{statusMessage}</span>
              <span
                className={clsx(
                  'inline-flex w-fit rounded-full px-2 py-1 font-semibold',
                  resultReady && runQuality === 'live' && 'bg-emerald-100 text-emerald-700',
                  resultReady && runQuality !== 'live' && 'bg-amber-100 text-amber-800',
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
                    onClick={() => handleResultAction(card.id)}
                    className={clsx(
                      'rounded-lg border p-3 text-left transition hover:border-slate-300 hover:bg-white',
                      activeAction === card.id ? 'border-blue-200 bg-blue-50' : 'border-slate-200 bg-slate-50',
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-white text-slate-700 shadow-sm">
                        <Icon className="h-4 w-4" aria-hidden="true" />
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

            <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  {activeAction === 'preview' && <Monitor className="h-4 w-4 text-blue-600" aria-hidden="true" />}
                  {activeAction === 'export' && <FileText className="h-4 w-4 text-blue-600" aria-hidden="true" />}
                  {activeAction === 'deploy' && <Rocket className="h-4 w-4 text-blue-600" aria-hidden="true" />}
                  {activeAction === 'save' && <CheckCircle2 className="h-4 w-4 text-blue-600" aria-hidden="true" />}
                  {RESULT_CARDS.find((card) => card.id === activeAction)?.title}
                </div>
                {saveCount > 0 && <span className="text-xs text-slate-500">{saveCount} saved</span>}
              </div>

              {generatedPackage ? (
                <div className="space-y-4 text-sm text-slate-700">
                  {activeAction === 'preview' && (
                    <>
                      <div>
                        <h3 className="text-base font-semibold text-slate-950">{generatedPackage.title}</h3>
                        <p className="mt-1 leading-6 text-slate-600">{generatedPackage.summary}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                        {generatedPackage.primaryOutput}
                      </div>
                    </>
                  )}

                  {activeAction === 'export' && (
                    <div className="space-y-3">
                      <p className="leading-6">The package is ready as JSON and plain text for handoff.</p>
                      <pre className="max-h-56 overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">
                        {packageToText(generatedPackage)}
                      </pre>
                    </div>
                  )}

                  {activeAction === 'deploy' && (
                    <div className="space-y-3">
                      <p className="leading-6">
                        This is deployable as a Vercel handoff now. Automatic backend deployment is gated by the configured backend pipeline health.
                      </p>
                      <div className="grid gap-2">
                        {generatedPackage.nextSteps.map((step) => (
                          <div key={step} className="flex gap-2 rounded-lg bg-slate-50 p-2 text-xs leading-5">
                            <Rocket className="mt-0.5 h-3.5 w-3.5 flex-none text-blue-600" aria-hidden="true" />
                            <span>{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeAction === 'save' && (
                    <div className="space-y-3">
                      <p className="leading-6">Saved packages stay in this browser so the user can return to the source trail.</p>
                      <div className="rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                        Latest saved package: {generatedPackage.title}
                      </div>
                    </div>
                  )}

                  <div className="grid gap-2">
                    {generatedPackage.evidence.map((item) => (
                      <div key={item} className="flex gap-2 text-xs leading-5 text-slate-600">
                        <Layers className="mt-0.5 h-3.5 w-3.5 flex-none text-blue-600" aria-hidden="true" />
                        <span>{item}</span>
                      </div>
                    ))}

                    {generatedPackage.deliverables.map((item) => (
                      <div key={item} className="flex gap-2 text-xs leading-5 text-slate-600">
                        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 flex-none text-emerald-600" aria-hidden="true" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>

                  {generatedPackage.safetyNote && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
                      {generatedPackage.safetyNote}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-500">
                  <Clipboard className="mt-1 h-4 w-4 flex-none text-slate-400" aria-hidden="true" />
                  <span>{actionMessage}</span>
                </div>
              )}

              {generatedPackage && (
                <div className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">{actionMessage}</div>
              )}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <button
              type="button"
              onClick={() => setDeveloperOpen((open) => !open)}
              aria-expanded={developerOpen}
              className="flex w-full items-center justify-between text-left text-sm font-semibold text-slate-950"
            >
              <span className="inline-flex items-center gap-2">
                <PanelRightOpen className="h-4 w-4 text-slate-500" aria-hidden="true" />
                Developer details
              </span>
              {developerOpen ? <X className="h-4 w-4 text-slate-400" aria-hidden="true" /> : <ChevronRight className="h-4 w-4 text-slate-400" aria-hidden="true" />}
            </button>

            {developerOpen && (
              <div className="mt-3 max-h-52 space-y-2 overflow-y-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-200">
                {realtime.events.length ? (
                  realtime.events.map((event) => (
                    <div key={event.id} className="flex items-start gap-2 border-b border-white/10 pb-2 last:border-0 last:pb-0">
                      <Search className="mt-0.5 h-3.5 w-3.5 flex-none text-blue-300" aria-hidden="true" />
                      <div className="min-w-0">
                        <div className="font-mono text-[11px] text-blue-200">{event.type}</div>
                        <div className="text-slate-300">{event.label}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center gap-2 text-slate-400">
                    <Layers className="h-4 w-4" aria-hidden="true" />
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
