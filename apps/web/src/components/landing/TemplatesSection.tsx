import Link from 'next/link';

const TEMPLATES = [
  {
    title: 'Tutorial → project plan',
    body: 'Extract the implementation path from a technical tutorial and scaffold a deployable project with code-oriented outputs.',
    tags: ['Engineering', 'Scaffold'],
    featured: true,
  },
  {
    title: 'Conference talk → action items',
    body: 'Capture decisions, follow-ups, and concrete next steps from long-form business or technical talks.',
    tags: ['Business', 'Tasks'],
    featured: false,
  },
  {
    title: 'Podcast → blog post',
    body: 'Turn a long discussion into a structured draft with themes, quotes, and a clear content outline.',
    tags: ['Content', 'Drafting'],
    featured: false,
  },
  {
    title: 'Lecture → study notes',
    body: 'Compress educational videos into notes, key ideas, and review material without losing source context.',
    tags: ['Education', 'Notes'],
    featured: false,
  },
];

export default function TemplatesSection() {
  return (
    <section id="templates" className="scroll-mt-24 py-24 px-8 max-w-[1440px] mx-auto w-full">
      {/* Heading */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-14">
        <div>
          <p className="text-xs tracking-[0.3em] uppercase font-bold mb-4" style={{ color: '#6af2de' }}>
            Workflow starting points
          </p>
          <h2 className="font-heading text-[clamp(2.5rem,4vw,4rem)] font-black tracking-tighter leading-[0.95] text-ink">
            Templates that match
            <br />
            real use cases.
          </h2>
        </div>
        <p className="text-base text-ink/50 max-w-sm leading-relaxed md:text-right">
          UVAI ships nine workflow templates. Browse the rest in the dashboard.
        </p>
      </div>

      {/* Template grid */}
      <div className="grid md:grid-cols-2 gap-4 mb-8">
        {TEMPLATES.map((t) => (
          <article
            key={t.title}
            className="rounded-2xl p-8 transition-all duration-300 hover:-translate-y-0.5 cursor-default group"
            style={{
              background: t.featured ? 'rgba(106,242,222,0.04)' : 'rgba(10,12,16,0.85)',
              border: t.featured
                ? '1px solid rgba(106,242,222,0.2)'
                : '1px solid rgba(255,255,255,0.07)',
            }}
          >
            {t.featured && (
              <span
                className="inline-flex mb-4 text-[10px] uppercase tracking-widest font-bold px-2.5 py-1 rounded-full"
                style={{
                  background: 'rgba(106,242,222,0.12)',
                  color: '#6af2de',
                  border: '1px solid rgba(106,242,222,0.25)',
                }}
              >
                Popular
              </span>
            )}
            <h3 className="font-heading text-xl font-black tracking-tight text-ink mb-3">
              {t.title}
            </h3>
            <p className="text-sm text-ink/50 leading-relaxed mb-6">{t.body}</p>
            <div className="flex flex-wrap gap-2">
              {t.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] uppercase tracking-widest font-bold px-2.5 py-1 rounded-full"
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    color: 'rgba(248,245,253,0.45)',
                    border: '1px solid rgba(255,255,255,0.07)',
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>

      <div className="flex justify-center">
        <Link
          href="/dashboard"
          className="group inline-flex items-center gap-2 text-sm font-bold"
          style={{ color: '#6af2de' }}
        >
          See all 9 templates in the dashboard
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            className="transition-transform duration-200 group-hover:translate-x-0.5"
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
    </section>
  );
}
