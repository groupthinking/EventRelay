'use client';

import Link from 'next/link';
import { clsx } from 'clsx';

const FEATURE_SECTIONS = [
  {
    icon: '⚡',
    tag: 'Core',
    title: 'Transcription that actually works',
    description: 'We use YouTube\'s own captions first — the fastest and most accurate option for public videos. When unavailable, we fall back to OpenAI Whisper for near-human accuracy.',
    color: 'from-yellow-500/20 to-orange-500/5',
    border: 'border-yellow-500/15',
    points: [
      'YouTube caption extraction (< 3 seconds)',
      'OpenAI Whisper STT fallback for videos without captions',
      'Speaker timestamp alignment',
      'Multi-language support (100+ languages)',
      'Download transcript as .txt',
    ],
    visual: '📝',
    visualBg: 'bg-yellow-500/10',
  },
  {
    icon: '🧠',
    tag: 'AI Intelligence',
    title: 'Extract meaning, not just words',
    description: 'EventRelay runs your transcript through Gemini 2.0 and GPT-4o to extract structured intelligence: events, decisions, topics, and insights — not just a summary.',
    color: 'from-violet-500/20 to-purple-500/5',
    border: 'border-violet-500/15',
    points: [
      'Event extraction with type classification (action, decision, topic, insight)',
      'Confidence scores for every extracted item',
      'Timestamp anchoring to the original video',
      'Sentiment analysis (positive, negative, neutral)',
      'Named entity recognition (people, tools, orgs)',
      'Topic modeling and keyword extraction',
    ],
    visual: '⚡',
    visualBg: 'bg-violet-500/10',
  },
  {
    icon: '✅',
    tag: 'Productivity',
    title: 'Actionable checklists from any video',
    description: 'Every action item mentioned in a video gets turned into a checkbox. Review your to-dos, check them off, and export to your task manager of choice.',
    color: 'from-green-500/20 to-emerald-500/5',
    border: 'border-green-500/15',
    points: [
      'Auto-generated action item checklist',
      'Priority scoring (high / medium / low)',
      'One-click export to Notion, Linear, or plain text',
      'Slack message formatting',
      'Persistent across sessions (Pro)',
    ],
    visual: '✓',
    visualBg: 'bg-green-500/10',
  },
  {
    icon: '💬',
    tag: 'AI Chat',
    title: 'Ask anything about your video',
    description: 'Open the chat panel on any processed video and ask natural language questions. The AI answers with context from the transcript, not the internet.',
    color: 'from-blue-500/20 to-cyan-500/5',
    border: 'border-blue-500/15',
    points: [
      '"What was the key decision at 14:30?"',
      '"Summarize the Q&A section"',
      '"List all tools and technologies mentioned"',
      '"Who were the speakers and what did each discuss?"',
      'Full conversation history',
      'Context-aware follow-up questions',
    ],
    visual: '💬',
    visualBg: 'bg-blue-500/10',
  },
  {
    icon: '📤',
    tag: 'Export',
    title: 'Your data, your format',
    description: 'EventRelay is not a data silo. Export transcripts, events, and insights in whatever format your workflow needs.',
    color: 'from-cyan-500/20 to-teal-500/5',
    border: 'border-cyan-500/15',
    points: [
      'JSON export (structured events + insights)',
      'CSV export (events spreadsheet)',
      'Plain text transcript download',
      'Notion page creation (Pro)',
      'Slack message formatting (Pro)',
      'REST API for programmatic access (Pro)',
    ],
    visual: '↓',
    visualBg: 'bg-cyan-500/10',
  },
  {
    icon: '🚀',
    tag: 'Experimental',
    title: 'Watch a tutorial, deploy an app',
    description: 'Our most experimental feature: paste a YouTube tutorial URL and EventRelay generates a working codebase, creates a GitHub repo, and deploys it to Vercel — fully automated.',
    color: 'from-pink-500/20 to-rose-500/5',
    border: 'border-pink-500/15',
    points: [
      'AI code generation from tutorial content',
      'GitHub repo creation (requires GITHUB_TOKEN)',
      'Vercel deployment (requires Vercel credentials)',
      'Framework detection (React, Next.js, Python, etc.)',
      'Generated file manifest + entry point',
    ],
    visual: '🚀',
    visualBg: 'bg-pink-500/10',
    experimental: true,
  },
  {
    icon: '🔌',
    tag: 'Advanced',
    title: 'MCP agent dispatch system',
    description: 'EventRelay integrates with the Model Context Protocol (MCP) ecosystem. Route extracted events to specialized AI agents for automated follow-through.',
    color: 'from-orange-500/20 to-amber-500/5',
    border: 'border-orange-500/15',
    points: [
      'Event routing to MCP-compatible agents',
      'Multi-agent orchestration',
      'Agent status tracking and progress',
      'Custom agent registry',
      'CloudEvents-compatible event publishing',
      'Extensible with custom agent types',
    ],
    visual: '⚙️',
    visualBg: 'bg-orange-500/10',
  },
];

