import Link from 'next/link';
import ContactForm from './ContactForm';
import { CONTACT_EMAIL } from '@/lib/constants';

/* ═══════════════════════════════════════════
   UVAI — Grounded One-Page Positioning Site
   Reflects only proven repo capabilities.
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
  'Bring Gemini + OpenAI keys',
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
    title: 'Agent analysis',
    body: 'Summary, intent, strategy, and video-aware chat inside the dashboard.',
    tag: 'Live',
  },
];

const CAPABILITY_CARDS = [
  {
    title: 'Transcript pipeline',
    body: 'Start with YouTube captions when available, then fall back to speech-to-text. The output is a usable transcript with timestamps.',
  },
  {
    title: 'Gemini agent passes',
    body: 'Analysis passes cover summary and tasks, intent signals, and strategic insights. The page only describes the active pipeline.',
  },
  {
    title: 'Dashboard and chat',
    body: 'The hosted app exposes workflow templates, async processing, status updates, cached results, and chat over processed video.',
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
    body: 'Transcription, structured extraction, and AI analysis run as a coordinated job with SSE status updates.',
  },
  {
    n: '03',
    title: 'Use the result',
    body: 'Read the transcript, export structured events, review action items, or ask the video follow-up questions.',
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

const TEMPLATE_CARDS = [
  {
    title: 'YouTube tutorial → deployable project',
    body: 'Extract the implementation path from a technical tutorial and turn it into a project plan with code-oriented outputs. Treat deployment as a next step, not a promised one-click finish.',
    tags: ['Engineering', 'Project scaffold'],
    featured: true,
  },
  {
    title: 'Conference talk → action items',
    body: 'Capture decisions, follow-ups, and concrete next steps from long-form business or technical talks.',
    tags: ['Business', 'Tasks'],
  },
  {
    title: 'Podcast → blog post',
    body: 'Turn a long discussion into a structured draft with themes, quotes, and a clear content outline.',
    tags: ['Content', 'Drafting'],
  },
  {
    title: 'Lecture → study notes',
    body: 'Compress educational videos into notes, key ideas, and review material without losing the source context.',
    tags: ['Education', 'Notes'],
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
              { href: '#capabilities', label: 'Capabilities' },
              { href: '#workflow', label: 'Workflow' },
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
          className="relative px-6 py-16 md:py-24"
          style={{
            background:
              'radial-gradient(circle at 30% 20%, rgba(106, 242, 222, 0.07) 0%, transparent 60%)',
          }}
        >
          <div className="max-w-[1200px] mx-auto grid lg:grid-cols-2 gap-12 items-start">
            <div>
              <p className="text-xs tracking-[0.3em] uppercase mb-5" style={{ color: TEAL }}>
                Agentic video execution platform
              </p>
              <h1
                className="font-heading text-4xl md:text-6xl font-bold tracking-tighter mb-6 leading-[1.05]"
                style={{ color: INK }}
              >
                Turn video into{' '}
                <span
                  style={{
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundImage: `linear-gradient(135deg, ${TEAL}, #38fbf7)`,
                  }}
                >
                  structured intelligence.
                </span>
              </h1>
              <p className="text-lg leading-relaxed mb-8 max-w-xl" style={{ color: MUTED }}>
                Paste a YouTube URL. UVAI returns a verbatim transcript, typed events, action items,
                and AI-driven analysis powered by Gemini and OpenAI.
              </p>

              <div className="flex flex-wrap gap-3 mb-8">
                <Link
                  href="/dashboard"
                  className="px-7 py-3 rounded-lg font-bold text-sm transition-all duration-300 active:scale-95"
                  style={{ background: `linear-gradient(135deg, ${TEAL}, ${TEAL_DEEP})`, color: '#002b26' }}
                >
                  Try a YouTube URL
                </Link>
                <a
                  href="#contact"
                  className="px-7 py-3 rounded-lg font-bold text-sm transition-all duration-300"
                  style={{ border: `1px solid ${BORDER}`, color: INK }}
                >
                  Talk through a workflow
                </a>
              </div>

              <ul className="flex flex-wrap gap-2" aria-label="Verified product attributes">
                {TRUST_PILLS.map((p) => (
                  <li
                    key={p}
                    className="text-[11px] uppercase tracking-widest px-3 py-1.5 rounded-full font-semibold"
                    style={{
                      background: 'rgba(106, 242, 222, 0.08)',
                      color: TEAL,
                      border: '1px solid rgba(106, 242, 222, 0.18)',
                    }}
                  >
                    {p}
                  </li>
                ))}
              </ul>
            </div>

            {/* Pipeline preview card */}
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
        <section id="capabilities" className="py-20 px-6" style={{ background: PANEL }}>
          <div className="max-w-[1200px] mx-auto">
            <div className="grid md:grid-cols-2 gap-8 mb-12">
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                  What is real today
                </p>
                <h2
                  className="font-heading text-3xl md:text-4xl font-bold tracking-tighter"
                  style={{ color: INK }}
                >
                  A focused video intelligence stack.
                </h2>
              </div>
              <p className="text-base leading-relaxed self-end" style={{ color: MUTED }}>
                UVAI is not a generic AI wrapper. It is a working YouTube processing pipeline with
                transcript extraction, structured event output, multi-agent analysis, async jobs,
                cache routes, and dashboard workflows.
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

        {/* ─── WORKFLOW ─── */}
        <section id="workflow" className="py-20 px-6">
          <div className="max-w-[1200px] mx-auto">
            <div className="grid md:grid-cols-2 gap-8 mb-12">
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                  How it works
                </p>
                <h2
                  className="font-heading text-3xl md:text-4xl font-bold tracking-tighter"
                  style={{ color: INK }}
                >
                  From URL to usable output.
                </h2>
              </div>
              <p className="text-base leading-relaxed self-end" style={{ color: MUTED }}>
                Keep the first run simple. Pick a template or paste a URL, let the pipeline process
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
        <section id="developers" className="py-20 px-6" style={{ background: PANEL }}>
          <div className="max-w-[1200px] mx-auto">
            <div
              className="rounded-2xl p-10 grid lg:grid-cols-[1fr_1.3fr] gap-10"
              style={{ background: 'rgba(19,19,24,0.65)', border: `1px solid ${BORDER}` }}
            >
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                  Built for operators and developers
                </p>
                <h2
                  className="font-heading text-3xl md:text-4xl font-bold tracking-tighter"
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

        {/* ─── TEMPLATES ─── */}
        <section className="py-20 px-6">
          <div className="max-w-[1200px] mx-auto">
            <div className="grid md:grid-cols-2 gap-8 mb-12">
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                  Workflow starting points
                </p>
                <h2
                  className="font-heading text-3xl md:text-4xl font-bold tracking-tighter"
                  style={{ color: INK }}
                >
                  Templates that match real use cases.
                </h2>
              </div>
              <p className="text-base leading-relaxed self-end" style={{ color: MUTED }}>
                UVAI ships nine workflow templates today. These four are the clearest public
                examples; browse the rest from the dashboard.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-5">
              {TEMPLATE_CARDS.map((t) => (
                <article
                  key={t.title}
                  className="rounded-2xl p-7 transition-all duration-300 hover:-translate-y-0.5"
                  style={{
                    background: t.featured ? 'rgba(106, 242, 222, 0.04)' : 'rgba(19,19,24,0.65)',
                    border: t.featured
                      ? '1px solid rgba(106, 242, 222, 0.25)'
                      : `1px solid ${BORDER}`,
                  }}
                >
                  <h3 className="font-heading text-lg font-bold mb-3" style={{ color: INK }}>
                    {t.title}
                  </h3>
                  <p className="text-sm leading-relaxed mb-5" style={{ color: MUTED }}>
                    {t.body}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {t.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-[10px] uppercase tracking-widest font-bold px-2.5 py-1 rounded-full"
                        style={{
                          background: 'rgba(106, 242, 222, 0.08)',
                          color: TEAL,
                          border: '1px solid rgba(106, 242, 222, 0.18)',
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>

            <div className="mt-8 text-center">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 text-sm font-bold uppercase tracking-widest"
                style={{ color: TEAL }}
              >
                See all templates in the dashboard
                <span aria-hidden>→</span>
              </Link>
            </div>
          </div>
        </section>

        {/* ─── CONTACT ─── */}
        <section id="contact" className="py-20 px-6" style={{ background: PANEL }}>
          <div className="max-w-[1200px] mx-auto grid lg:grid-cols-2 gap-10">
            <div>
              <p className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: TEAL }}>
                Inbound
              </p>
              <h2
                className="font-heading text-3xl md:text-4xl font-bold tracking-tighter mb-5"
                style={{ color: INK }}
              >
                Send the video workflow you want automated.
              </h2>
              <p className="text-base leading-relaxed mb-4" style={{ color: MUTED }}>
                Share the type of video, the output you need, and where the result should go.
                Submitting hands the draft to your browser or local mail app, which fills in a new
                message you can review and send.
              </p>
              <p className="text-sm leading-relaxed mb-7" style={{ color: FAINT }}>
                Privacy note: this page does not submit to our backend. The draft contents are
                handed to your browser or local email app, which formats them as a new message for
                you to review and send.
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
        <div className="flex flex-col md:flex-row justify-between items-center gap-6 max-w-[1200px] mx-auto">
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
