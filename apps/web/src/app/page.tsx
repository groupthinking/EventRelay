import Link from 'next/link';
import ContactForm from './ContactForm';
import { CONTACT_EMAIL } from '@/lib/constants';

/* ═══════════════════════════════════════════
   UVAI — Video to Action Landing Page
   Producer.ai-style centered hero with URL
   input box. Reflects "action layer" positioning.
   ═══════════════════════════════════════════ */

const TEAL = '#6af2de';
const TEAL_DEEP = '#10b7a5';
const INK = '#f8f5fd';
const BG = '#0e0e13';
const PANEL = '#131318';
const BORDER = 'rgba(72, 71, 77, 0.18)';
const MUTED = 'rgba(248,245,253,0.55)';
const FAINT = 'rgba(248,245,253,0.35)';

const TRUST_PILLS = [
  'Open source',
  'MIT licensed',
  'Self-hostable',
  'OpenAPI included',
  'Bring your own keys',
];

const STARTER_TEMPLATES = [
  {
    icon: '▶',
    title: 'Tutorial → deployable project',
    prompt: 'Turn this tutorial into a project plan with code steps and deployment path',
    tags: ['Engineering'],
  },
  {
    icon: '◉',
    title: 'Conference talk → action items',
    prompt: 'Extract decisions, follow-ups, and next steps from this talk',
    tags: ['Business'],
  },
  {
    icon: '◈',
    title: 'Podcast → blog post',
    prompt: 'Turn this conversation into a structured draft with themes and quotes',
    tags: ['Content'],
  },
  {
    icon: '◎',
    title: 'Product demo → feature tickets',
    prompt: 'Extract the features shown and generate implementation tickets',
    tags: ['Product'],
  },
  {
    icon: '◇',
    title: 'Lecture → study notes',
    prompt: 'Compress this lecture into notes, key ideas, and review questions',
    tags: ['Education'],
  },
];

const PIPELINE_ROWS = [
  {
    n: '01',
    title: 'Transcript',
    body: 'YouTube captions first, speech-to-text fallback when captions are missing.',
    tag: 'Ready',
  },
  {
    n: '02',
    title: 'Typed events',
    body: 'Decisions, tasks, topics, and key moments returned as schema-bound JSON.',
    tag: 'Strict',
  },
  {
    n: '03',
    title: 'Agent execution',
    body: 'Summary, intent, strategy, and video-aware chat that takes action on the output.',
    tag: 'Live',
  },
];

const CAPABILITY_CARDS = [
  {
    title: 'Transcript pipeline',
    body: 'Start with YouTube captions when available, then fall back to speech-to-text. The output is a timestamped transcript ready for downstream processing.',
  },
  {
    title: 'Gemini agent passes',
    body: 'Analysis passes cover summary and tasks, intent signals, and strategic insights. Agents act on what they find, not just report it.',
  },
  {
    title: 'Dashboard and execution',
    body: 'Workflow templates, async processing, status updates, cached results, and video-aware chat — all wired to take the next step, not just display the output.',
  },
];

const STEPS = [
  {
    n: '01',
    title: 'Paste a YouTube URL',
    body: 'Use the hosted dashboard or run the open-source project with your own Gemini and OpenAI keys.',
  },
  {
    n: '02',
    title: 'Watch the pipeline run',
    body: 'Transcription, structured extraction, and AI analysis run as a coordinated job with real-time status updates.',
  },
  {
    n: '03',
    title: 'Take action on the result',
    body: 'Read the transcript, export structured events, review action items, or ask the video follow-up questions — then execute.',
  },
];

