import Image from 'next/image';
import Link from 'next/link';
import {
  Captions,
  CheckCircle2,
  Clock3,
  Database,
  ExternalLink,
  FileDown,
  Fingerprint,
  Gauge,
  PlayCircle,
  Route,
  ShieldCheck,
  Workflow,
} from 'lucide-react';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';

const capabilities = [
  {
    title: 'Source provenance',
    body: 'Every completed record shows the source host, acquisition method, fetch time, segment counts, timed coverage, and raw source link.',
    icon: Fingerprint,
  },
  {
    title: 'Timed captions',
    body: 'The transcript is built from backend-acquired caption segments with real timestamps. Unlabeled captions remain labeled as captions.',
    icon: Captions,
  },
  {
    title: 'Evidence quality gate',
    body: 'Export and success states stay blocked unless transcript evidence passes structural and provenance checks.',
    icon: ShieldCheck,
  },
  {
    title: 'Durable workflow runs',
    body: 'Each analysis receives a run ID, persists its result, and can resume polling after a browser refresh.',
    icon: Workflow,
  },
  {
    title: 'Grounded AI synthesis',
    body: 'The model receives the verified transcript and returns summary, topics, and proposed actions without reconstructing missing source content.',
    icon: Database,
  },
  {
    title: 'Review before execution',
    body: 'Action preparation executes nothing. A second confirmation is required for the exact reviewed plan, and external writes are labeled.',
    icon: CheckCircle2,
  },
  {
    title: 'Interactive playback',
    body: 'The YouTube player, seek timeline, and caption timestamps stay connected so users can inspect the source while reviewing conclusions.',
    icon: PlayCircle,
  },
  {
    title: 'Verified export boundary',
    body: 'Exports are enabled only after the quality gate passes; failed acquisition never turns into a synthetic package.',
    icon: FileDown,
  },
  {
    title: 'Protected paid AI routes',
    body: 'AI endpoints use a tighter budget and fail closed in production when distributed rate limiting is unavailable.',
    icon: Gauge,
  },
];

const runtimeRows = [
  ['Video input', 'YouTube watch and short URLs only', 'SSRF boundary'],
  ['Transcript', 'Backend caption API or named STT source', 'Evidence required'],
  ['Analysis', 'Vercel AI Gateway with configured provider', 'Transcript-grounded'],
  ['Persistence', 'Workflow run ID plus persisted result', 'Refresh recovery'],
  ['Actions', 'Prepare, review, confirm', 'No automatic dispatch'],
  ['Deployment', 'Vercel Services: Next.js and FastAPI', 'Preview before production'],
];

export default function FeaturesPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#07080b] text-[#f4f6fb]">
      <Nav fixed />

      <section className="px-6 pb-16 pt-32 md:pt-40">
        <div className="mx-auto max-w-6xl">
          <div className="max-w-3xl">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-indigo-400/25 bg-indigo-500/10 px-3.5 py-1 text-xs font-semibold tracking-wide text-indigo-200">
              Decision Intelligence Architecture
            </p>
            <h1 className="font-heading text-4xl font-bold leading-tight tracking-tight text-white md:text-6xl">
              Video intelligence you can inspect before you act.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-zinc-300 md:text-lg">
              UVAI treats captions as verifiable evidence, keeps source provenance visible, persists
              every workflow run, and enforces a deliberate review boundary in front of external
              execution.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/"
                className="inline-flex items-center justify-center rounded-xl bg-[#f4f6fb] px-7 py-3.5 text-sm font-bold text-[#07080b] transition-colors hover:bg-white"
              >
                Analyze a YouTube video
              </Link>
              <Link
                href="/docs/api"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.12] bg-white/[0.04] px-7 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-white/[0.09]"
              >
                <Route className="h-4 w-4 text-indigo-300" aria-hidden="true" />
                Inspect API surface
              </Link>
            </div>
          </div>

          <figure className="mt-14 overflow-hidden rounded-2xl border border-white/[0.09] bg-[#0e1118] shadow-2xl">
            <Image
              src="/evidence-workspace-dashboard.png"
              alt="Verified UVAI analysis with source provenance, timed captions, YouTube playback, and grounded synthesis"
              width={990}
              height={762}
              priority
              className="h-auto w-full"
              sizes="(max-width: 1200px) 100vw, 1152px"
            />
            <figcaption className="flex flex-col justify-between gap-2 border-t border-white/[0.07] px-5 py-4 text-xs leading-5 text-zinc-400 sm:flex-row">
              <span>Real test fixture: 176/176 timed caption segments, 474.4 seconds of source coverage.</span>
              <a
                href="https://www.youtube.com/watch?v=auJzb1D-fag"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 font-semibold text-indigo-300 hover:text-indigo-200"
              >
                Inspect source
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-2xl">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-indigo-300">
              System Capabilities
            </p>
            <h2 className="font-heading text-3xl font-bold tracking-tight text-white md:text-5xl">
              Clear evidence, durable state, controlled action.
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {capabilities.map(({ title, body, icon: Icon }) => (
              <article key={title} className="rounded-2xl border border-white/[0.08] bg-[#0e1118] p-6">
                <Icon className="mb-5 h-6 w-6 text-indigo-300" strokeWidth={1.7} aria-hidden="true" />
                <h3 className="font-heading text-lg font-bold text-white">{title}</h3>
                <p className="mt-3 text-[15px] leading-7 text-zinc-300">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl rounded-2xl border border-white/[0.09] bg-[#0e1118] p-6 md:p-10">
          <div className="mb-8 flex items-start gap-4">
            <Clock3 className="mt-1 h-6 w-6 shrink-0 text-indigo-300" aria-hidden="true" />
            <div>
              <h2 className="font-heading text-2xl font-bold text-white">Runtime contract</h2>
              <p className="mt-2 text-[15px] leading-7 text-zinc-300">
                These are the boundaries the current build enforces in production.
              </p>
            </div>
          </div>
          <div className="overflow-hidden rounded-xl border border-white/[0.08]">
            {runtimeRows.map(([surface, implementation, boundary], index) => (
              <div
                key={surface}
                className="grid gap-2 border-b border-white/[0.06] px-5 py-4 text-sm last:border-0 md:grid-cols-[0.7fr_1.4fr_0.9fr]"
                style={{ background: index % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}
              >
                <strong className="font-heading text-white">{surface}</strong>
                <span className="text-zinc-300">{implementation}</span>
                <span className="font-medium text-indigo-300">{boundary}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl rounded-2xl border border-indigo-400/20 bg-[#0e1118] p-8 text-center md:p-12">
          <h2 className="font-heading text-3xl font-bold tracking-tight text-white md:text-5xl">
            Start with a source you can verify.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-zinc-300">
            Paste a public YouTube URL. UVAI will either return a verified decision model or surface the exact stage that blocked it.
          </p>
          <Link
            href="/"
            className="mt-8 inline-flex justify-center rounded-xl bg-[#f4f6fb] px-8 py-3.5 text-sm font-bold text-[#07080b] transition-colors hover:bg-white"
          >
            Open Studio
          </Link>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
