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
  { method: 'GET', path: '/api/pipeline', summary: 'Inspect available pipeline stages.' },
  { method: 'POST', path: '/api/pipeline', summary: 'Run the full intake to agents pipeline.' },
  { method: 'POST', path: '/api/pipeline/stream', summary: 'Streaming variant of /api/pipeline (SSE).' },
  { method: 'POST', path: '/api/chat', summary: 'Conversational query over an analyzed video.' },
  { method: 'GET', path: '/api/video', summary: 'List recently analyzed videos.' },
  { method: 'POST', path: '/api/video', summary: 'Register a new video for analysis.' },
  { method: 'GET', path: '/api/video/search', summary: 'Semantic search across stored videos.' },
  { method: 'GET', path: '/api/dashboard', summary: 'Dashboard aggregates and recent runs.' },
  { method: 'POST', path: '/api/dashboard', summary: 'Mutate dashboard state (pin, archive, etc.).' },
  { method: 'GET', path: '/api/training/status', summary: 'Current status of training/embedding jobs.' },
  { method: 'POST', path: '/api/training/trigger', summary: 'Trigger a training/embedding job.' },
];

const METHOD_COLOR: Record<Endpoint['method'], string> = {
  GET: 'bg-teal-500/10 border-teal-500/30 text-teal-300',
  POST: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
};

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen bg-void text-ink">
      <Nav />
      <main className="mx-auto max-w-4xl px-6 py-20">
        <header className="mb-12">
          <p className="text-xs uppercase tracking-[0.2em] text-ink/40">Reference</p>
          <h1 className="mt-2 font-heading text-4xl font-black">API Reference</h1>
          <p className="mt-3 max-w-2xl text-ink/60">
            UVAI exposes a small, REST-style surface for transcription, event
            extraction, pipeline execution, and search. All endpoints accept
            and return JSON unless noted. Streaming endpoints use Server-Sent
            Events.
          </p>
        </header>

        <section className="mb-10 rounded-xl border border-white/5 bg-white/[0.02] p-6">
          <h2 className="font-heading text-lg font-bold text-ink">Base URL</h2>
          <code className="mt-2 block text-sm text-teal-300">https://uvai.io</code>
          <p className="mt-3 text-sm text-ink/60">
            Want to run it yourself? UVAI is MIT-licensed.{' '}
            <a
              href="https://github.com/groupthinking/EventRelay"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-400 hover:underline"
            >
              See the EventRelay repo
            </a>{' '}
            for self-hosting.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="font-heading text-2xl font-bold text-ink">Endpoints</h2>
          <ul className="divide-y divide-white/5 rounded-xl border border-white/5">
            {ENDPOINTS.map((e) => (
              <li key={`${e.method}-${e.path}`} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:gap-4">
                <span
                  className={`inline-flex h-6 shrink-0 items-center justify-center rounded-md border px-2 font-mono text-xs font-bold ${METHOD_COLOR[e.method]}`}
                >
                  {e.method}
                </span>
                <div className="flex-1">
                  <code className="font-mono text-sm text-ink">{e.path}</code>
                  <p className="mt-1 text-sm text-ink/60">{e.summary}</p>
                  {e.body ? (
                    <pre className="mt-2 overflow-x-auto rounded-md border border-white/5 bg-black/40 p-3 text-xs text-ink/70">
                      <code>{e.body}</code>
                    </pre>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-12">
          <h2 className="font-heading text-2xl font-bold text-ink">Try it</h2>
          <p className="mt-2 text-ink/60">
            The{' '}
            <Link href="/playground" className="text-teal-400 hover:underline">
              playground
            </Link>{' '}
            exercises these endpoints end-to-end against a real YouTube URL.
          </p>
        </section>
      </main>
      <Footer />
    </div>
  );
}
