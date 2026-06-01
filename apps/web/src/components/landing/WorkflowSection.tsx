const STEPS = [
  {
    n: '01',
    title: 'Paste a YouTube URL',
    body: 'Use the hosted dashboard or self-host with your own Gemini and OpenAI keys. No setup required to try it.',
    hint: 'youtube.com/watch?v=...',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    n: '02',
    title: 'Watch the pipeline run',
    body: 'Transcription, structured extraction, and AI analysis run as a coordinated job with real-time SSE status updates.',
    hint: 'SSE status → live progress',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
      </svg>
    ),
  },
  {
    n: '03',
    title: 'Use the result',
    body: 'Read the transcript, export structured events, review action items, or open video chat and ask any follow-up questions.',
    hint: 'Export JSON / chat / share',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 5v14M5 12l7 7 7-7" />
      </svg>
    ),
  },
];

export default function WorkflowSection() {
  return (
    <section
      id="workflow"
      className="scroll-mt-24 py-24 px-8"
      style={{ background: 'rgba(8,10,14,0.95)' }}
    >
      <div className="max-w-[1440px] mx-auto">
        {/* Eyebrow + heading */}
        <div className="mb-16 max-w-2xl">
          <p className="text-xs tracking-[0.3em] uppercase font-bold mb-4" style={{ color: '#6af2de' }}>
            How it works
          </p>
          <h2 className="font-heading text-[clamp(2.5rem,5vw,5rem)] font-black tracking-tighter leading-[0.95] text-ink">
            From URL to usable output.
          </h2>
          <p className="mt-5 text-base text-ink/50 leading-relaxed">
            Three steps. No configuration needed for the first run.
          </p>
        </div>

        {/* Step cards */}
        <div className="grid md:grid-cols-3 gap-5">
          {STEPS.map((s, idx) => (
            <article
              key={s.n}
              className="relative rounded-2xl p-8 overflow-hidden group"
              style={{
                background: 'rgba(10,12,16,0.85)',
                border: '1px solid rgba(106,242,222,0.08)',
              }}
            >
              {/* Ghost number */}
              <span
                className="absolute right-6 top-4 font-heading text-8xl font-black leading-none select-none pointer-events-none transition-all duration-500 group-hover:opacity-100"
                style={{ color: 'rgba(106,242,222,0.05)' }}
                aria-hidden
              >
                {s.n}
              </span>

              {/* Icon */}
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center mb-6 transition-all duration-300"
                style={{
                  background: 'rgba(106,242,222,0.08)',
                  border: '1px solid rgba(106,242,222,0.15)',
                  color: '#6af2de',
                }}
              >
                {s.icon}
              </div>

              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: '#6af2de' }}>
                Step {s.n}
              </p>
              <h3 className="font-heading text-xl font-black tracking-tight text-ink mb-3">
                {s.title}
              </h3>
              <p className="text-sm text-ink/50 leading-relaxed mb-5">{s.body}</p>

              {/* Inline hint tag */}
              <span
                className="inline-flex items-center gap-1.5 text-[11px] font-mono px-3 py-1.5 rounded-lg"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.07)',
                  color: 'rgba(248,245,253,0.35)',
                }}
              >
                {s.hint}
              </span>

              {/* Step connector line (not on last) */}
              {idx < STEPS.length - 1 && (
                <div
                  className="hidden md:block absolute top-1/2 -right-2.5 w-5 h-px"
                  style={{ background: 'rgba(106,242,222,0.25)' }}
                  aria-hidden
                />
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