const COMPARISON = [
  { feature: 'Transcript extraction', eventrelay: true, youtube: 'Partial', otter: true, manual: false },
  { feature: 'Structured event extraction', eventrelay: true, youtube: false, otter: false, manual: false },
  { feature: 'Action item generation', eventrelay: true, youtube: false, otter: 'Partial', manual: true },
  { feature: 'AI video chat', eventrelay: true, youtube: false, otter: false, manual: false },
  { feature: 'Sentiment analysis', eventrelay: true, youtube: false, otter: false, manual: false },
  { feature: 'Topic detection', eventrelay: true, youtube: 'Chapters only', otter: false, manual: false },
  { feature: 'JSON / CSV export', eventrelay: true, youtube: false, otter: 'Paid', manual: false },
  { feature: 'REST API', eventrelay: true, youtube: 'Paid', otter: 'Paid', manual: false },
  { feature: 'MCP agent dispatch', eventrelay: true, youtube: false, otter: false, manual: false },
  { feature: 'Open source', eventrelay: true, youtube: false, otter: false, manual: true },
  { feature: 'Free forever', eventrelay: true, youtube: true, otter: 'Limited', manual: true },
];

function CompareCell({ val }: { val: boolean | string }) {
  if (val === true) return <span className="text-green-400 font-bold">✓</span>;
  if (val === false) return <span className="text-white/20">—</span>;
  return <span className="text-yellow-400 text-xs font-medium">{val}</span>;
}

