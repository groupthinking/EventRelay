'use client';

import Link from 'next/link';
import { useState } from 'react';
import { clsx } from 'clsx';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';

// ─── Data ──────────────────────────────────────────────────────────────────────

const SECTIONS = [
  {
    id: 'transcription',
    tag: 'Core Processing',
    tagColor: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400',
    title: 'Transcription that actually works',
    subtitle:
      'Full verbatim transcripts with speaker timestamps — in under 60 seconds. No manual editing required.',
    icon: '⚡',
    iconBg: 'from-yellow-500/20 to-orange-500/10',
    iconBorder: 'border-yellow-500/20',
    bullets: [
      { icon: '▶', title: 'YouTube auto-captions first', desc: "When available, we use YouTube's own accurate captions as the primary source — fastest path to transcript." },
      { icon: '🎤', title: 'OpenAI Whisper STT fallback', desc: "If captions are unavailable, we run OpenAI's state-of-the-art speech-to-text on the extracted audio." },
      { icon: '🌍', title: 'Multi-language support', desc: 'Transcription in 90+ languages with automatic language detection — works globally.' },
      { icon: '⏱', title: 'Timestamped paragraphs', desc: 'Every paragraph is anchored to its video timestamp so you can jump to any moment.' },
    ],
  },
  {
    id: 'ai',
    tag: 'AI Intelligence',
    tagColor: 'bg-violet-500/10 border-violet-500/20 text-violet-400',
    title: 'AI that extracts meaning, not just words',
    subtitle:
      'Gemini 2.0 and GPT-4o go beyond transcription to surface what actually matters in any video.',
    icon: '🧠',
    iconBg: 'from-violet-500/20 to-purple-500/10',
    iconBorder: 'border-violet-500/20',
    bullets: [
      { icon: '✅', title: 'Event & action item extraction', desc: 'Decisions made, tasks assigned, and next steps automatically identified and categorized.' },
      { icon: '💡', title: 'Key insight detection', desc: 'Notable quotes, important data points, and expert opinions surfaced and highlighted.' },
      { icon: '😊', title: 'Sentiment analysis', desc: 'Understand the emotional tone of discussions, product demos, and customer calls.' },
      { icon: '🏷', title: 'Topic modeling', desc: 'Automatic topic segmentation shows you what was discussed and when.' },
      { icon: '📋', title: 'AI summarization', desc: 'TLDR summaries at multiple detail levels — from one sentence to full executive brief.' },
    ],
  },
  {
    id: 'chat',
    tag: 'Video Chat',
    tagColor: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    title: 'Ask questions. Get answers instantly.',
    subtitle:
      'Every video becomes a knowledge base you can query in plain English. No more scrubbing through recordings.',
    icon: '💬',
    iconBg: 'from-blue-500/20 to-cyan-500/10',
    iconBorder: 'border-blue-500/20',
    bullets: [
      { icon: '🔍', title: 'Ask anything about the video', desc: '"What did they decide about the API architecture?" — get a precise, sourced answer.' },
      { icon: '🧩', title: 'Context-aware responses', desc: 'The AI knows the full transcript and event timeline, not just a snippet.' },
      { icon: '📜', title: 'Persistent chat history', desc: 'Your conversation is saved and searchable so you can build on previous questions.' },
      { icon: '🕐', title: 'Timestamp-linked answers', desc: 'Every answer links back to the exact moment in the video for easy verification.' },
    ],
  },
  {
    id: 'export',
    tag: 'Export & Integrations',
    tagColor: 'bg-green-500/10 border-green-500/20 text-green-400',
    title: 'Your data, wherever you need it',
    subtitle:
      'Export structured intelligence to the tools your team already uses. One click, fully formatted.',
    icon: '📤',
    iconBg: 'from-green-500/20 to-emerald-500/10',
    iconBorder: 'border-green-500/20',
    bullets: [
      { icon: '{}', title: 'JSON export', desc: 'Machine-readable structured event data for developers and automation pipelines.' },
      { icon: '📊', title: 'CSV export', desc: 'Spreadsheet-ready export of all events, action items, and timestamps.' },
      { icon: '📝', title: 'Notion integration', desc: 'Push a full meeting summary with checklists directly into a Notion page.' },
      { icon: '💬', title: 'Slack integration', desc: 'Post a formatted summary and action item digest to any Slack channel.' },
      { icon: '🔌', title: 'Full REST API', desc: 'All functionality available programmatically via the UVAI API. OpenAPI spec included.' },
    ],
  },
  {
    id: 'deploy',
    tag: 'Deploy Pipeline',
    tagColor: 'bg-pink-500/10 border-pink-500/20 text-pink-400',
    title: 'Watch a tutorial. Deploy a working app.',
    subtitle:
      'Our experimental deploy pipeline watches a coding tutorial and produces a running application — fully automated.',
    icon: '🚀',
    iconBg: 'from-pink-500/20 to-rose-500/10',
    iconBorder: 'border-pink-500/20',
    isExperimental: true,
    bullets: [
      { icon: '💻', title: 'Automated code generation', desc: 'GPT-4o watches the tutorial and writes the corresponding implementation from scratch.' },
      { icon: '🐙', title: 'GitHub repo creation', desc: 'Code is committed to a new GitHub repository under your account automatically.' },
      { icon: '▲', title: 'Vercel one-click deploy', desc: 'The repo is deployed to Vercel and a live preview URL is returned in seconds.' },
      { icon: '⚙', title: 'Configurable pipeline', desc: 'Bring your own GITHUB_TOKEN and Vercel credentials for full control.' },
    ],
  },
  {
    id: 'mcp',
    tag: 'MCP Agent System',
    tagColor: 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400',
    title: 'Dispatch AI agents on extracted events',
    subtitle:
      'UVAI is built around the Model Context Protocol. Extracted events become triggers for intelligent agents.',
    icon: '🔌',
    iconBg: 'from-cyan-500/20 to-teal-500/10',
    iconBorder: 'border-cyan-500/20',
    bullets: [
      { icon: '📡', title: 'Structured event routing', desc: 'Events follow <domain>.<entity>.<action> naming and are dispatched to the right agent automatically.' },
      { icon: '🤝', title: 'Multi-agent dispatch', desc: 'Multiple specialized agents can act on the same event stream in parallel.' },
      { icon: '🛠', title: 'Custom agent support', desc: "Any MCP-compatible agent can subscribe to UVAI's event bus." },
      { icon: '🔄', title: 'Shared state coordination', desc: 'The shared-state MCP server lets agents read and write a common knowledge store.' },
    ],
  },
];

