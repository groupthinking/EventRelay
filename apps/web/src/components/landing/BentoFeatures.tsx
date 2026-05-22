import Link from 'next/link';

// Bento grid feature cards — producer.ai style
// Large headline + product demo panels + smaller supporting tiles

const TRANSCRIPT_LINES = [
  { ts: '0:00', text: 'Welcome back, everyone. Today we are diving into' },
  { ts: '0:04', text: 'the architecture decisions behind our new API design,' },
  { ts: '0:08', text: 'starting with the schema layer and event sourcing.' },
  { ts: '0:13', text: 'First, let me show you how the typed event extraction' },
  { ts: '0:17', text: 'handles ambiguous decisions in long-form content…' },
];

const EVENT_ROWS = [
  { type: 'decision', ts: '0:08', text: 'Adopt event sourcing for schema layer' },
  { type: 'task', ts: '0:17', text: 'Review typed event extraction spec' },
  { type: 'topic', ts: '0:22', text: 'API design — schema layer' },
  { type: 'insight', ts: '0:31', text: 'Event sourcing removes dual-write risk' },
];

const TYPE_COLORS: Record<string, string> = {
  decision: '#6af2de',
  task: '#fbbf24',
  topic: '#a78bfa',
  insight: '#f472b6',
};

const STAT_TILES = [
  { value: '~3s', label: 'Avg transcript time' },
  { value: '9', label: 'Workflow templates' },
  { value: '5+', label: 'Agent analysis passes' },
  { value: '100%', label: 'Open source' },
];

