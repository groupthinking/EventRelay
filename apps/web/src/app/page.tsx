'use client';

import Link from 'next/link';
import { useState, useCallback, useEffect } from 'react';
import { clsx } from 'clsx';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/ui/Toast';

// ─── URL Validation ────────────────────────────────────────────────────────────
function validateVideoUrl(url: string): string | null {
  if (!url.trim()) {
    return 'Please enter a video URL';
  }

  try {
    // Try to parse as URL
    new URL(url);
  } catch {
    return 'Please enter a valid URL';
  }

  // Check if it's a recognized video platform
  const videoPatterns = [
    /youtube\.com/i,
    /youtu\.be/i,
    /drive\.google\.com/i,
    /vimeo\.com/i,
    /loom\.com/i,
    /\.mp4$/i,
    /\.webm$/i,
  ];

  if (!videoPatterns.some(pattern => pattern.test(url))) {
    return 'URL must be from a supported platform (YouTube, Google Drive, Vimeo, etc.) or a direct video link';
  }

  return null;
}

// ─── Typewriter Hook ───────────────────────────────────────────────────────────
function useTypewriter(words: string[], speed = 80, pause = 2200) {
  const [displayed, setDisplayed] = useState('');
  const [wordIdx, setWordIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const current = words[wordIdx % words.length];
    const timeout = setTimeout(() => {
      if (!deleting) {
        setDisplayed(current.slice(0, charIdx + 1));
        if (charIdx + 1 === current.length) {
          setTimeout(() => setDeleting(true), pause);
        } else {
          setCharIdx((c) => c + 1);
        }
      } else {
        setDisplayed(current.slice(0, charIdx - 1));
        if (charIdx - 1 === 0) {
          setDeleting(false);
          setWordIdx((w) => (w + 1) % words.length);
          setCharIdx(0);
        } else {
          setCharIdx((c) => c - 1);
        }
      }
    }, deleting ? speed / 2 : speed);
    return () => clearTimeout(timeout);
  }, [charIdx, deleting, wordIdx, words, speed, pause]);

  return displayed;
}

// ─── Data ──────────────────────────────────────────────────────────────────────
const USE_CASES = [
  'team meetings',
  'product demos',
  'conference talks',
  'tutorials',
  'podcasts',
  'investor pitches',
  'training videos',
  'webinars',
];

const FEATURES = [
  {
    icon: '⚡',
    title: 'Instant Transcription',
    desc: 'Full verbatim transcripts with speaker timestamps in under 60 seconds. YouTube captions + OpenAI STT fallback.',
    color: 'from-yellow-500/20 to-orange-500/10',
    border: 'border-yellow-500/20',
    tag: 'Core',
  },
  {
    icon: '🧠',
    title: 'AI Event Extraction',
    desc: 'Automatically identifies actions, decisions, topics, and insights. Powered by Gemini 2.0 and GPT-4o.',
    color: 'from-violet-500/20 to-purple-500/10',
    border: 'border-violet-500/20',
    tag: 'AI',
  },
  {
    icon: '✅',
    title: 'Actionable Checklists',
    desc: 'Every action item extracted and turned into a checkbox. Export to Notion, Slack, or your task manager.',
    color: 'from-green-500/20 to-emerald-500/10',
    border: 'border-green-500/20',
    tag: 'Productivity',
  },
  {
    icon: '💬',
    title: 'Video Chat',
    desc: 'Ask questions about any video. "What did they decide at 14:30?" "Summarize the Q&A section."',
    color: 'from-blue-500/20 to-cyan-500/10',
    border: 'border-blue-500/20',
    tag: 'AI Chat',
  },
  {
    icon: '🚀',
    title: 'One-Click Deploy',
    desc: 'Watch a tutorial then deploy a running app from it. Code generation + GitHub + Vercel, all automated.',
    color: 'from-pink-500/20 to-rose-500/10',
    border: 'border-pink-500/20',
    tag: 'Superpower',
  },
  {
    icon: '🔌',
    title: 'MCP Agent Dispatch',
    desc: 'Dispatch specialized AI agents to act on extracted events. Integrates with any MCP-compatible system.',
    color: 'from-cyan-500/20 to-teal-500/10',
    border: 'border-cyan-500/20',
    tag: 'Automation',
  },
];

const STATS = [
  { value: '< 60s', label: 'Average processing time' },
  { value: '94%', label: 'Action item accuracy' },
  { value: '12+', label: 'Export integrations' },
  { value: '∞', label: 'Videos per session' },
];