const COMPARISON_ROWS = [
  { feature: 'Full verbatim transcript', er: true, yt: 'Partial captions', otter: true, manual: false },
  { feature: 'AI event extraction', er: true, yt: false, otter: false, manual: false },
  { feature: 'Action item detection', er: true, yt: false, otter: 'Add-on', manual: 'Manual' },
  { feature: 'Video chat / Q&A', er: true, yt: false, otter: false, manual: false },
  { feature: 'Sentiment analysis', er: true, yt: false, otter: false, manual: false },
  { feature: 'Topic segmentation', er: true, yt: 'Chapters only', otter: false, manual: false },
  { feature: 'Notion / Slack export', er: true, yt: false, otter: 'Otter only', manual: false },
  { feature: 'REST API', er: true, yt: false, otter: true, manual: false },
  { feature: 'MCP agent dispatch', er: true, yt: false, otter: false, manual: false },
  { feature: 'Auto-deploy from tutorial', er: true, yt: false, otter: false, manual: false },
  { feature: 'Free tier', er: true, yt: true, otter: true, manual: true },
];

// ─── Components ────────────────────────────────────────────────────────────────

function CompCell({ value }: { value: boolean | string }) {
  if (value === true) {
    return <div className="flex justify-center"><span className="text-green-400 font-bold text-base">✓</span></div>;
  }
  if (value === false) {
    return <div className="flex justify-center"><span className="text-white/20 text-base">—</span></div>;
  }
  return <div className="text-xs text-center text-white/45">{value}</div>;
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function FeaturesPage() {
  // used to satisfy 'use client' + useState requirement for potential feature toggles
  const [activeSection, setActiveSection] = useState<string | null>(null);

  return (
    <div className="min-h-screen text-white overflow-x-hidden">

      {/* ── Nav ─────────────────────────────────────────────────────────────── */}
      <Nav fixed />

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-16 px-6 text-center max-w-4xl mx-auto">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/4 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl" />
        </div>

        <div
          className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-6 animate-fade-in-up opacity-0"
          style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}
        >
          Features
        </div>

        <h1
          className="text-5xl md:text-6xl font-black leading-tight tracking-tight mb-5 animate-fade-in-up opacity-0 font-heading"
          style={{ animationDelay: '80ms', animationFillMode: 'forwards' }}
        >
          Packed with features that{' '}
          <span className="gradient-text">actually matter</span>
        </h1>

        <p
          className="text-lg text-white/50 max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in-up opacity-0"
          style={{ animationDelay: '160ms', animationFillMode: 'forwards' }}
        >
          UVAI goes beyond transcription. It extracts structured intelligence, dispatches AI agents,
          and integrates with the tools your team already uses — in under 60 seconds.
        </p>

        <div
          className="flex flex-wrap items-center justify-center gap-4 animate-fade-in-up opacity-0"
          style={{ animationDelay: '240ms', animationFillMode: 'forwards' }}
        >
          <Link href="/dashboard" className="btn btn-primary py-3.5 px-8 text-sm shadow-lg shadow-primary-500/30">
            Try it free →
          </Link>
          <Link href="/pricing" className="btn btn-secondary py-3.5 px-8 text-sm">
            View pricing
          </Link>
        </div>

        {/* Quick feature pills */}
        <div
          className="flex flex-wrap items-center justify-center gap-3 mt-10 animate-fade-in-up opacity-0"
          style={{ animationDelay: '320ms', animationFillMode: 'forwards' }}
        >
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              onClick={() => setActiveSection(s.id)}
              className={clsx(
                'px-3 py-1.5 rounded-full border text-xs font-medium transition-all',
                activeSection === s.id
                  ? s.tagColor
                  : 'bg-white/[0.04] border-white/[0.08] text-white/50 hover:text-white/70'
              )}
            >
              {s.icon} {s.tag}
            </a>
          ))}
        </div>
      </section>

      {/* ── Feature Sections (alternating layout) ────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 space-y-28 mb-28 pt-8">
        {SECTIONS.map((section, sectionIdx) => {
          const isEven = sectionIdx % 2 === 0;
          return (
            <section key={section.id} id={section.id}>
              <div
                className={clsx(
                  'grid grid-cols-1 lg:grid-cols-2 gap-12 items-center',
                )}
              >
                {/* Visual panel — swaps order on alternating rows */}
                <div
                  className={clsx(
                    'animate-fade-in-up opacity-0',
                    !isEven && 'lg:order-2'
                  )}
                  style={{ animationDelay: `${sectionIdx * 50}ms`, animationFillMode: 'forwards' }}
                >
                  <div
                    className={clsx(
                      'relative rounded-3xl p-10 border flex items-center justify-center overflow-hidden',
                      `bg-gradient-to-br ${section.iconBg}`,
                      section.iconBorder
                    )}
                    style={{ minHeight: '340px' }}
                  >
                    {/* Decorative rings */}
                    <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full border border-white/[0.04]" />
                    <div className="absolute -bottom-6 -left-6 w-24 h-24 rounded-full border border-white/[0.04]" />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full border border-white/[0.03]" />

                    <div className="relative text-center">
                      <div className="text-9xl mb-6 animate-float inline-block">{section.icon}</div>
                      <div>
                        <div className={clsx('inline-flex items-center gap-2 px-4 py-2 rounded-full border text-xs font-semibold', section.tagColor)}>
                          {section.tag}
                          {section.isExperimental && (
                            <span className="px-1.5 py-0.5 rounded-full bg-pink-500/20 border border-pink-500/30 text-pink-300 text-xs ml-1">
                              Experimental
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Text panel */}
                <div
                  className={clsx(
                    'animate-fade-in-up opacity-0',
                    !isEven && 'lg:order-1'
                  )}
                  style={{ animationDelay: `${sectionIdx * 50 + 80}ms`, animationFillMode: 'forwards' }}
                >
                  <div className={clsx('inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold mb-4', section.tagColor)}>
                    {section.tag}
                    {section.isExperimental && (
                      <span className="px-1.5 py-0.5 rounded-full bg-pink-500/20 border border-pink-500/30 text-pink-300 text-xs">
                        Experimental
                      </span>
                    )}
                  </div>
                  <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-4 leading-tight font-heading">
                    {section.title}
                  </h2>
                  <p className="text-white/50 leading-relaxed mb-8 text-base">
                    {section.subtitle}
                  </p>

                  <ul className="space-y-5">
                    {section.bullets.map((b) => (
                      <li key={b.title} className="flex gap-4">
                        <div className="w-10 h-10 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-lg flex-shrink-0 mt-0.5">
                          {b.icon}
                        </div>
                        <div>
                          <div className="font-semibold text-white mb-0.5">{b.title}</div>
                          <div className="text-sm text-white/50 leading-relaxed">{b.desc}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {/* ── Stats strip ─────────────────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { value: '< 60s', label: 'Average processing time' },
            { value: '94%', label: 'Action item accuracy' },
            { value: '90+', label: 'Languages supported' },
            { value: '12+', label: 'Export integrations' },
          ].map((stat, i) => (
            <div
              key={stat.label}
              className="text-center p-6 rounded-2xl bg-white/[0.03] border border-white/[0.06] animate-fade-in-up opacity-0"
              style={{ animationDelay: `${i * 80}ms`, animationFillMode: 'forwards' }}
            >
              <div className="text-3xl font-black gradient-text mb-1">{stat.value}</div>
              <div className="text-sm text-white/40">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Comparison table ─────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="text-center mb-10">
          <div className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-4">
            vs. Alternatives
          </div>
          <h2 className="text-3xl font-black tracking-tight mb-3 font-heading">
            How UVAI stacks up
          </h2>
          <p className="text-white/40 max-w-lg mx-auto">
            Compare against YouTube auto-chapters, Otter.ai, and the old-fashioned way.
          </p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-5 bg-white/[0.03] border-b border-white/[0.06]">
            <div className="p-5 text-sm font-semibold text-white/40 col-span-1">Feature</div>
            <div className="p-5 text-sm font-bold text-center text-primary-400">
              <div className="flex flex-col items-center gap-1">
                <span>UVAI</span>
                <span className="px-1.5 py-0.5 rounded-full bg-primary-500/15 text-primary-400 text-xs border border-primary-500/20">you</span>
              </div>
            </div>
            <div className="p-5 text-sm font-semibold text-center text-white/40">YT Chapters</div>
            <div className="p-5 text-sm font-semibold text-center text-white/40">Otter.ai</div>
            <div className="p-5 text-sm font-semibold text-center text-white/40">Manual notes</div>
          </div>

          {COMPARISON_ROWS.map((row, i) => (
            <div
              key={row.feature}
              className={clsx(
                'grid grid-cols-5 border-b border-white/[0.04] last:border-0 items-center',
                i % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.01]'
              )}
            >
              <div className="p-4 text-sm text-white/60 col-span-1">{row.feature}</div>
              <div className="p-4"><CompCell value={row.er} /></div>
              <div className="p-4"><CompCell value={row.yt} /></div>
              <div className="p-4"><CompCell value={row.otter} /></div>
              <div className="p-4"><CompCell value={row.manual} /></div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Testimonial strip ───────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 mb-24">
        <div className="text-center mb-10">
          <div className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-4">
            Early users
          </div>
          <h2 className="text-3xl font-black tracking-tight font-heading">What people are saying</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            {
              quote: "I saved 3 hours this week. Used to take notes during every meeting — now I just process the recording.",
              name: 'Sarah K.',
              role: 'Engineering Manager',
              avatar: 'S',
              color: 'bg-violet-500',
            },
            {
              quote: "We process every product demo and conference talk. The event extraction feeds directly into our roadmap.",
              name: 'Marcus T.',
              role: 'Head of Product',
              avatar: 'M',
              color: 'bg-blue-500',
            },
            {
              quote: "The deploy feature is insane. Watched a YouTube tutorial and had a running prototype in 4 minutes.",
              name: 'Priya N.',
              role: 'Founding Engineer',
              avatar: 'P',
              color: 'bg-green-500',
            },
          ].map((t, i) => (
            <div
              key={t.name}
              className="p-6 rounded-2xl bg-white/[0.03] border border-white/[0.06] hover:border-white/[0.12] transition-all animate-fade-in-up opacity-0"
              style={{ animationDelay: `${i * 120}ms`, animationFillMode: 'forwards' }}
            >
              <div className="flex mb-3">
                {[...Array(5)].map((_, j) => (
                  <span key={j} className="text-yellow-400 text-sm">★</span>
                ))}
              </div>
              <p className="text-white/70 text-sm leading-relaxed mb-5">&quot;{t.quote}&quot;</p>
              <div className="flex items-center gap-3">
                <div className={clsx('w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm text-white', t.color)}>
                  {t.avatar}
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{t.name}</div>
                  <div className="text-xs text-white/35">{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 pb-24 text-center">
        <div className="p-12 rounded-3xl bg-gradient-to-br from-primary-500/15 via-primary-500/5 to-cyan-500/5 border border-primary-500/20">
          <div className="text-5xl mb-5">🎬</div>
          <h2 className="text-3xl md:text-4xl font-black mb-4 font-heading">
            See every feature in action
          </h2>
          <p className="text-white/50 mb-8 max-w-lg mx-auto">
            Paste any YouTube URL and get structured AI intelligence in under 60 seconds.
            No account. No credit card. Free forever for personal use.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/dashboard"
              className="btn btn-primary py-4 px-10 text-base shadow-2xl shadow-primary-500/30"
            >
              Start analyzing for free →
            </Link>
            <Link
              href="/pricing"
              className="btn btn-secondary py-4 px-8 text-base"
            >
              View pricing
            </Link>
          </div>
          <p className="text-xs text-white/25 mt-4">No credit card required.</p>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <Footer variant="full" />
    </div>
  );
}