export default function BentoFeatures() {
  return (
    <section id="features" className="scroll-mt-24 px-8 py-24 max-w-[1440px] mx-auto w-full">
      {/* Section eyebrow */}
      <div className="mb-12">
        <p
          className="text-xs tracking-[0.3em] uppercase font-bold mb-4"
          style={{ color: '#6af2de' }}
        >
          What UVAI does
        </p>
        <h2 className="font-heading text-[clamp(2.5rem,5vw,5rem)] font-black tracking-tighter leading-[0.95] text-ink">
          Everything you need to
          <br />
          <span
            style={{
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundImage: 'linear-gradient(135deg, #6af2de, #38fbf7)',
            }}
          >
            extract value from video.
          </span>
        </h2>
      </div>

      {/* Bento grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-[minmax(200px,auto)]">

        {/* LARGE — Transcript pipeline */}
        <article
          className="lg:col-span-2 rounded-2xl overflow-hidden group"
          style={{
            background: 'rgba(10,12,16,0.85)',
            border: '1px solid rgba(106,242,222,0.1)',
          }}
        >
          <div className="p-7">
            <p className="text-xs uppercase tracking-widest font-bold mb-2" style={{ color: '#6af2de' }}>
              01 — Transcript pipeline
            </p>
            <h3 className="font-heading text-2xl font-black tracking-tight text-ink mb-2">
              Verbatim + timestamped.
            </h3>
            <p className="text-sm text-ink/50 mb-6 max-w-sm">
              YouTube captions first, speech-to-text fallback when captions are missing. Every word, every timestamp.
            </p>
          </div>

          {/* Simulated transcript view */}
          <div
            className="mx-5 mb-5 rounded-xl overflow-hidden"
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <div
              className="flex items-center gap-2 px-4 py-2.5 text-xs"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'rgba(248,245,253,0.3)' }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              transcript.txt
              <span className="ml-auto px-2 py-0.5 rounded text-[10px] font-bold" style={{ background: 'rgba(106,242,222,0.1)', color: '#6af2de' }}>
                READY
              </span>
            </div>
            <div className="px-4 py-4 font-mono text-xs leading-6 max-h-[160px] overflow-hidden" style={{ color: 'rgba(248,245,253,0.55)' }}>
              {TRANSCRIPT_LINES.map((line) => (
                <div key={line.ts} className="flex gap-3">
                  <span className="text-[10px] pt-0.5 flex-shrink-0 font-bold" style={{ color: '#6af2de' }}>{line.ts}</span>
                  <span>{line.text}</span>
                </div>
              ))}
            </div>
          </div>
        </article>

        {/* TALL — Stats column */}
        <div className="grid grid-rows-2 gap-4">
          {STAT_TILES.map((s) => (
            <article
              key={s.label}
              className="rounded-2xl p-6 flex flex-col justify-between"
              style={{
                background: 'rgba(10,12,16,0.85)',
                border: '1px solid rgba(106,242,222,0.08)',
              }}
            >
              <p className="text-5xl font-black font-heading tracking-tight" style={{ color: '#6af2de' }}>
                {s.value}
              </p>
              <p className="text-sm text-ink/45 font-medium mt-2">{s.label}</p>
            </article>
          ))}
        </div>

        {/* MEDIUM — Structured events */}
        <article
          className="rounded-2xl overflow-hidden"
          style={{
            background: 'rgba(10,12,16,0.85)',
            border: '1px solid rgba(106,242,222,0.1)',
          }}
        >
          <div className="p-7 pb-4">
            <p className="text-xs uppercase tracking-widest font-bold mb-2" style={{ color: '#6af2de' }}>
              02 — Typed events
            </p>
            <h3 className="font-heading text-xl font-black tracking-tight text-ink mb-1">
              Structured output.
            </h3>
            <p className="text-sm text-ink/50">
              Decisions, tasks, topics, insights — returned as schema-bound JSON.
            </p>
          </div>
          <div className="px-5 pb-5 grid gap-2">
            {EVENT_ROWS.map((e) => (
              <div
                key={e.ts + e.type}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg"
                style={{
                  background: 'rgba(255,255,255,0.025)',
                  border: '1px solid rgba(255,255,255,0.05)',
                }}
              >
                <span
                  className="text-[9px] uppercase tracking-widest font-bold px-2 py-0.5 rounded"
                  style={{
                    background: `${TYPE_COLORS[e.type]}18`,
                    color: TYPE_COLORS[e.type],
                    border: `1px solid ${TYPE_COLORS[e.type]}30`,
                    minWidth: 56,
                    textAlign: 'center',
                  }}
                >
                  {e.type}
                </span>
                <span className="text-xs text-ink/60 flex-1">{e.text}</span>
                <span className="text-[10px] font-mono text-ink/25">{e.ts}</span>
              </div>
            ))}
          </div>
        </article>

        {/* MEDIUM — Agent analysis */}
        <article
          className="rounded-2xl overflow-hidden"
          style={{
            background: 'rgba(10,12,16,0.85)',
            border: '1px solid rgba(106,242,222,0.1)',
          }}
        >
          <div className="p-7 pb-4">
            <p className="text-xs uppercase tracking-widest font-bold mb-2" style={{ color: '#6af2de' }}>
              03 — Agent analysis
            </p>
            <h3 className="font-heading text-xl font-black tracking-tight text-ink mb-1">
              Multi-agent depth.
            </h3>
            <p className="text-sm text-ink/50">
              Gemini passes for summary, intent, strategy, and video-aware chat.
            </p>
          </div>

          {/* Chat preview */}
          <div className="px-5 pb-5 grid gap-2.5">
            <div
              className="px-4 py-3 rounded-xl text-xs text-ink/70 leading-relaxed"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
            >
              <span className="block text-[10px] uppercase tracking-widest font-bold mb-1.5" style={{ color: '#6af2de' }}>
                Summary
              </span>
              This video covers event sourcing architecture decisions, with a focus on typed schema design and eliminating dual-write consistency risks.
            </div>
            <div
              className="flex items-start gap-2.5 px-4 py-3 rounded-xl text-xs"
              style={{ background: 'rgba(106,242,222,0.04)', border: '1px solid rgba(106,242,222,0.12)' }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#6af2de" strokeWidth="2" className="mt-0.5 shrink-0">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span className="text-ink/60">
                &ldquo;What action items came from the schema discussion?&rdquo;
              </span>
            </div>
          </div>
        </article>

        {/* WIDE — CTA banner */}
        <article
          className="lg:col-span-3 rounded-2xl p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6"
          style={{
            background: 'rgba(106,242,222,0.04)',
            border: '1px solid rgba(106,242,222,0.15)',
          }}
        >
          <div>
            <h3 className="font-heading text-2xl font-black tracking-tight text-ink mb-1">
              Ready to process your first video?
            </h3>
            <p className="text-sm text-ink/50">
              Paste any YouTube URL into the dashboard. Results in seconds.
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Link
              href="/dashboard"
              className="px-7 py-3.5 rounded-xl font-bold text-sm transition-all duration-200 active:scale-95 whitespace-nowrap"
              style={{ background: '#6af2de', color: '#021a18' }}
            >
              Open dashboard
            </Link>
            <a
              href="https://github.com/groupthinking/EventRelay"
              target="_blank"
              rel="noopener noreferrer"
              className="px-7 py-3.5 rounded-xl font-bold text-sm transition-all duration-200 whitespace-nowrap text-ink/70 hover:text-ink"
              style={{ border: '1px solid rgba(255,255,255,0.1)' }}
            >
              View source
            </a>
          </div>
        </article>
      </div>
    </section>
  );
}