const HOW_IT_WORKS = [
  {
    step: '01',
    title: 'Paste any video URL',
    desc: 'YouTube, Google Drive, or any direct video link. Supports 400+ video platforms.',
    icon: '🔗',
  },
  {
    step: '02',
    title: 'AI analyzes everything',
    desc: 'Gemini 2.0 + GPT-4o extract events, actions, decisions, topics, and key insights.',
    icon: '🧠',
  },
  {
    step: '03',
    title: 'Get structured intelligence',
    desc: 'Searchable transcripts, event timelines, checklists, and a chat interface to query your video.',
    icon: '⚡',
  },
];

const TESTIMONIALS = [
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
];

const FAQS = [
  {
    q: 'What video sources are supported?',
    a: 'YouTube (any public video), direct video URLs, and Google Drive. Private YouTube videos require authentication. Support for Loom, Vimeo, and Zoom recordings coming soon.',
  },
  {
    q: 'How accurate is the transcript?',
    a: "We first try YouTube's auto-generated captions (which are very accurate). If unavailable, we use OpenAI's Whisper via the STT API. Average accuracy is 94%+ for clear English speech.",
  },
  {
    q: 'What are \"events\"?',
    a: 'Events are structured data points extracted from a video: action items (things to do), decisions made, topics discussed, insights shared, and mentions of tools or people. Each has a timestamp, confidence score, and description.',
  },
  {
    q: 'Is there an API?',
    a: 'Yes. The full EventRelay REST API is available via the FastAPI backend. See /playground for interactive docs. All endpoints are also available as MCP tools for agent integrations.',
  },
  {
    q: 'What happens to my video data?',
    a: 'We never store your video files. We only process the transcript and metadata. All analysis results are session-scoped and deleted after 24 hours unless you export them.',
  },
  {
    q: 'What is the deploy pipeline?',
    a: 'An experimental feature that watches a tutorial video, generates a working codebase from it, creates a GitHub repo, and deploys it to Vercel — fully automated. Requires GITHUB_TOKEN and Vercel credentials.',
  },
];

const EXAMPLES = [
  { label: 'Y Combinator talk', url: 'https://www.youtube.com/watch?v=aircAruvnKk' },
  { label: 'Tech demo', url: 'https://www.youtube.com/watch?v=zjkBMFhNj_g' },
];

