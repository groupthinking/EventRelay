import Link from 'next/link';
import Image from 'next/image';
import LandingNav from '@/components/landing/LandingNav';
import Footer from '@/components/Footer';

const workflowSteps = [
  {
    label: 'Paste a video URL',
    detail: 'Start with a YouTube link from a meeting, tutorial, launch, podcast, or customer interview.',
  },
  {
    label: 'Extract intelligence',
    detail: 'UVAI acquires timed captions, verifies their provenance, and extracts grounded topics and action proposals.',
  },
  {
    label: 'Review and confirm',
    detail: 'Inspect grounded action proposals, then explicitly confirm any external agent or knowledge-store work.',
  },
];

const featureCards = [
  {
    title: 'Verified caption evidence',
    body: 'Inspect the source host, acquisition method, fetch time, segment counts, timed coverage, and raw video link.',
  },
  {
    title: 'Action event extraction',
    body: 'Detect decisions, tasks, requirements, product ideas, risks, and follow-ups as structured events.',
  },
  {
    title: 'Source-linked playback',
    body: 'Seek from timed caption segments while the real YouTube source remains visible beside the analysis.',
  },
  {
    title: 'Agent pipeline ready',
    body: 'Review extracted events before explicitly dispatching MCP-compatible automation for downstream work.',
  },
  {
    title: 'Exports and API workflows',
    body: 'Export structured results only after the evidence quality gate has passed.',
  },
  {
    title: 'Built for repeat analysis',
    body: 'Keep a video library with processing state, filters, insights, and reusable action history.',
  },
];

const reasons = [
  'Less manual note-taking after long videos.',
  'More structure than a generic summary.',
  'Agent-ready output instead of static documents.',
  'A dashboard-first workflow your team can reuse.',
];

const faqs = [
  {
    question: 'What can I analyze?',
    answer: 'UVAI is optimized for YouTube URLs today, including demos, talks, podcasts, tutorials, and meetings published as videos.',
  },
  {
    question: 'What happens after I paste a URL?',
    answer: 'A durable run acquires captions, records provenance, checks evidence quality, creates grounded analysis, and saves the verified result in your dashboard library.',
  },
  {
    question: 'Do I need to configure agents first?',
    answer: 'No. Start with review-only video analysis. External execution remains unavailable until its backend and entitlement requirements are satisfied.',
  },
  {
    question: 'Is this just transcription?',
    answer: 'No. Captions are the evidence layer for topics, summaries, action proposals, search, and explicitly confirmed automation.',
  },
];

