import Link from 'next/link';
import LandingNav from '@/components/landing/LandingNav';
import Footer from '@/components/Footer';

const workflowSteps = [
  {
    label: 'Paste a video URL',
    detail: 'Start with a YouTube link from a meeting, tutorial, launch, podcast, or customer interview.',
  },
  {
    label: 'Extract intelligence',
    detail: 'UVAI pulls transcript context, topics, decisions, timestamps, sentiment, and action events.',
  },
  {
    label: 'Dispatch agents',
    detail: 'Structured events can power chat, exports, APIs, MCP-compatible agents, and follow-up workflows.',
  },
];

const featureCards = [
  {
    title: 'Video-to-transcript intelligence',
    body: 'Turn raw video links into searchable summaries, chapters, transcript segments, and time-coded context.',
  },
  {
    title: 'Action event extraction',
    body: 'Detect decisions, tasks, requirements, product ideas, risks, and follow-ups as structured events.',
  },
  {
    title: 'Chat with the video',
    body: 'Ask questions against the full video context instead of scrubbing through timelines or notes.',
  },
  {
    title: 'Agent pipeline ready',
    body: 'Route extracted events into MCP-compatible automation for docs, code, research, and operations.',
  },
  {
    title: 'Exports and API workflows',
    body: 'Move intelligence into downstream tools with JSON-style event payloads and integration surfaces.',
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
    answer: 'The app analyzes the content, creates structured insights, and saves the result in your dashboard library.',
  },
  {
    question: 'Do I need to configure agents first?',
    answer: 'No. Start with video analysis, then use the agent pipeline when you want extracted events to trigger downstream work.',
  },
  {
    question: 'Is this just transcription?',
    answer: 'No. Transcription is one input; the product focuses on events, actions, decisions, search, chat, and automation.',
  },
];

function DashboardPreview() {
  return (
    <div className="relative mx-auto w-full max-w-xl rounded-[2rem] border border-white/[0.08] bg-surface-950/90 p-4 shadow-2xl shadow-teal-500/10">
      <div className="mb-4 flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-teal-400" />
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-400/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
        </div>
        <span className="rounded-full border border-teal-400/20 bg-teal-400/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.25em] text-teal-300">
          Live analysis
        </span>
      </div>

      <div className="rounded-2xl border border-teal-400/15 bg-teal-400/[0.04] p-4">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.25em] text-teal-300/80">
          Video URL
        </p>
        <div className="flex items-center gap-3 rounded-xl border border-white/[0.08] bg-black/30 p-3 text-left text-xs text-white/55">
          <span className="h-2 w-2 rounded-full bg-teal-300" />
          youtube.com/watch?v=product-demo
          <span className="ml-auto rounded-lg bg-teal-400 px-3 py-1.5 text-[10px] font-black uppercase text-surface-950">
            Analyze
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] p-4">
          <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.25em] text-white/30">
            Transcript
          </p>
          <div className="space-y-2">
            {['00:14 Launch goal identified', '02:48 Customer pain surfaced', '06:32 Follow-up assigned'].map((line) => (
              <div key={line} className="h-2.5 rounded-full bg-white/[0.09]" title={line} />
            ))}
          </div>
        </div>
        <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] p-4">
          <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.25em] text-white/30">
            Events
          </p>
          <div className="space-y-2 text-[11px] text-white/55">
            <div className="rounded-lg border border-teal-400/15 bg-teal-400/10 px-3 py-2 text-teal-200">
              action_item.created
            </div>
            <div className="rounded-lg border border-cyan-400/15 bg-cyan-400/10 px-3 py-2 text-cyan-200">
              insight.detected
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-white/[0.07] bg-white/[0.03] p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-white/30">Agent pipeline</p>
          <span className="text-[10px] text-teal-300">3 agents ready</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-[10px] text-white/45">
          {['Research', 'Docs', 'Ops'].map((agent) => (
            <div key={agent} className="rounded-xl border border-white/[0.06] bg-black/20 px-2 py-3">
              {agent}
            </div>
          ))}
        </div>
      </div>
    </div>
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
              Turn any video into actions, insights, and agent workflows.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-white/50 md:text-lg">
              UVAI analyzes YouTube videos, extracts structured events, lets you chat with the context, and routes the useful parts into automation.
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
              {['Transcript context', 'Structured events', 'Agent dispatch'].map((item) => (
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
              The dashboard is built around reusable video records, extracted events, and agent handoffs so your team can act on what the video contains.
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
            Paste a YouTube URL and turn passive content into work your agents can use.
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
