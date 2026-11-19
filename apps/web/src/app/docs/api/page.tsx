import type { Metadata } from 'next';
import Link from 'next/link';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'API Reference',
  description:
    'HTTP reference for the UVAI / EventRelay public API: transcription, event extraction, agent pipelines, and video metadata.',
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
  { method: 'POST', path: '/api/extract-events', summary: 'Extract typed events from a transcript.' },
  { method: 'POST', path: '/api/chat', summary: 'Conversational query over an analyzed video.' },
  { method: 'GET', path: '/api/video', summary: 'Health probe for the video API.' },
  { method: 'POST', path: '/api/video', summary: 'Register a new video for analysis. [DEPRECATED — use /api/video/pack]' },
  { method: 'GET', path: '/api/video/search', summary: 'Semantic search across stored videos.' },
  { method: 'GET', path: '/api/dashboard', summary: 'Backend health as status and workflow metrics.' },
  { method: 'POST', path: '/api/dashboard', summary: 'Request a backend dashboard embed URL.' },
  { method: 'GET', path: '/api/training/status', summary: 'Current status of training/embedding jobs.' },
  { method: 'POST', path: '/api/training/trigger', summary: 'Trigger a training/embedding job.' },
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

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen bg-[var(--uvai-bg)] text-[var(--uvai-ink)]">
      <Nav />
      <main className="mx-auto max-w-4xl px-6 py-16">
        <header className="mb-10 border-b border-[var(--uvai-border-strong)] pb-8">
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
              <li aria-current="page" className="text-[var(--uvai-ink-soft)]">
                API Reference
              </li>
            </ol>
          </nav>
          <h1 className="mt-4 text-4xl font-medium tracking-tight">API Reference</h1>
          <p className="mt-3 max-w-2xl text-[var(--uvai-ink-soft)]">
            UVAI exposes a small, REST-style surface for transcription, event
            extraction, and search. All endpoints accept and return JSON unless noted.
          </p>
          <p className="mt-3 max-w-2xl text-sm text-[var(--uvai-ink-faint)]">
            The legacy <code>/api/pipeline</code> and <code>/api/pipeline/stream</code>
            routes are retired. <code>GET /api/video</code> is a health probe.
            <code>POST /api/video</code> remains for compatibility but is deprecated;
            use <code>POST /api/video/pack</code>.
          </p>
        </header>

        <section className="mb-10 rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] p-6">
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

        <section className="space-y-3">
          <h2 className="text-2xl font-medium tracking-tight text-[var(--uvai-ink)]">Endpoints</h2>
          <ul className="divide-y divide-[var(--uvai-border)] rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)]">
            {ENDPOINTS.map((e) => (
              <li key={`${e.method}-${e.path}`} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:gap-4">
                <span
                  className={`inline-flex h-6 shrink-0 items-center justify-center rounded-md border px-2 font-mono text-xs font-bold ${METHOD_COLOR[e.method]}`}
                >
                  {e.method}
                </span>
                <div className="flex-1">
                  <code className="font-mono text-sm text-[var(--uvai-ink)]">{e.path}</code>
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

        <section className="mt-12">
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
      </main>
      <Footer />
    </div>
  );
}