export default function FeaturesPage() {
  return (
    <div className="min-h-screen text-white overflow-x-hidden">

      {/* ── Nav ─────────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05] bg-surface-950/80 backdrop-blur-xl">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-base shadow-lg shadow-primary-500/25">E</div>
          <span className="font-bold text-lg tracking-tight">EventRelay</span>
          <span className="hidden sm:block px-2 py-0.5 rounded-full bg-primary-500/15 text-primary-400 text-xs font-semibold border border-primary-500/20">BETA</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link href="/features" className="hidden md:block text-sm text-white/80 hover:text-white transition px-3 py-2">Features</Link>
          <Link href="/pricing" className="hidden md:block text-sm text-white/50 hover:text-white transition px-3 py-2">Pricing</Link>
          <Link href="/dashboard" className="btn btn-secondary py-2 px-4 text-sm">Dashboard</Link>
          <Link href="/dashboard" className="btn btn-primary py-2 px-4 text-sm">Get started free →</Link>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <section className="pt-32 pb-16 px-6 text-center max-w-4xl mx-auto">
        <div className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-6 animate-fade-in-up opacity-0" style={{ animationFillMode: 'forwards' }}>
          Features
        </div>
        <h1 className="text-5xl md:text-6xl font-black tracking-tight mb-5 animate-fade-in-up opacity-0" style={{ animationDelay: '80ms', animationFillMode: 'forwards' }}>
          Packed with features that<br />
          <span className="gradient-text">actually matter</span>
        </h1>
        <p className="text-lg text-white/50 max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in-up opacity-0" style={{ animationDelay: '160ms', animationFillMode: 'forwards' }}>
          EventRelay doesn't just transcribe. It extracts, structures, and acts on video content
          so you never have to take notes again.
        </p>
        <div className="flex flex-wrap gap-3 justify-center animate-fade-in-up opacity-0" style={{ animationDelay: '240ms', animationFillMode: 'forwards' }}>
          <Link href="/dashboard" className="btn btn-primary py-3.5 px-8 text-sm shadow-xl shadow-primary-500/25">Try it now — free →</Link>
          <Link href="/pricing" className="btn btn-secondary py-3.5 px-8 text-sm">See pricing</Link>
        </div>
      </section>

      {/* ── Feature Sections ────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 mb-24 space-y-8">
        {FEATURE_SECTIONS.map((section, i) => (
          <div
            key={section.title}
            className={clsx(
              'relative p-8 md:p-10 rounded-3xl border transition-all animate-fade-in-up opacity-0',
              `bg-gradient-to-br ${section.color}`,
              section.border,
            )}
            style={{ animationDelay: `${i * 60}ms`, animationFillMode: 'forwards' }}
          >
            {section.experimental && (
              <div className="absolute top-6 right-6 px-3 py-1 rounded-full bg-yellow-500/15 border border-yellow-500/25 text-yellow-400 text-xs font-bold">
                Experimental
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              <div className={i % 2 === 1 ? 'md:order-2' : ''}>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">{section.icon}</span>
                  <span className="text-xs font-semibold text-white/40 uppercase tracking-widest">{section.tag}</span>
                </div>
                <h2 className="text-2xl md:text-3xl font-black mb-4 leading-tight">{section.title}</h2>
                <p className="text-white/55 text-sm leading-relaxed mb-6">{section.description}</p>
                <ul className="space-y-2.5">
                  {section.points.map((point) => (
                    <li key={point} className="flex items-start gap-2.5 text-sm text-white/65">
                      <span className="text-primary-400 mt-0.5 flex-shrink-0 font-bold">✓</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className={clsx('flex items-center justify-center', i % 2 === 1 ? 'md:order-1' : '')}>
                <div className={clsx(
                  'w-40 h-40 rounded-3xl flex items-center justify-center text-7xl',
                  section.visualBg,
                  'border border-white/[0.08]',
                )}>
                  {section.visual}
                </div>
              </div>
            </div>
          </div>
        ))}
      </section>

      {/* ── Comparison Table ────────────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <div className="text-center mb-10">
          <div className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-4">
            Comparison
          </div>
          <h2 className="text-3xl font-black tracking-tight mb-3">EventRelay vs. the alternatives</h2>
          <p className="text-white/40 text-sm">Why copy-paste from YouTube when you can extract intelligence?</p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] overflow-hidden">
          <div className="grid grid-cols-5 bg-white/[0.03] border-b border-white/[0.06]">
            <div className="p-4 text-sm font-semibold text-white/40">Feature</div>
            <div className="p-4 text-sm font-bold text-center text-primary-400">EventRelay</div>
            <div className="p-4 text-sm font-semibold text-center text-white/40">YouTube</div>
            <div className="p-4 text-sm font-semibold text-center text-white/40">Otter.ai</div>
            <div className="p-4 text-sm font-semibold text-center text-white/40">Manual</div>
          </div>
          {COMPARISON.map((row, i) => (
            <div
              key={row.feature}
              className={clsx('grid grid-cols-5 border-b border-white/[0.04] last:border-0', i % 2 === 0 ? '' : 'bg-white/[0.01]')}
            >
              <div className="p-4 text-sm text-white/60">{row.feature}</div>
              <div className="p-4 text-sm text-center"><CompareCell val={row.eventrelay} /></div>
              <div className="p-4 text-sm text-center"><CompareCell val={row.youtube} /></div>
              <div className="p-4 text-sm text-center"><CompareCell val={row.otter} /></div>
              <div className="p-4 text-sm text-center"><CompareCell val={row.manual} /></div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 pb-24 text-center">
        <div className="p-12 rounded-3xl bg-gradient-to-br from-primary-500/15 via-primary-500/5 to-cyan-500/5 border border-primary-500/20">
          <h2 className="text-3xl md:text-4xl font-black mb-4">See it for yourself</h2>
          <p className="text-white/50 mb-8 max-w-lg mx-auto">
            No setup. No account. Paste a YouTube URL and watch EventRelay extract intelligence in under 60 seconds.
          </p>
          <Link href="/dashboard" className="btn btn-primary py-4 px-10 text-base shadow-2xl shadow-primary-500/30 inline-block">
            Start analyzing — it&apos;s free →
          </Link>
          <div className="flex flex-wrap justify-center gap-4 mt-5">
            <Link href="/pricing" className="text-xs text-white/30 hover:text-white/50 transition underline underline-offset-2">See pricing</Link>
            <Link href="/playground" className="text-xs text-white/30 hover:text-white/50 transition underline underline-offset-2">API Docs</Link>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/[0.06] py-8">
        <div className="max-w-5xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-white/25">
          <span>© 2026 EventRelay. MIT License.</span>
          <div className="flex items-center gap-4">
            <Link href="/" className="hover:text-white/50 transition">Home</Link>
            <Link href="/pricing" className="hover:text-white/50 transition">Pricing</Link>
            <Link href="/dashboard" className="hover:text-white/50 transition">Dashboard</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
