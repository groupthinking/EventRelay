'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

const TRUST_PILLS = [
  'Open source',
  'MIT licensed',
  'Self-hostable',
  'OpenAPI included',
  'Gemini + OpenAI',
  'FastAPI backend',
  'Next.js dashboard',
  'Docker ready',
];

// Animated pipeline rows that cycle through processing states
const PIPELINE_ITEMS = [
  { id: 'transcript', label: 'Transcript', value: 'Fetching captions…', done: 'timestamped text', color: '#6af2de' },
  { id: 'events', label: 'Typed events', value: 'Extracting decisions…', done: 'typed JSON', color: '#6af2de' },
  { id: 'actions', label: 'Action items', value: 'Identifying tasks…', done: 'owner-ready tasks', color: '#6af2de' },
  { id: 'analysis', label: 'AI analysis', value: 'Gemini pass running…', done: 'strategic insights', color: '#6af2de' },
  { id: 'chat', label: 'Video chat', value: 'Indexing context…', done: 'ask the video', color: '#6af2de' },
];

export default function HeroSection() {
  const [activeStep, setActiveStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setActiveStep((prev) => {
        const next = prev + 1;
        if (next >= PIPELINE_ITEMS.length) {
          // Reset animation
          setTimeout(() => {
            setCompletedSteps(new Set());
            setActiveStep(0);
          }, 1200);
          return prev;
        }
        setCompletedSteps((c) => new Set([...c, prev]));
        return next;
      });
    }, 900);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  return (
    <section
      className="relative min-h-screen flex flex-col pt-20"
      style={{
        background:
          'radial-gradient(ellipse 80% 60% at 50% -10%, rgba(106,242,222,0.12) 0%, transparent 70%)',
      }}
    >
      {/* Subtle grid overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(rgba(106,242,222,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(106,242,222,0.03) 1px, transparent 1px)',
          backgroundSize: '80px 80px',
        }}
        aria-hidden
      />

      <div className="relative flex-1 flex flex-col justify-center px-8 py-20 max-w-[1440px] mx-auto w-full">
        {/* Eyebrow */}
        <div className="flex justify-center mb-8">
          <span
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-[0.2em]"
            style={{
              background: 'rgba(106,242,222,0.08)',
              border: '1px solid rgba(106,242,222,0.2)',
              color: '#6af2de',
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ background: '#6af2de' }}
              aria-hidden
            />
            The action layer for video
          </span>
        </div>

        {/* Hero headline — display scale */}
        <h1 className="font-heading text-center text-[clamp(3rem,8vw,8rem)] font-black leading-[0.9] tracking-tighter mb-8 text-ink">
          Paste a video.{' '}
          <span
            style={{
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundImage: 'linear-gradient(135deg, #6af2de 0%, #38fbf7 50%, #14b8a6 100%)',
            }}
          >
            Build from it.
          </span>
        </h1>

        {/* Sub-headline */}
        <p className="text-center text-[clamp(1rem,2vw,1.25rem)] leading-relaxed max-w-2xl mx-auto mb-12 text-ink/55">
          Paste a YouTube URL. UVAI takes what is inside the video — transcript, typed events, action items,
          and AI-driven execution — and builds from it. YouTube tells you what&apos;s there. UVAI acts on it.
        </p>

        {/* CTAs */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-16">
          <Link
            href="/"
            className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl font-bold text-base transition-all duration-200 active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de]"
            style={{ background: '#6af2de', color: '#021a18' }}
          >
            Try a YouTube URL
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              className="transition-transform duration-200 group-hover:translate-x-0.5"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </Link>
          <a
            href="#features"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl font-bold text-base transition-all duration-200 text-ink/70 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de]"
            style={{ border: '1px solid rgba(255,255,255,0.1)' }}
          >
            See how it works
          </a>
        </div>

        {/* Trust pills marquee */}
        <div className="relative overflow-hidden mb-20" aria-label="Product attributes">
          <div className="flex gap-3 animate-marquee whitespace-nowrap">
            {[...TRUST_PILLS, ...TRUST_PILLS].map((p, i) => (
              <span
                key={i}
                className="inline-flex shrink-0 items-center px-4 py-2 rounded-full text-xs font-semibold uppercase tracking-widest"
                style={{
                  background: 'rgba(106,242,222,0.06)',
                  border: '1px solid rgba(106,242,222,0.15)',
                  color: 'rgba(106,242,222,0.8)',
                }}
              >
                {p}
              </span>
            ))}
          </div>
        </div>

        {/* Product mockup — hero pipeline card */}
        <div className="max-w-3xl mx-auto w-full">
          <div
            className="rounded-2xl overflow-hidden"
            style={{
              background: 'rgba(10,12,16,0.9)',
              border: '1px solid rgba(106,242,222,0.12)',
              boxShadow: '0 0 80px -20px rgba(106,242,222,0.25), 0 40px 80px -20px rgba(0,0,0,0.6)',
            }}
          >
            {/* Window chrome */}
            <div
              className="flex items-center justify-between px-5 py-3.5"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
            >
              <div className="flex gap-1.5" aria-hidden>
                <span className="w-3 h-3 rounded-full" style={{ background: '#ff5f57' }} />
                <span className="w-3 h-3 rounded-full" style={{ background: '#ffbd2e' }} />
                <span className="w-3 h-3 rounded-full" style={{ background: '#28ca41' }} />
              </div>
              <div
                className="flex items-center gap-2 text-xs px-3 py-1 rounded-full"
                style={{
                  background: 'rgba(106,242,222,0.08)',
                  border: '1px solid rgba(106,242,222,0.15)',
                  color: '#6af2de',
                }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ background: '#6af2de' }}
                  aria-hidden
                />
                Pipeline running
              </div>
              <span className="text-xs font-mono text-ink/25">uvai.run/job_a4f2</span>
            </div>

            {/* URL input bar */}
            <div className="px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <div
                className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-mono"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  style={{ color: '#ff0000', flexShrink: 0 }}
                  aria-hidden
                >
                  <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.37 6.37 0 0 0-.79-.05A6.34 6.34 0 0 0 3.15 15.3 6.34 6.34 0 0 0 9.49 21.5a6.34 6.34 0 0 0 6.35-6.35V8.64a8.24 8.24 0 0 0 4.81 1.54V6.74a4.84 4.84 0 0 1-1.06-.05z" />
                </svg>
                <span className="text-ink/40">youtube.com/watch?v=</span>
                <span className="text-ink/70">auJzb1D-fag</span>
                <span
                  className="ml-auto text-[10px] px-2 py-0.5 rounded-full uppercase tracking-widest font-bold"
                  style={{ background: 'rgba(106,242,222,0.1)', color: '#6af2de' }}
                >
                  Analyzing
                </span>
              </div>
            </div>

            {/* Pipeline steps */}
            <div className="p-5 grid gap-2">
              {PIPELINE_ITEMS.map((item, idx) => {
                const isDone = completedSteps.has(idx);
                const isActive = activeStep === idx;
                return (
                  <div
                    key={item.id}
                    className="flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-500"
                    style={{
                      background: isActive
                        ? 'rgba(106,242,222,0.06)'
                        : isDone
                        ? 'rgba(106,242,222,0.03)'
                        : 'rgba(255,255,255,0.02)',
                      border: isActive
                        ? '1px solid rgba(106,242,222,0.2)'
                        : isDone
                        ? '1px solid rgba(106,242,222,0.08)'
                        : '1px solid rgba(255,255,255,0.04)',
                    }}
                  >
                    {/* Status icon */}
                    <div
                      className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300"
                      style={{
                        background: isDone
                          ? 'rgba(106,242,222,0.15)'
                          : isActive
                          ? 'rgba(106,242,222,0.08)'
                          : 'rgba(255,255,255,0.04)',
                        border: isDone
                          ? '1px solid rgba(106,242,222,0.4)'
                          : isActive
                          ? '1px solid rgba(106,242,222,0.25)'
                          : '1px solid rgba(255,255,255,0.08)',
                      }}
                    >
                      {isDone ? (
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="#6af2de"
                          strokeWidth="3"
                          strokeLinecap="round"
                        >
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      ) : isActive ? (
                        <span
                          className="w-2 h-2 rounded-full animate-pulse"
                          style={{ background: '#6af2de' }}
                          aria-hidden
                        />
                      ) : (
                        <span className="w-2 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.15)' }} aria-hidden />
                      )}
                    </div>

                    {/* Label */}
                    <span
                      className="font-heading text-sm font-bold flex-1"
                      style={{ color: isDone || isActive ? '#f8f5fd' : 'rgba(248,245,253,0.35)' }}
                    >
                      {item.label}
                    </span>

                    {/* Value */}
                    <span
                      className="text-xs font-mono transition-all duration-500"
                      style={{ color: isDone ? '#6af2de' : 'rgba(248,245,253,0.25)' }}
                    >
                      {isDone ? item.done : isActive ? item.value : '—'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

    </section>
  );
}