const DEVELOPER_ITEMS = [
  {
    head: 'FastAPI backend with OpenAPI docs',
    body: 'Use the API directly, inspect the contract, or extend the processing routes.',
  },
  {
    head: 'Next.js dashboard',
    body: 'A working hosted interface for URL input, templates, status, results, and video chat.',
  },
  {
    head: 'Self-hostable deployment paths',
    body: 'Docker, Cloud Run, Railway, and Vercel configs are present for teams that want their own stack.',
  },
  {
    head: 'MIT licensed source',
    body: 'EventRelay is the open-source repo name; UVAI is the live product brand.',
  },
];

const REPO_URL = 'https://github.com/groupthinking/EventRelay';

export default function Home() {
  return (
    <div className="min-h-screen text-white" style={{ background: BG }}>
      {/* ─── NAV ─── */}
      <nav
        className="fixed top-0 w-full z-50"
        style={{
          background: 'rgba(14, 14, 19, 0.85)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: `1px solid ${BORDER}`,
        }}
      >
        <div className="flex justify-between items-center px-6 py-4 max-w-[1200px] mx-auto">
          <Link href="/" className="flex items-center gap-2">
            <span
              className="inline-flex items-center justify-center w-8 h-8 rounded-lg"
              style={{ border: `2px solid ${TEAL}`, color: TEAL }}
              aria-hidden
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z" />
              </svg>
            </span>
            <span className="text-xl font-black tracking-tight font-heading" style={{ color: INK }}>
              UVAI
            </span>
          </Link>
          <div className="hidden md:flex gap-7 items-center">
            {[
              { href: '#how-it-works', label: 'How it works' },
              { href: '#capabilities', label: 'Capabilities' },
              { href: '#developers', label: 'Developers' },
              { href: '#contact', label: 'Contact' },
            ].map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="text-sm transition-colors duration-300 hover:opacity-100"
                style={{ color: 'rgba(248,245,253,0.6)' }}
              >
                {l.label}
              </a>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex px-4 py-2 rounded-md text-sm font-bold transition-all duration-200"
              style={{ border: `1px solid ${BORDER}`, color: INK }}
            >
              GitHub
            </a>
            <Link
              href="/dashboard"
              className="px-5 py-2 rounded-md font-bold text-sm transition-all duration-300 active:scale-95"
              style={{ background: `linear-gradient(135deg, ${TEAL}, ${TEAL_DEEP})`, color: '#002b26' }}
            >
              Open dashboard
            </Link>
          </div>
        </div>
      </nav>

      <main className="pt-24 overflow-x-hidden">
        {/* ─── HERO ─── */}
        <section
          id="top"
          className="relative px-6 pt-16 pb-10 md:pt-24 md:pb-14"
          style={{
            background:
              'radial-gradient(circle at 50% 10%, rgba(106, 242, 222, 0.07) 0%, transparent 65%)',
          }}
        >
          <div className="max-w-[860px] mx-auto flex flex-col items-center text-center">
            {/* Eyebrow */}
            <p
              className="text-xs tracking-[0.3em] uppercase mb-5 px-4 py-2 rounded-full"
              style={{
                color: TEAL,
                background: 'rgba(106, 242, 222, 0.08)',
                border: '1px solid rgba(106, 242, 222, 0.18)',
              }}
            >
              The action layer for video
            </p>

            {/* Headline */}
            <h1
              className="font-heading text-4xl md:text-6xl lg:text-7xl font-bold tracking-tighter mb-5 leading-[1.05] text-balance"
              style={{ color: INK }}
            >
              Paste a video.{' '}
              <span
                style={{
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundImage: `linear-gradient(135deg, ${TEAL}, #38fbf7)`,
                }}
              >
                Build from it.
              </span>
            </h1>

            {/* Sub-headline */}
            <p className="text-lg leading-relaxed mb-10 max-w-[600px] text-pretty" style={{ color: MUTED }}>
              YouTube native search only shows you what exists. UVAI takes what is{' '}
              <em>inside</em> a video — the tools, concepts, workflows — and{' '}
              <strong style={{ color: INK }}>executes on them</strong>. Transcripts, typed events,
              action items, and agentic builds powered by Gemini and OpenAI.
            </p>

            {/* ── URL Input Box (producer.ai-style) ── */}
            <div
              className="w-full max-w-[680px] rounded-2xl p-4 mb-4"
              style={{
                background: 'rgba(19, 19, 24, 0.8)',
                border: `1px solid rgba(106, 242, 222, 0.25)`,
                backdropFilter: 'blur(20px)',
                boxShadow: '0 0 60px -20px rgba(106, 242, 222, 0.15)',
              }}
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="flex-1 flex items-center gap-2 px-4 py-3 rounded-xl"
                  style={{ background: 'rgba(14,14,19,0.8)', border: `1px solid ${BORDER}` }}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    style={{ color: TEAL, flexShrink: 0 }}
                  >
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  <span className="text-sm flex-1" style={{ color: FAINT }}>
                    Paste a YouTube URL to build from…
                  </span>
                </div>
                <Link
                  href="/dashboard"
                  className="px-5 py-3 rounded-xl font-bold text-sm transition-all duration-300 active:scale-95 whitespace-nowrap"
                  style={{ background: `linear-gradient(135deg, ${TEAL}, ${TEAL_DEEP})`, color: '#002b26' }}
                >
                  Run pipeline
                </Link>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs" style={{ color: FAINT }}>
                  Try a starter:
                </span>
                {['Tutorial → project', 'Talk → action items', 'Demo → tickets'].map((s) => (
                  <Link
                    key={s}
                    href="/dashboard"
                    className="text-xs px-3 py-1.5 rounded-full transition-colors duration-200 hover:opacity-80"
                    style={{
                      background: 'rgba(106, 242, 222, 0.07)',
                      color: TEAL,
                      border: '1px solid rgba(106, 242, 222, 0.15)',
                    }}
                  >
                    {s}
                  </Link>
                ))}
              </div>
            </div>

            {/* Trust pills */}
            <ul className="flex flex-wrap gap-2 justify-center" aria-label="Verified product attributes">
              {TRUST_PILLS.map((p) => (
                <li
                  key={p}
                  className="text-[11px] uppercase tracking-widest px-3 py-1.5 rounded-full font-semibold"
                  style={{
                    background: 'rgba(106, 242, 222, 0.06)',
                    color: FAINT,
                    border: `1px solid ${BORDER}`,
                  }}
                >
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ─── STARTERS ─── */}
        <section className="px-6 pb-20" style={{ background: BG }}>
          <div className="max-w-[1100px] mx-auto">
            <p
              className="text-[10px] tracking-[0.3em] uppercase mb-6 text-center"
              style={{ color: FAINT }}
            >
              Workflow starters
            </p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {STARTER_TEMPLATES.map((t) => (
                <Link
                  key={t.title}
                  href="/dashboard"
                  className="group rounded-xl p-5 flex flex-col gap-3 transition-all duration-300 hover:-translate-y-0.5"
                  style={{
                    background: 'rgba(19,19,24,0.65)',
                    border: `1px solid ${BORDER}`,
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className="text-lg font-bold leading-none"
                      style={{ color: TEAL, fontFamily: 'monospace' }}
                    >
                      {t.icon}
                    </span>
                    <div className="flex gap-1.5">
                      {t.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[9px] uppercase tracking-widest font-bold px-2 py-0.5 rounded-full"
                          style={{
                            background: 'rgba(106, 242, 222, 0.08)',
                            color: TEAL,
                            border: '1px solid rgba(106, 242, 222, 0.15)',
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <h3 className="font-heading text-sm font-bold leading-snug" style={{ color: INK }}>
                    {t.title}
                  </h3>
                  <p className="text-xs leading-relaxed" style={{ color: FAINT }}>
                    {t.prompt}
                  </p>
                  <div className="mt-auto flex items-center gap-1.5 text-xs font-semibold" style={{ color: TEAL }}>
                    <span>Use template</span>
                    <span className="transition-transform duration-200 group-hover:translate-x-0.5" aria-hidden>→</span>
                  </div>
                </Link>
              ))}
              {/* Browse all */}
              <Link
                href="/dashboard"
                className="group rounded-xl p-5 flex flex-col items-center justify-center gap-2 transition-all duration-300 hover:-translate-y-0.5"
                style={{
                  background: 'rgba(106, 242, 222, 0.03)',
                  border: `1px dashed rgba(106, 242, 222, 0.2)`,
                }}
              >
                <span className="text-2xl font-bold" style={{ color: TEAL, opacity: 0.6 }}>+</span>
                <span className="text-xs font-semibold text-center" style={{ color: TEAL }}>
                  Browse all 9 templates
                </span>
                <span className="text-xs text-center" style={{ color: FAINT }}>
                  in the dashboard
                </span>
              </Link>
            </div>
          </div>
        </section>

        {/* ─── WHAT UVAI DOES ─── */}
        <section
          className="py-20 px-6"
          style={{
            background: PANEL,
            borderTop: `1px solid ${BORDER}`,
            borderBottom: `1px solid ${BORDER}`,
          }}
        >
          <div className="max-w-[1100px] mx-auto grid md:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                The gap we fill
              </p>
              <h2
                className="font-heading text-3xl md:text-4xl font-bold tracking-tighter mb-5 text-balance"
                style={{ color: INK }}
              >
                YouTube shows you what exists. We build from what&apos;s inside.
              </h2>
              <p className="text-base leading-relaxed mb-6" style={{ color: MUTED }}>
                The native YouTube experience gives you search, recommendations, and a chat
                assistant that can summarize. It does not let you take action on the content —
                no connection made, no output generated, no next step executed.
              </p>
              <p className="text-base leading-relaxed" style={{ color: MUTED }}>
                UVAI is the action layer. It takes the tools, concepts, workflows, and insights
                inside a video and <strong style={{ color: INK }}>builds from them</strong>:
                structured events, implementation plans, agent-driven tasks, and
                code-ready output — all from a single URL paste.
              </p>
            </div>
            {/* Pipeline preview */}
            <aside
              aria-label="UVAI processing pipeline preview"
              className="rounded-2xl overflow-hidden"
              style={{
                background: 'rgba(19, 19, 24, 0.7)',
                border: `1px solid ${BORDER}`,
                backdropFilter: 'blur(20px)',
              }}
            >
              <div
                className="flex items-center justify-between px-5 py-3"
                style={{ borderBottom: `1px solid ${BORDER}`, background: 'rgba(255,255,255,0.02)' }}
              >
                <div className="flex gap-1.5" aria-hidden>
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#3a3a44' }} />
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#3a3a44' }} />
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#3a3a44' }} />
                </div>
                <span className="text-xs uppercase tracking-widest" style={{ color: FAINT }}>
                  Pipeline run
                </span>
              </div>
              <div className="divide-y" style={{ borderColor: BORDER }}>
                {PIPELINE_ROWS.map((row) => (
                  <article
                    key={row.n}
                    className="flex items-start gap-4 px-5 py-5"
                    style={{ borderTop: `1px solid ${BORDER}` }}
                  >
                    <span
                      className="font-heading text-sm font-bold"
                      style={{ color: TEAL, minWidth: 28 }}
                    >
                      {row.n}
                    </span>
                    <div className="flex-1">
                      <h3
                        className="font-heading text-base font-bold mb-1"
                        style={{ color: INK }}
                      >
                        {row.title}
                      </h3>
                      <p className="text-sm leading-relaxed" style={{ color: MUTED }}>
                        {row.body}
                      </p>
                    </div>
                    <span
                      className="text-[10px] uppercase tracking-widest font-bold px-2 py-1 rounded-md"
                      style={{
                        background: 'rgba(106, 242, 222, 0.1)',
                        color: TEAL,
                        border: '1px solid rgba(106, 242, 222, 0.2)',
                      }}
                    >
                      {row.tag}
                    </span>
                  </article>
                ))}
              </div>
            </aside>
          </div>
        </section>

        {/* ─── CAPABILITIES ─── */}
        <section id="capabilities" className="scroll-mt-24 py-20 px-6">
          <div className="max-w-[1100px] mx-auto">
            <div className="grid md:grid-cols-2 gap-8 mb-12">
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                  What is real today
                </p>
                <h2
                  className="font-heading text-3xl md:text-4xl font-bold tracking-tighter text-balance"
                  style={{ color: INK }}
                >
                  A focused video action stack.
                </h2>
              </div>
              <p className="text-base leading-relaxed self-end" style={{ color: MUTED }}>
                UVAI is not a generic AI wrapper. It is a working YouTube processing pipeline with
                transcript extraction, structured event output, multi-agent analysis, async jobs,
                and execution hooks that turn results into deliverables.
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <article
                className="rounded-2xl p-8"
                style={{ background: 'rgba(25,25,31,0.7)', border: `1px solid ${BORDER}` }}
              >
                <h3 className="font-heading text-xl font-bold mb-3" style={{ color: INK }}>
                  Structured event extraction
                </h3>
                <p className="text-sm leading-relaxed mb-6" style={{ color: MUTED }}>
                  The system turns video content into typed, machine-readable output: action items,
                  decisions, topics, timestamps, and key insights. That makes the result usable by
                  people, APIs, and downstream automation.
                </p>
                <div className="rounded-xl p-5" style={{ background: 'rgba(14,14,19,0.6)', border: `1px solid ${BORDER}` }}>
                  {[
                    { k: 'transcript', v: 'timestamped text' },
                    { k: 'events', v: 'typed JSON' },
                    { k: 'actions', v: 'owner-ready tasks' },
                    { k: 'chat', v: 'ask the video' },
                  ].map((row, i, arr) => (
                    <div
                      key={row.k}
                      className="flex justify-between items-center py-2.5"
                      style={i < arr.length - 1 ? { borderBottom: `1px solid ${BORDER}` } : undefined}
                    >
                      <strong className="font-mono text-sm font-bold" style={{ color: TEAL }}>
                        {row.k}
                      </strong>
                      <span className="text-xs uppercase tracking-widest" style={{ color: FAINT }}>
                        {row.v}
                      </span>
                    </div>
                  ))}
                </div>
              </article>

              <div className="grid gap-6">
                {CAPABILITY_CARDS.map((c) => (
                  <article
                    key={c.title}
                    className="rounded-2xl p-7"
                    style={{ background: 'rgba(25,25,31,0.7)', border: `1px solid ${BORDER}` }}
                  >
                    <h3 className="font-heading text-lg font-bold mb-2" style={{ color: INK }}>
                      {c.title}
                    </h3>
                    <p className="text-sm leading-relaxed" style={{ color: MUTED }}>
                      {c.body}
                    </p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ─── HOW IT WORKS ─── */}
        <section id="how-it-works" className="scroll-mt-24 py-20 px-6" style={{ background: PANEL }}>
          <div className="max-w-[1100px] mx-auto">
            <div className="grid md:grid-cols-2 gap-8 mb-12">
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                  How it works
                </p>
                <h2
                  className="font-heading text-3xl md:text-4xl font-bold tracking-tighter text-balance"
                  style={{ color: INK }}
                >
                  From URL to usable output.
                </h2>
              </div>
              <p className="text-base leading-relaxed self-end" style={{ color: MUTED }}>
                Keep the first run simple. Pick a starter or paste a URL, let the pipeline process
                the video, then use the output in the dashboard or through the API.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {STEPS.map((s) => (
                <article
                  key={s.n}
                  className="rounded-2xl p-7"
                  style={{ background: 'rgba(19,19,24,0.65)', border: `1px solid ${BORDER}` }}
                >
                  <p
                    className="font-heading text-4xl font-black mb-4"
                    style={{ color: 'rgba(106, 242, 222, 0.18)' }}
                  >
                    {s.n}
                  </p>
                  <h3 className="font-heading text-lg font-bold mb-2" style={{ color: INK }}>
                    {s.title}
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ color: MUTED }}>
                    {s.body}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ─── DEVELOPERS ─── */}
        <section id="developers" className="scroll-mt-24 py-20 px-6">
          <div className="max-w-[1100px] mx-auto">
            <div
              className="rounded-2xl p-10 grid lg:grid-cols-[1fr_1.3fr] gap-10"
              style={{ background: 'rgba(19,19,24,0.65)', border: `1px solid ${BORDER}` }}
            >
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                  Built for operators and developers
                </p>
                <h2
                  className="font-heading text-3xl md:text-4xl font-bold tracking-tighter text-balance"
                  style={{ color: INK }}
                >
                  Open where it matters.
                </h2>
              </div>
              <ul className="grid gap-5">
                {DEVELOPER_ITEMS.map((d) => (
                  <li
                    key={d.head}
                    className="grid sm:grid-cols-[minmax(0,260px)_1fr] gap-x-6 gap-y-1 pb-5"
                    style={{ borderBottom: `1px solid ${BORDER}` }}
                  >
                    <strong className="font-heading text-sm font-bold" style={{ color: INK }}>
                      {d.head}
                    </strong>
                    <span className="text-sm leading-relaxed" style={{ color: MUTED }}>
                      {d.body}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ─── CONTACT ─── */}
        <section id="contact" className="scroll-mt-24 py-20 px-6" style={{ background: PANEL }}>
          <div className="max-w-[1100px] mx-auto grid lg:grid-cols-2 gap-10">
            <div>
              <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                Inbound
              </p>
              <h2
                className="font-heading text-3xl md:text-4xl font-bold tracking-tighter mb-5 text-balance"
                style={{ color: INK }}
              >
                Tell us the video workflow you want executed.
              </h2>
              <p className="text-base leading-relaxed mb-4" style={{ color: MUTED }}>
                Share the type of video, the output you need, and where the result should go.
                Submitting hands the draft to your browser or local mail app, which fills in a new
                message you can review and send.
              </p>
              <p className="text-sm leading-relaxed mb-7" style={{ color: FAINT }}>
                Privacy note: this page does not submit to our backend. The draft contents are
                handed to your browser or local email app.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/dashboard"
                  className="px-6 py-3 rounded-lg font-bold text-sm transition-all duration-300 active:scale-95"
                  style={{ background: `linear-gradient(135deg, ${TEAL}, ${TEAL_DEEP})`, color: '#002b26' }}
                >
                  Open dashboard
                </Link>
                <a
                  href={REPO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-6 py-3 rounded-lg font-bold text-sm transition-all duration-300"
                  style={{ border: `1px solid ${BORDER}`, color: INK }}
                >
                  View source
                </a>
              </div>
            </div>

            <ContactForm />
          </div>
        </section>
      </main>

      {/* ─── FOOTER ─── */}
      <footer
        className="py-10 px-6"
        style={{ borderTop: `1px solid ${BORDER}`, background: BG }}
      >
        <div className="flex flex-col md:flex-row justify-between items-center gap-6 max-w-[1100px] mx-auto">
          <p className="text-sm" style={{ color: FAINT }}>
            © 2026 UVAI. EventRelay open-source project, MIT licensed.
          </p>
          <div className="flex gap-6">
            <Link href="/dashboard" className="text-sm" style={{ color: FAINT }}>
              Dashboard
            </Link>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm"
              style={{ color: FAINT }}
            >
              GitHub
            </a>
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-sm" style={{ color: FAINT }}>
              Contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