function DashboardPreview() {
  return (
    <figure className="relative mx-auto w-full max-w-xl overflow-hidden rounded-[2rem] border border-white/[0.08] bg-surface-950/90 shadow-2xl shadow-teal-500/10">
      <Image
        src="/evidence-workspace-dashboard.png"
        alt="UVAI dashboard showing a verified YouTube source, timed captions, the video player, and grounded analysis"
        width={1440}
        height={1024}
        priority
        className="h-auto w-full"
        sizes="(max-width: 1024px) 100vw, 560px"
      />
      <figcaption className="border-t border-white/[0.07] px-5 py-3 text-xs leading-5 text-white/45">
        Product capture from a real YouTube analysis: 176 timed captions and 474.4 seconds of verified coverage.
      </figcaption>
    </figure>
  );
}

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-surface-950 text-white">
      <LandingNav />

      <section className="relative px-6 pb-20 pt-36 md:pb-28 md:pt-44">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.18),transparent_36%),radial-gradient(circle_at_80%_20%,rgba(34,211,238,0.14),transparent_30%)]" />
        <div className="mx-auto grid max-w-6xl items-center gap-14 lg:grid-cols-[1.02fr_0.98fr]">
          <div>
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-400/20 bg-teal-400/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.24em] text-teal-200">
              Video intelligence for agent workflows
            </div>
            <h1 className="max-w-3xl font-heading text-5xl font-black leading-[1.02] tracking-tight md:text-7xl">
              Turn YouTube videos into evidence, findings, and reviewable actions.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-white/50 md:text-lg">
              UVAI acquires timed YouTube captions, verifies the evidence, extracts structured events, and prepares actions for review before automation.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link href="/dashboard" className="btn btn-primary justify-center px-7 py-3 text-sm">
                Analyze a video
              </Link>
              <Link href="#workflow" className="btn btn-secondary justify-center px-7 py-3 text-sm">
                See how it works
              </Link>
            </div>
            <div className="mt-8 grid max-w-xl grid-cols-3 gap-3 text-xs text-white/35">
              {['Verified captions', 'Structured events', 'Review gate'].map((item) => (
                <div key={item} className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-3">
                  {item}
                </div>
              ))}
            </div>
          </div>
          <DashboardPreview />
        </div>
      </section>

      <section id="workflow" className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-2xl">
            <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.25em] text-teal-300/70">Workflow</p>
            <h2 className="font-heading text-3xl font-black tracking-tight md:text-5xl">From video link to useful work.</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {workflowSteps.map((step, index) => (
              <div key={step.label} className="rounded-3xl border border-white/[0.07] bg-white/[0.03] p-6">
                <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-2xl border border-teal-400/20 bg-teal-400/10 font-heading text-sm font-black text-teal-300">
                  {index + 1}
                </div>
                <h3 className="mb-3 font-heading text-xl font-bold">{step.label}</h3>
                <p className="text-sm leading-7 text-white/45">{step.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 text-center">
            <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.25em] text-teal-300/70">Features</p>
            <h2 className="font-heading text-3xl font-black tracking-tight md:text-5xl">Everything after the transcript.</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {featureCards.map((feature) => (
              <div key={feature.title} className="rounded-3xl border border-white/[0.07] bg-surface-900/40 p-6 transition hover:border-teal-400/25 hover:bg-white/[0.04]">
                <h3 className="mb-3 font-heading text-lg font-bold">{feature.title}</h3>
                <p className="text-sm leading-7 text-white/45">{feature.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="rounded-[2rem] border border-teal-400/15 bg-teal-400/[0.06] p-8">
            <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.25em] text-teal-200/80">Why UVAI</p>
            <h2 className="font-heading text-3xl font-black tracking-tight">Structured intelligence beats another summary.</h2>
            <p className="mt-4 text-sm leading-7 text-white/50">
              The dashboard is built around source provenance, reusable video records, extracted events, and confirmed handoffs so your team can act on verified content.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {reasons.map((reason) => (
              <div key={reason} className="rounded-3xl border border-white/[0.07] bg-white/[0.03] p-6 text-sm leading-7 text-white/55">
                {reason}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <div className="mb-10 text-center">
            <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.25em] text-teal-300/70">FAQ</p>
            <h2 className="font-heading text-3xl font-black tracking-tight md:text-5xl">Questions before the first video.</h2>
          </div>
          <div className="space-y-3">
            {faqs.map((faq) => (
              <div key={faq.question} className="rounded-2xl border border-white/[0.07] bg-white/[0.03] p-5">
                <h3 className="font-heading text-base font-bold">{faq.question}</h3>
                <p className="mt-2 text-sm leading-7 text-white/45">{faq.answer}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="contact" className="px-6 py-20">
        <div className="mx-auto max-w-5xl rounded-[2rem] border border-white/[0.08] bg-white/[0.04] p-8 text-center md:p-12">
          <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.25em] text-teal-300/70">Ready when your next video is</p>
          <h2 className="mx-auto max-w-3xl font-heading text-3xl font-black tracking-tight md:text-5xl">
            Paste a YouTube URL and turn verified source evidence into work your agents can use.
          </h2>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link href="/dashboard" className="btn btn-primary justify-center px-7 py-3 text-sm">
              Open dashboard
            </Link>
            <Link href="/features" className="btn btn-secondary justify-center px-7 py-3 text-sm">
              Explore features
            </Link>
          </div>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
