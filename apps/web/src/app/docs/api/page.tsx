import type { Metadata } from 'next';
import Link from 'next/link';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import DownloadMarkdownButton from '@/components/docs/DownloadMarkdownButton';

export const metadata: Metadata = {
  title: 'API Reference',
  description:
    'HTTP reference for the UVAI public API: Video Packs, transcription, and the Studio analysis workflow.',
  alternates: { canonical: '/docs/api' },
  robots: { index: true, follow: true },
};

type Endpoint = {
  method: 'GET' | 'POST';
  path: string;
  summary: string;
  body?: string;
};

const ENDPOINTS: Endpoint[] = [
  { method: 'GET', path: '/api', summary: 'Service descriptor (name, version, status).' },
  { method: 'POST', path: '/api/transcribe', summary: 'Fetch a transcript for a YouTube URL.', body: '{ "url": "https://youtu.be/..." }' },
  { method: 'POST', path: '/api/chat', summary: 'Conversational query over an analyzed video.' },
  { method: 'POST', path: '/api/video/pack', summary: 'Emit a hashed Video Pack from a YouTube URL.', body: '{ "url": "https://www.youtube.com/watch?v=..." }' },
  { method: 'GET', path: '/api/video/pack', summary: 'Poll a pack by video_id or source_hash until ready (202 processing → 200 success).', body: '?video_id=auJzb1D-fag' },
  { method: 'GET', path: '/api/video/sandbox', summary: 'Materialize an App Builder Workspace sandbox from a stored Video Pack (startup.sh, 8080, browser-smoke, build/typecheck).' },
  { method: 'POST', path: '/api/video/sandbox', summary: 'Same sandbox emit by paste-URL identity. Requires a ready pack from POST /api/video/pack.', body: '{ "url": "https://www.youtube.com/watch?v=..." }' },
  { method: 'GET', path: '/api/video/assemble', summary: 'Same stored-pack lookup as sandbox plus a planned assembly receipt (file hashes, pinned deps, unresolved requirements). Gates are labeled untested — HTTP does not run npm.' },
  { method: 'POST', path: '/api/video/assemble', summary: 'Planned assembly receipt by paste-URL identity. Requires a ready pack. Does not install, build, or typecheck on the server.', body: '{ "url": "https://www.youtube.com/watch?v=..." }' },
  { method: 'POST', path: '/api/workflows/video-to-actions', summary: 'Start the Studio analysis workflow.', body: '{ "url": "https://www.youtube.com/watch?v=..." }' },
];

const METHOD_COLOR: Record<Endpoint['method'], string> = {
  GET: 'border-[var(--uvai-success-border,var(--uvai-border-strong))] bg-[var(--uvai-success-bg,transparent)] text-[var(--uvai-success-ink,var(--uvai-ink))]',
  POST: 'border-[var(--uvai-accent)] bg-[var(--uvai-accent-soft)] text-[var(--uvai-accent-ink,var(--uvai-accent))]',
};

const LINK_CLASS =
  'text-[var(--uvai-accent-ink,var(--uvai-accent))] underline-offset-4 hover:underline';
const CODE_CLASS = 'text-[var(--uvai-accent-ink,var(--uvai-accent))]';

const LAUNCH_CHECKLIST = [
  {
    phase: '1. Workspace & source intake',
    items: [
      'Normalize YouTube URL identity (`video_id` + `source_hash`) before queuing extraction.',
      'Persist `language`, theme mode (`data-theme`), and WCAG AAA contrast (`data-contrast`).',
    ],
  },
  {
    phase: '2. Design system & breakpoints',
    items: [
      'Keep Webflow/MDN persistent left sidebar active down to 600px half-screen widths.',
      'Enforce zero horizontal overflow (`scrollWidth <= innerWidth`) across 720x900 and 1440x900.',
    ],
  },
  {
    phase: '3. Video Pack & G.A.T.E. spec',
    items: [
      'Render numbered syllabus chapters, clickable transcript timestamps, and detected stack tools.',
      'Keep Deliverables consolidated into 4 plain-English tabs: Preview, Tasks & Tools, Code & Spec, Transcript.',
    ],
  },
  {
    phase: '4. WebMCP & tool harnesses',
    items: [
      'Expose declarative `<form toolname>` and `document.modelContext` tools within Chrome limits.',
      'Export downloadable Markdown specs (`.md`) ready for Claude, Cursor, or ChatGPT.',
    ],
  },
  {
    phase: '5. Pre-launch Security, LCP & Accessibility QA',
    items: [
      'Prioritize video poster image loading (`fetchPriority="high"`) and automatic embed fallback.',
      'Audit heading hierarchy, form field labels/ids, keyboard focus rings, and CodeQL sanitization.',
    ],
  },
] as const;