// ─── Components ────────────────────────────────────────────────────────────────
function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="border border-white/[0.08] rounded-2xl overflow-hidden transition-all"
      style={{ background: open ? 'rgba(255,255,255,0.03)' : 'transparent' }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-6 py-5 text-left gap-4 hover:bg-white/[0.03] transition-colors"
      >
        <span className="font-semibold text-white/90">{q}</span>
        <span
          className={clsx(
            'w-6 h-6 flex-shrink-0 rounded-full bg-white/[0.05] flex items-center justify-center text-white/50 transition-transform duration-300',
            open && 'rotate-45'
          )}
        >
          +
        </span>
      </button>
      {open && (
        <div className="px-6 pb-5">
          <p className="text-white/55 leading-relaxed text-sm">{a}</p>
        </div>
      )}
    </div>
  );
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center p-6 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
      <div className="text-3xl font-black gradient-text mb-1">{value}</div>
      <div className="text-sm text-white/40">{label}</div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function Home() {
  const [videoUrl, setVideoUrl] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [pasting, setPasting] = useState(false);
  const router = useRouter();
  const typedWord = useTypewriter(USE_CASES);
  const { addToast } = useToast();

  const handleProcess = useCallback(() => {
    const error = validateVideoUrl(videoUrl);
    if (error) {
      setUrlError(error);
      return;
    }
    setUrlError(null);
    router.push(`/dashboard?video=${encodeURIComponent(videoUrl)}`);
  }, [videoUrl, router]);

  const handleUrlChange = useCallback((value: string) => {
    setVideoUrl(value);
    if (urlError) setUrlError(null); // clear error on change
  }, []);

  const handlePasteFromClipboard = useCallback(async () => {
    try {
      setPasting(true);
      const text = await navigator.clipboard.readText();
      if (text.trim()) {
        setVideoUrl(text.trim());
        setUrlError(null);
        addToast('Pasted from clipboard', 'success');
      } else {
        addToast('Clipboard is empty', 'warning');
      }
    } catch {
      addToast('Could not access clipboard — paste manually', 'error');
    } finally {
      setPasting(false);
    }
  }, [addToast]);

  return (
    <div className="min-h-screen text-white overflow-x-hidden">

      {/* ── Nav ─────────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05] bg-surface-950/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-base shadow-lg shadow-primary-500/25">
            E
          </div>
          <span className="font-bold text-lg tracking-tight">EventRelay</span>
          <span className="hidden sm:block px-2 py-0.5 rounded-full bg-primary-500/15 text-primary-400 text-xs font-semibold border border-primary-500/20">
            BETA
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/features" className="hidden md:block text-sm text-white/50 hover:text-white transition px-3 py-2">
            Features
          </Link>
          <Link href="/pricing" className="hidden md:block text-sm text-white/50 hover:text-white transition px-3 py-2">
            Pricing
          </Link>
          <Link
            href="/dashboard"
            className="btn btn-secondary py-2 px-4 text-sm"
          >
            Dashboard
          </Link>
          <Link
            href="/dashboard"
            className="btn btn-primary py-2 px-4 text-sm"
          >
            Get started free →
          </Link>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-20 px-6 text-center max-w-5xl mx-auto">
        {/* Product Hunt badge */}
        <a
          href="https://www.producthunt.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-400 text-xs font-semibold mb-8 hover:bg-orange-500/20 transition-colors animate-fade-in-up"
          style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}
        >
          <span>🚀</span>
          <span>Featured on Product Hunt</span>
          <span className="text-orange-300/60">→</span>
        </a>

        <h1
          className="text-5xl md:text-6xl lg:text-7xl font-black leading-[1.05] mb-6 tracking-tight animate-fade-in-up opacity-0"
          style={{ animationDelay: '100ms', animationFillMode: 'forwards' }}
        >
          Turn your{' '}
          <span className="gradient-text">{typedWord}<span className="animate-pulse">|</span></span>
          <br />
          into intelligence.
        </h1>

        <p
          className="text-lg md:text-xl text-white/50 max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in-up opacity-0"
          style={{ animationDelay: '200ms', animationFillMode: 'forwards' }}
        >
          Paste a video URL. EventRelay extracts transcripts, events, action items,
          and AI insights — in under 60 seconds. No browser extension. No account required.
        </p>

        {/* Hero input */}
        <div
          className="max-w-2xl mx-auto animate-fade-in-up opacity-0"
          style={{ animationDelay: '300ms', animationFillMode: 'forwards' }}
        >
          <form
            onSubmit={(e) => { e.preventDefault(); handleProcess(); }}
            className={clsx(
              'flex gap-2 p-2 rounded-2xl border transition-all duration-300',
              isFocused
                ? 'bg-white/[0.06] border-primary-500/50 shadow-xl shadow-primary-500/10'
                : 'bg-white/[0.04] border-white/[0.08]'
            )}
          >
            <input
              type="url"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Paste a YouTube URL to analyze…"
              className="flex-1 px-4 py-3.5 bg-transparent text-white placeholder:text-white/25 focus:outline-none text-sm"
            />
            {/* Paste from clipboard */}
            <button
              type="button"
              onClick={handlePasteFromClipboard}
              disabled={pasting}
              title="Paste from clipboard"
              className="btn btn-ghost py-3 px-3 text-white/40 hover:text-white/70 disabled:opacity-40"
            >
              {pasting ? (
                <span className="inline-block animate-spin text-xs">⏳</span>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              )}
            </button>
            <button
              type="submit"
              disabled={!videoUrl.trim()}
              className="btn btn-primary py-3.5 px-8 disabled:opacity-30 disabled:cursor-not-allowed text-sm whitespace-nowrap"
            >
              Analyze free →
            </button>
          </form>

          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 mt-4">
            <span className="text-xs text-white/30">Try an example:</span>
            {EXAMPLES.map((ex) => (
              <button
                key={ex.url}
                onClick={() => setVideoUrl(ex.url)}
                className="text-xs text-primary-400/60 hover:text-primary-400 transition underline underline-offset-2"
              >
                {ex.label}
              </button>
            ))}
          </div>

          <p className="text-xs text-white/25 mt-3">
            No credit card. No signup. Free forever for personal use.
          </p>
        </div>

        {/* Trust signals */}
        <div
          className="flex flex-wrap items-center justify-center gap-6 mt-12 animate-fade-in-up opacity-0"
          style={{ animationDelay: '450ms', animationFillMode: 'forwards' }}
        >
          {[
            '✓ Powered by Gemini 2.0 + GPT-4o',
            '✓ Works with YouTube, Drive & more',
            '✓ Export to Notion, Slack, JSON',
          ].map((t) => (
            <span key={t} className="text-xs text-white/35 font-medium">{t}</span>
          ))}
        </div>
      </section>

      {/* ── Stats bar ───────────────────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {STATS.map((s, i) => (
            <div
              key={s.label}
              className="animate-fade-in-up opacity-0"
              style={{ animationDelay: `${500 + i * 80}ms`, animationFillMode: 'forwards' }}
            >
              <StatCard value={s.value} label={s.label} />
            </div>
          ))}
        </div>
      </section>

      {/* ── How It Works ────────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 mb-28">
        <div className="text-center mb-12">
          <div className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-4">
            How it works
          </div>
          <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-3">
            From URL to insight in 3 steps
          </h2>
          <p className="text-white/40 max-w-xl mx-auto">
            No setup. No configuration. Just paste and go.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
          {/* Connector line */}
          <div className="hidden md:block absolute top-10 left-[33%] right-[33%] h-px bg-gradient-to-r from-primary-500/30 via-primary-500/60 to-primary-500/30" />

          {HOW_IT_WORKS.map((step, i) => (
            <div
              key={step.step}
              className="relative p-7 rounded-2xl bg-white/[0.03] border border-white/[0.06] hover:border-primary-500/20 transition-all group animate-fade-in-up opacity-0"
              style={{ animationDelay: `${200 + i * 150}ms`, animationFillMode: 'forwards' }}
            >
              <div className="absolute top-5 right-5 text-4xl font-black text-white/[0.04] group-hover:text-white/[0.07] transition-colors">
                {step.step}
              </div>
              <div className="text-4xl mb-4">{step.icon}</div>
              <h3 className="font-bold text-white mb-2 text-lg">{step.title}</h3>
              <p className="text-sm text-white/45 leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features Grid ───────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 mb-28">
        <div className="text-center mb-12">
          <div className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-4">
            Features
          </div>
          <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-3">
            Everything you need from a video
          </h2>
          <p className="text-white/40 max-w-xl mx-auto">
            More than transcription. EventRelay extracts meaning.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f, i) => (
            <div
              key={f.title}
              className={clsx(
                'relative p-6 rounded-2xl border transition-all duration-300',
                'hover:-translate-y-1 hover:shadow-xl cursor-default',
                `bg-gradient-to-br ${f.color}`,
                f.border,
                'animate-fade-in-up opacity-0'
              )}
              style={{ animationDelay: `${200 + i * 80}ms`, animationFillMode: 'forwards' }}
            >
              <span className="absolute top-4 right-4 text-xs px-2 py-0.5 rounded-full bg-white/[0.06] text-white/40 border border-white/[0.08]">
                {f.tag}
              </span>
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="font-bold text-white mb-2">{f.title}</h3>
              <p className="text-sm text-white/50 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>

        <div className="text-center mt-8">
          <Link href="/features" className="btn btn-secondary py-3 px-6 text-sm">
            See all features →
          </Link>
        </div>
      </section>

      {/* ── Demo strip ──────────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 mb-28">
        <div className="rounded-3xl border border-white/[0.08] bg-gradient-to-br from-primary-500/10 to-cyan-500/5 p-8 md:p-12 text-center">
          <div className="text-5xl mb-4">🎬</div>
          <h2 className="text-2xl md:text-3xl font-black mb-3">
            See it live in 30 seconds
          </h2>
          <p className="text-white/50 mb-8 max-w-lg mx-auto">
            Paste any YouTube URL below and watch EventRelay extract structured intelligence in real time.
          </p>
          <Link
            href="/dashboard"
            className="btn btn-primary py-4 px-10 text-base shadow-2xl shadow-primary-500/30"
          >
            Open the dashboard →
          </Link>
        </div>
      </section>

      {/* ── Testimonials ────────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 mb-28">
        <div className="text-center mb-12">
          <div className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-4">
            Early users
          </div>
          <h2 className="text-3xl md:text-4xl font-black tracking-tight">
            What people are saying
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {TESTIMONIALS.map((t, i) => (
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
              <p className="text-white/70 text-sm leading-relaxed mb-5">"{t.quote}"</p>
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

      {/* ── Pricing CTA ─────────────────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 mb-28">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Free */}
          <div className="p-7 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
            <div className="font-bold text-white/50 text-sm mb-1">Free</div>
            <div className="text-4xl font-black mb-1">$0</div>
            <div className="text-xs text-white/30 mb-6">forever</div>
            <ul className="space-y-2.5 mb-8 text-sm text-white/60">
              {['Unlimited video analysis', 'Transcript extraction', 'Event extraction', 'AI chat (5/day)', 'JSON export'].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> {f}
                </li>
              ))}
            </ul>
            <Link href="/dashboard" className="btn btn-secondary py-3 w-full text-sm text-center block">
              Get started free
            </Link>
          </div>

          {/* Pro */}
          <div className="p-7 rounded-2xl bg-gradient-to-br from-primary-500/15 to-primary-500/5 border border-primary-500/30 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-primary-500 text-white text-xs font-bold">
              Most Popular
            </div>
            <div className="font-bold text-primary-400 text-sm mb-1">Pro</div>
            <div className="text-4xl font-black mb-1">$19</div>
            <div className="text-xs text-white/30 mb-6">per month</div>
            <ul className="space-y-2.5 mb-8 text-sm text-white/70">
              {['Everything in Free', 'Unlimited AI chat', 'Agent dispatch', 'Notion + Slack export', 'API access', 'Priority processing'].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <span className="text-primary-400">✓</span> {f}
                </li>
              ))}
            </ul>
            <Link href="/pricing" className="btn btn-primary py-3 w-full text-sm text-center block">
              Start Pro trial →
            </Link>
          </div>

          {/* Enterprise */}
          <div className="p-7 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
            <div className="font-bold text-white/50 text-sm mb-1">Enterprise</div>
            <div className="text-4xl font-black mb-1">Custom</div>
            <div className="text-xs text-white/30 mb-6">contact us</div>
            <ul className="space-y-2.5 mb-8 text-sm text-white/60">
              {['Everything in Pro', 'Self-hosted option', 'SSO / SAML', 'SLA guarantee', 'Dedicated support', 'Custom integrations'].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <span className="text-cyan-400">✓</span> {f}
                </li>
              ))}
            </ul>
            <Link href="/pricing" className="btn btn-secondary py-3 w-full text-sm text-center block">
              Contact sales →
            </Link>
          </div>
        </div>
      </section>

      {/* ── FAQ ─────────────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 mb-28">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-black tracking-tight">Frequently asked questions</h2>
        </div>
        <div className="space-y-3">
          {FAQS.map((faq) => (
            <FaqItem key={faq.q} q={faq.q} a={faq.a} />
          ))}
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 pb-24 text-center">
        <div className="p-12 rounded-3xl bg-gradient-to-br from-primary-500/15 via-primary-500/5 to-cyan-500/5 border border-primary-500/20">
          <h2 className="text-3xl md:text-4xl font-black mb-4">
            Ready to stop rewatching videos?
          </h2>
          <p className="text-white/50 mb-8 max-w-lg mx-auto">
            Paste any YouTube URL and get structured intelligence in under 60 seconds. Free, forever.
          </p>
          <Link
            href="/dashboard"
            className="btn btn-primary py-4 px-10 text-base shadow-2xl shadow-primary-500/30 inline-block"
          >
            Start analyzing for free →
          </Link>
          <p className="text-xs text-white/25 mt-4">No credit card. No account required.</p>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/[0.06] py-10">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-xs">
                  E
                </div>
                <span className="font-bold text-sm">EventRelay</span>
              </div>
              <p className="text-xs text-white/30 leading-relaxed">
                AI-powered video intelligence for teams and individuals.
              </p>
            </div>
            <div>
              <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">Product</div>
              <ul className="space-y-2.5 text-xs text-white/35">
                {[['Dashboard', '/dashboard'], ['Features', '/features'], ['Pricing', '/pricing'], ['API Docs', '/playground']].map(([label, href]) => (
                  <li key={label}>
                    <Link href={href} className="hover:text-white/60 transition">{label}</Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">Use Cases</div>
              <ul className="space-y-2.5 text-xs text-white/35">
                {['Meeting Notes', 'Conference Talks', 'Tutorials', 'Product Demos', 'Podcasts'].map((u) => (
                  <li key={u}><span className="cursor-default">{u}</span></li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">Links</div>
              <ul className="space-y-2.5 text-xs text-white/35">
                <li>
                  <a href="https://github.com/groupthinking/EventRelay" target="_blank" rel="noopener noreferrer" className="hover:text-white/60 transition">
                    GitHub
                  </a>
                </li>
                <li>
                  <a href="https://www.producthunt.com" target="_blank" rel="noopener noreferrer" className="hover:text-white/60 transition">
                    Product Hunt
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-white/[0.05] pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-white/25">
            <span>© 2026 EventRelay. MIT License.</span>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <span>All systems operational</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
