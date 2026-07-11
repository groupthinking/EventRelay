const DEVELOPER_ITEMS = [
  {
    head: 'FastAPI backend',
    body: 'Use the API directly, inspect the OpenAPI contract, or extend the processing routes with your own logic.',
    badge: 'Python',
  },
  {
    head: 'Next.js 15 dashboard',
    body: 'A working hosted interface for URL input, templates, status, results, and video chat. Fork or deploy as-is.',
    badge: 'TypeScript',
  },
  {
    head: 'Self-hostable deployment',
    body: 'Docker, Cloud Run, Railway, and Vercel configs ship with the repo. Run it on your own infrastructure.',
    badge: 'Docker',
  },
  {
    head: 'MIT licensed',
    body: 'EventRelay is the open-source repo name; UVAI is the live product brand. Use, fork, or contribute freely.',
    badge: 'Open source',
  },
];

const CODE_SNIPPET = `# Quick start
pip install eventelay

from eventelay import UVAIClient

client = UVAIClient(
  gemini_key="your-key",
  openai_key="your-key"
)

result = await client.process(
  url="https://youtube.com/watch?v=..."
)

print(result.transcript)
print(result.events)   # typed JSON
print(result.actions)  # task list`;

export default function DeveloperSection() {
  return (
    <section
      id="developers"
      className="scroll-mt-24 py-24 px-8"
      style={{ background: 'rgba(5,6,9,0.98)' }}
    >
      <div className="max-w-[1440px] mx-auto">
        {/* Heading */}
        <div className="mb-14">
          <p className="text-xs tracking-[0.3em] uppercase font-bold mb-4" style={{ color: '#6af2de' }}>
            Built for operators and developers
          </p>
          <h2 className="font-heading text-[clamp(2.5rem,5vw,5rem)] font-black tracking-tighter leading-[0.95] text-ink">
            Open where it matters.
          </h2>
        </div>

        {/* Two-column layout: features + code */}
        <div className="grid lg:grid-cols-2 gap-8 items-start">
          {/* Feature list */}
          <ul className="grid gap-4">
            {DEVELOPER_ITEMS.map((d) => (
              <li
                key={d.head}
                className="flex items-start gap-4 p-6 rounded-2xl transition-all duration-200"
                style={{
                  background: 'rgba(10,12,16,0.85)',
                  border: '1px solid rgba(255,255,255,0.07)',
                }}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-heading text-base font-black tracking-tight text-ink">
                      {d.head}
                    </h3>
                    <span
                      className="text-[9px] uppercase tracking-widest font-bold px-2 py-0.5 rounded"
                      style={{
                        background: 'rgba(106,242,222,0.08)',
                        color: '#6af2de',
                        border: '1px solid rgba(106,242,222,0.2)',
                      }}
                    >
                      {d.badge}
                    </span>
                  </div>
                  <p className="text-sm text-ink/50 leading-relaxed">{d.body}</p>
                </div>
                <div
                  className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: 'rgba(106,242,222,0.06)', border: '1px solid rgba(106,242,222,0.12)' }}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#6af2de"
                    strokeWidth="2"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
              </li>
            ))}
          </ul>

          {/* Code preview */}
          <div
            className="rounded-2xl overflow-hidden sticky top-28"
            style={{
              background: 'rgba(10,12,16,0.9)',
              border: '1px solid rgba(106,242,222,0.12)',
              boxShadow: '0 0 60px -20px rgba(106,242,222,0.15)',
            }}
          >
            <div
              className="flex items-center justify-between px-5 py-3"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
            >
              <div className="flex gap-1.5" aria-hidden>
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }} />
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }} />
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }} />
              </div>
              <span className="text-xs font-mono text-ink/30">quick_start.py</span>
            </div>
            <pre
              className="p-6 text-xs font-mono leading-6 overflow-x-auto"
              style={{ color: 'rgba(248,245,253,0.65)' }}
            >
              <code>
                {CODE_SNIPPET.split('\n').map((line, i) => {
                  // Very light syntax coloring
                  const isComment = line.trim().startsWith('#');
                  const isKey = /^(from|import|await|print)/.test(line.trim());
                  return (
                    <span
                      key={i}
                      className="block"
                      style={{
                        color: isComment
                          ? 'rgba(106,242,222,0.5)'
                          : isKey
                          ? 'rgba(248,245,253,0.45)'
                          : undefined,
                      }}
                    >
                      {line || '\u00a0'}
                    </span>
                  );
                })}
              </code>
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}