const DOCS_MARKDOWN = `# UVAI Operational Reference & Build Checklist

Base URL: https://uvai.io
Workflow: YouTube URL -> POST /api/video/pack -> POST /api/workflows/video-to-actions -> /d/[videoId]

## Endpoints
${ENDPOINTS.map((e) => `- \`${e.method} ${e.path}\` — ${e.summary}`).join('\n')}

## Build & Launch Checklist
${LAUNCH_CHECKLIST.map((s) => `### ${s.phase}\n${s.items.map((i) => `- [ ] ${i}`).join('\n')}`).join('\n\n')}
`;

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen bg-[var(--uvai-bg)] text-[var(--uvai-ink)]">
      <Nav variant="rail" defaultCollapsed={false} />
      <main className="w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] px-4 py-3">
          <nav aria-label="Breadcrumb" className="text-xs text-[var(--uvai-ink-faint)]">
            <ol className="flex items-center gap-2">
              <li>
                <Link className="hover:text-[var(--uvai-ink)] hover:underline" href="/">
                  Home
                </Link>
              </li>
              <li aria-hidden="true">/</li>
              <li>Docs</li>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="font-medium text-[var(--uvai-ink)]">
                API Reference
              </li>
            </ol>
          </nav>
          <div className="flex flex-wrap items-center gap-2">
            <span className="hidden font-mono text-[11px] text-[var(--uvai-ink-faint)] sm:inline">
              Ready for Claude, Cursor, or ChatGPT
            </span>
            <DownloadMarkdownButton
              filename="uvai-build-and-launch-checklist.md"
              content={DOCS_MARKDOWN}
              label="Download .md"
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--uvai-border-strong)] bg-[var(--uvai-bg)] px-3 py-1.5 font-mono text-xs font-semibold text-[var(--uvai-ink)] transition hover:border-[var(--uvai-accent)]"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_272px] lg:items-start">
          <div>
            <header id="overview" className="mb-8 border-b border-[var(--uvai-border-strong)] pb-6">
              <p className="uvai-label">UVAI Operational Documentation</p>
              <h1 className="mt-2 text-3xl font-medium tracking-tight sm:text-4xl">API Reference</h1>
              <p className="mt-3 max-w-2xl text-[var(--uvai-ink-soft)]">
                UVAI exposes a small, REST-style surface for Video Packs, transcription,
                and Studio chat. All endpoints accept and return JSON unless noted.
              </p>
              <p className="mt-3 max-w-2xl text-sm text-[var(--uvai-ink-faint)]">
                The legacy <code>/api/pipeline</code> routes are retired. Start a pack with{' '}
                <code>POST /api/video/pack</code>.
              </p>
            </header>

            <section id="base-url" className="mb-8 rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] p-5 sm:p-6">
              <h2 className="text-lg font-medium text-[var(--uvai-ink)]">Base URL</h2>
              <code className={`mt-2 block text-sm ${CODE_CLASS}`}>https://uvai.io</code>
              <p className="mt-3 text-sm text-[var(--uvai-ink-soft)]">
                Want to run it yourself? UVAI is MIT-licensed.{' '}
                <a
                  href="https://github.com/groupthinking/EventRelay"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={LINK_CLASS}
                >
                  See the EventRelay repo
                </a>{' '}
                for self-hosting.
              </p>
            </section>

            <section id="endpoints" className="space-y-3">
              <h2 className="text-2xl font-medium tracking-tight text-[var(--uvai-ink)]">Endpoints</h2>
              <ul className="divide-y divide-[var(--uvai-border)] rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)]">
                {ENDPOINTS.map((e) => (
                  <li key={`${e.method}-${e.path}`} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:gap-4">
                    <span
                      className={`inline-flex h-6 shrink-0 items-center justify-center rounded-md border px-2 font-mono text-xs font-bold ${METHOD_COLOR[e.method]}`}
                    >
                      {e.method}
                    </span>
                    <div className="min-w-0 flex-1">
                      <code className="break-all font-mono text-sm text-[var(--uvai-ink)]">{e.path}</code>
                      <p className="mt-1 text-sm text-[var(--uvai-ink-soft)]">{e.summary}</p>
                      {e.body ? (
                        <pre className="mt-2 overflow-x-auto rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-bg)] p-3 text-xs text-[var(--uvai-ink-soft)]">
                          <code>{e.body}</code>
                        </pre>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </section>

            <section id="checklist" className="mt-10 space-y-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-2xl font-medium tracking-tight text-[var(--uvai-ink)]">
                  Build &amp; Launch Checklist
                </h2>
                <span className="font-mono text-xs text-[var(--uvai-ink-faint)]">
                  Webflow · MDN QA alignment
                </span>
              </div>
              <div className="space-y-3">
                {LAUNCH_CHECKLIST.map((group) => (
                  <div
                    key={group.phase}
                    className="rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] p-4 sm:p-5"
                  >
                    <h3 className="text-sm font-semibold text-[var(--uvai-ink)]">{group.phase}</h3>
                    <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-[var(--uvai-ink-soft)]">
                      {group.items.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>

            <section id="try-it" className="mt-10">
              <h2 className="text-2xl font-medium tracking-tight text-[var(--uvai-ink)]">Try it</h2>
              <p className="mt-2 text-[var(--uvai-ink-soft)]">
                The{' '}
                <Link href="/studio" className={LINK_CLASS}>
                  studio
                </Link>{' '}
                runs the end-to-end YouTube workflow against a real URL: hashed Video
                Pack via <code className={CODE_CLASS}>/api/video/pack</code>, then{' '}
                <code className={CODE_CLASS}>/api/workflows/video-to-actions</code>.
              </p>
              <ol className="mt-4 list-decimal space-y-1 pl-5 text-sm text-[var(--uvai-ink-soft)]">
                <li>Paste a YouTube URL on Home.</li>
                <li>Home redirects to <code className={CODE_CLASS}>/studio?video=...</code>.</li>
                <li>Studio auto-starts analysis once for that handoff URL.</li>
                <li>Transcript and events flow into actions and output publishing.</li>
              </ol>
            </section>
          </div>

          <aside
            aria-label="In this article"
            className="space-y-4 rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] p-5 lg:sticky lg:top-6"
          >
            <div>
              <p className="uvai-label">On this page</p>
              <ul className="mt-3 space-y-2 text-sm text-[var(--uvai-ink-soft)]">
                <li><a href="#overview" className="hover:text-[var(--uvai-ink)]">Overview</a></li>
                <li><a href="#base-url" className="hover:text-[var(--uvai-ink)]">Base URL</a></li>
                <li><a href="#endpoints" className="hover:text-[var(--uvai-ink)]">Endpoints</a></li>
                <li><a href="#checklist" className="hover:text-[var(--uvai-ink)]">Build &amp; Launch Checklist</a></li>
                <li><a href="#try-it" className="hover:text-[var(--uvai-ink)]">Try it in Studio</a></li>
              </ul>
            </div>
            <div className="border-t border-[var(--uvai-border)] pt-4">
              <p className="text-xs leading-relaxed text-[var(--uvai-ink-soft)]">
                Open the interactive split workbench to analyze a YouTube URL or download this reference as Markdown.
              </p>
              <Link href="/studio" className="uvai-btn uvai-btn-primary mt-3 w-full justify-center text-xs">
                Open Studio
              </Link>
            </div>
          </aside>
        </div>
      </main>
      <Footer />
    </div>
  );
}
