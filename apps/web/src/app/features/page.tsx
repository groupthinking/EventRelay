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
import LandingNav from '@/components/landing/LandingNav';
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
    <main className="min-h-screen overflow-hidden bg-surface-950 text-white">
      <LandingNav />

      <section className="px-6 pb-16 pt-36 md:pt-44">
        <div className="mx-auto max-w-6xl">
          <div className="max-w-3xl">
            <p className="mb-4 text-[11px] font-bold uppercase tracking-[0.26em] text-teal-300/80">
              Evidence-first platform
            </p>
            <h1 className="font-heading text-5xl font-black leading-tight tracking-tight md:text-7xl">
              Video intelligence you can inspect before you act.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-white/50 md:text-lg">
              UVAI treats captions as evidence, keeps provenance visible, persists every workflow run,
              and puts a deliberate review boundary in front of external execution.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/dashboard" className="btn btn-primary justify-center px-7 py-3 text-sm">
                Analyze a YouTube video
              </Link>
              <Link href="/docs/api" className="btn btn-secondary justify-center px-7 py-3 text-sm">
                <Route className="h-4 w-4" aria-hidden="true" />
                Inspect API surface
              </Link>
            </div>
          </div>

          <figure className="mt-14 overflow-hidden rounded-[2rem] border border-white/[0.08] bg-black/30 shadow-2xl shadow-teal-500/10">
            <Image
              src="/evidence-workspace-dashboard.png"
              alt="Verified UVAI analysis with source provenance, timed captions, YouTube playback, and grounded synthesis"
              width={990}
              height={762}
              priority
              className="h-auto w-full"
              sizes="(max-width: 1200px) 100vw, 1152px"
            />
            <figcaption className="flex flex-col justify-between gap-2 border-t border-white/[0.07] px-5 py-4 text-xs leading-5 text-white/45 sm:flex-row">
              <span>Real test fixture: 176/176 timed caption segments, 474.4 seconds of source coverage.</span>
              <a
                href="https://www.youtube.com/watch?v=auJzb1D-fag"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-teal-300/80 hover:text-teal-200"
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
            <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.25em] text-teal-300/70">
              What is implemented
            </p>
            <h2 className="font-heading text-3xl font-black tracking-tight md:text-5xl">
              Clear evidence, durable state, controlled action.
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {capabilities.map(({ title, body, icon: Icon }) => (
              <article key={title} className="rounded-3xl border border-white/[0.07] bg-white/[0.03] p-6">
                <Icon className="mb-5 h-6 w-6 text-teal-300" strokeWidth={1.7} aria-hidden="true" />
                <h3 className="font-heading text-lg font-bold">{title}</h3>
                <p className="mt-3 text-sm leading-7 text-white/45">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl rounded-[2rem] border border-white/[0.08] bg-white/[0.025] p-6 md:p-10">
          <div className="mb-8 flex items-start gap-4">
            <Clock3 className="mt-1 h-6 w-6 shrink-0 text-teal-300" aria-hidden="true" />
            <div>
              <h2 className="font-heading text-2xl font-black">Runtime contract</h2>
              <p className="mt-2 text-sm leading-7 text-white/45">
                These are the boundaries the current build enforces, not future roadmap promises.
              </p>
            </div>
          </div>
          <div className="overflow-hidden rounded-2xl border border-white/[0.07]">
            {runtimeRows.map(([surface, implementation, boundary], index) => (
              <div
                key={surface}
                className="grid gap-2 border-b border-white/[0.06] px-5 py-4 text-sm last:border-0 md:grid-cols-[0.7fr_1.4fr_0.9fr]"
                style={{ background: index % 2 ? 'rgba(255,255,255,0.015)' : 'transparent' }}
              >
                <strong className="font-heading text-white/85">{surface}</strong>
                <span className="text-white/50">{implementation}</span>
                <span className="text-teal-300/75">{boundary}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl rounded-[2rem] border border-teal-400/15 bg-teal-400/[0.06] p-8 text-center md:p-12">
          <h2 className="font-heading text-3xl font-black tracking-tight md:text-5xl">
            Start with a source you can verify.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-white/50">
            Paste a public YouTube URL. UVAI will either return a verified analysis or show the exact stage that blocked it.
          </p>
          <Link href="/dashboard" className="btn btn-primary mt-8 inline-flex justify-center px-8 py-3 text-sm">
            Open dashboard
          </Link>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
