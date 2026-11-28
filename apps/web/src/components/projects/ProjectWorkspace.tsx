'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { ArrowLeft } from 'lucide-react';
import AppShell from '@/components/AppShell';
import Footer from '@/components/Footer';
import { emitVideoPack, verifyIdentityPack, type EmittedVideoPack } from '@/lib/emit-video-pack';
import { readLocalProjects } from '@/lib/projects/project-local-store';
import type { ProjectRecord } from '@/lib/projects/project-types';
import {
  PROJECT_VIEWS,
  buildProjectFolders,
  parseProjectTime,
  parseProjectView,
  resolveProjectFolder,
  type ProjectView,
} from '@/lib/projects/project-workspace';
import ProjectBriefView, { type PackStatus } from './ProjectBriefView';
import ProjectRunView from './ProjectRunView';
import { ProjectCanvasView, ProjectElementsView } from './ProjectSecondaryViews';
import '@/styles/project-workspace.css';

const SOURCE_HASH = /^[a-f0-9]{64}$/;
const POLL_MS = 3_000;
const MAX_POLLS = 40;

type ProjectState =
  | { status: 'loading' }
  | { status: 'ready'; project: ProjectRecord }
  | { status: 'missing' };

type PackResult =
  | { status: 'ready'; pack: EmittedVideoPack }
  | { status: 'processing' }
  | { status: 'missing' }
  | { status: 'error'; error: string };

const VIEW_LABELS: Record<ProjectView, string> = {
  brief: 'Brief',
  run: 'Run',
  elements: 'Elements',
  canvas: 'Canvas',
};

async function fetchStoredPack(project: ProjectRecord, signal: AbortSignal): Promise<PackResult> {
  const query = SOURCE_HASH.test(project.sourceHash)
    ? `source_hash=${project.sourceHash}`
    : `video_id=${encodeURIComponent(project.videoId)}`;
  try {
    const response = await fetch(`/api/video/pack?${query}`, { signal });
    if (response.status === 404) return { status: 'missing' };
    if (response.status === 202) return { status: 'processing' };
    const payload: unknown = await response.json().catch(() => null);
    if (response.ok) {
      try {
        return { status: 'ready', pack: verifyIdentityPack(payload).pack };
      } catch (error) {
        return { status: 'error', error: error instanceof Error ? error.message : 'The Video Pack is invalid.' };
      }
    }
    const record = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
    const message =
      typeof record.error === 'string' ? record.error : typeof record.detail === 'string' ? record.detail : null;
    return { status: 'error', error: message ?? `The Video Pack could not be loaded (${response.status}).` };
  } catch (error) {
    if (signal.aborted) return { status: 'processing' };
    return { status: 'error', error: error instanceof Error ? error.message : 'The Video Pack could not be loaded.' };
  }
}

/** `/projects/[projectId]`: sidebar (Brief, Run, Elements, Canvas, chapter folders) + the selected view. */
export default function ProjectWorkspace({ projectId }: { projectId: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { status: sessionStatus } = useSession();

  const [projectState, setProjectState] = useState<ProjectState>({ status: 'loading' });
  const [pack, setPack] = useState<EmittedVideoPack | null>(null);
  const [packStatus, setPackStatus] = useState<PackStatus>('loading');
  const [packError, setPackError] = useState<string | null>(null);
  const extractingRef = useRef(false);
  const pollsRef = useRef(0);
  const extractAbortRef = useRef<AbortController | null>(null);

  const project = projectState.status === 'ready' ? projectState.project : null;

  // Load the project: durable store first when signed in, then this browser's guest projects.
  useEffect(() => {
    if (sessionStatus === 'loading') return;
    let cancelled = false;
    const findLocal = () => readLocalProjects().find((entry) => entry.id === projectId) ?? null;
    void (async () => {
      if (sessionStatus === 'authenticated') {
        try {
          const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, { credentials: 'same-origin' });
          if (response.ok) {
            const data = (await response.json()) as { project?: ProjectRecord };
            if (!cancelled && data.project) {
              setProjectState({ status: 'ready', project: data.project });
              return;
            }
          }
        } catch {
          // Fall through to local projects.
        }
      }
      const local = findLocal();
      if (!cancelled) setProjectState(local ? { status: 'ready', project: local } : { status: 'missing' });
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, sessionStatus]);

  const applyPackResult = useCallback((result: PackResult) => {
    if (result.status === 'ready') {
      setPack(result.pack);
      setPackStatus('ready');
      setPackError(null);
    } else if (result.status === 'error') {
      setPackStatus('error');
      setPackError(result.error);
    } else {
      setPackStatus(result.status);
      setPackError(null);
    }
  }, []);

  // Read any stored pack. This never starts an extraction on its own.
  useEffect(() => {
    if (!project) return;
    const controller = new AbortController();
    pollsRef.current = 0;
    setPackStatus('loading');
    void fetchStoredPack(project, controller.signal).then((result) => {
      if (!controller.signal.aborted && !extractingRef.current) applyPackResult(result);
    });
    return () => controller.abort();
  }, [project, applyPackResult]);

  // While a stored extraction is still running, poll politely and give up eventually.
  useEffect(() => {
    if (!project || packStatus !== 'processing' || extractingRef.current) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      pollsRef.current += 1;
      if (pollsRef.current > MAX_POLLS) {
        setPackStatus('error');
        setPackError('Extraction is taking longer than expected. Reload to check again.');
        return;
      }
      void fetchStoredPack(project, controller.signal).then((result) => {
        if (!controller.signal.aborted && !extractingRef.current) applyPackResult(result);
      });
    }, POLL_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [project, packStatus, applyPackResult]);

  useEffect(() => () => extractAbortRef.current?.abort(), []);

  const onExtractPack = useCallback(() => {
    if (!project || extractingRef.current) return;
    extractingRef.current = true;
    const controller = new AbortController();
    extractAbortRef.current = controller;
    setPackStatus('processing');
    setPackError(null);
    void emitVideoPack(project.sourceUrl, { signal: controller.signal, timeoutMs: 120_000 })
      .then((citation) => {
        if (controller.signal.aborted) return;
        setPack(citation.pack);
        setPackStatus('ready');
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setPackStatus('error');
        setPackError(error instanceof Error ? error.message : 'Video Pack extraction failed.');
      })
      .finally(() => {
        extractingRef.current = false;
      });
  }, [project]);

  const view = parseProjectView(searchParams.get('view'));
  const t = parseProjectTime(searchParams.get('t'));
  const folders = useMemo(() => buildProjectFolders(pack), [pack]);
  const folder = resolveProjectFolder(folders, searchParams.get('folder'));

  const setQuery = useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === null) next.delete(key);
        else next.set(key, value);
      }
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const selectView = (next: ProjectView) => setQuery({ view: next === 'brief' ? null : next });
  const selectFolder = (id: string) => {
    const target = folders.find((entry) => entry.id === id) ?? folders[0];
    setQuery({
      view: 'run',
      folder: target.id === 'all' ? null : target.id,
      t: target.start != null ? String(target.start) : null,
    });
  };
  const openChapter = (chapterNumber: number, startSeconds: number) =>
    setQuery({ view: 'run', folder: `ch-${chapterNumber}`, t: String(startSeconds) });
  const seekUrl = (seconds: number) => setQuery({ view: 'run', t: String(Math.max(0, Math.floor(seconds))) });

  if (projectState.status === 'loading') {
    return (
      <AppShell>
        <main className="pw" data-testid="project-workspace">
          <div className="pw-inner">
            <p className="pw-card pw-muted" role="status">
              Loading project…
            </p>
          </div>
        </main>
      </AppShell>
    );
  }

  if (!project) {
    return (
      <AppShell>
        <main className="pw" data-testid="project-workspace">
          <div className="pw-inner">
            <section className="pw-card" data-testid="project-not-found">
              <h1 className="pw-title">Project not found</h1>
              <p>This project does not exist, or it is not saved in this browser or your account.</p>
              <div>
                <Link className="pw-btn" href="/projects">
                  Back to Projects
                </Link>
              </div>
            </section>
          </div>
        </main>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <main className="pw" data-testid="project-workspace">
        <div className="pw-inner">
          <aside className="pw-side" aria-label="Project">
            <Link href="/projects" className="pw-back">
              <ArrowLeft size={14} aria-hidden="true" /> Back to Projects
            </Link>
            <div>
              <h2 className="pw-side-title">{project.title}</h2>
              <div className="pw-badges">
                <span className="pw-badge">{project.videoId}</span>
                <span className="pw-badge">{project.visibility === 'shared' ? 'Shared' : 'Private'}</span>
                {project.storage === 'local' ? <span className="pw-badge">Local only</span> : null}
              </div>
            </div>

            <nav aria-label="Project sections">
              <p className="pw-group-label">Workspace</p>
              <ul className="pw-nav">
                {PROJECT_VIEWS.filter((entry) => entry !== 'canvas').map((entry) => (
                  <li key={entry}>
                    <button
                      type="button"
                      className="pw-nav-btn"
                      data-testid={`project-nav-${entry}`}
                      aria-current={view === entry ? 'page' : undefined}
                      onClick={() => selectView(entry)}
                    >
                      {VIEW_LABELS[entry]}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="pw-group-label" style={{ marginTop: 12 }}>
                Tools
              </p>
              <ul className="pw-nav">
                <li>
                  <button
                    type="button"
                    className="pw-nav-btn"
                    data-testid="project-nav-canvas"
                    aria-current={view === 'canvas' ? 'page' : undefined}
                    onClick={() => selectView('canvas')}
                  >
                    Canvas
                  </button>
                </li>
              </ul>
            </nav>

            <nav aria-label="Folders">
              <p className="pw-group-label">Folders</p>
              <ul className="pw-folders" data-testid="project-folders">
                {folders.map((entry) => (
                  <li key={entry.id}>
                    <button
                      type="button"
                      className="pw-folder"
                      data-testid={`project-folder-${entry.id}`}
                      aria-current={folder.id === entry.id ? 'true' : undefined}
                      onClick={() => selectFolder(entry.id)}
                    >
                      <span className="pw-folder-label">
                        <span>{entry.label}</span>
                        {entry.id !== 'all' ? <span className="pw-folder-topic">{entry.topic}</span> : null}
                      </span>
                      <span className="pw-folder-count" data-testid={`project-folder-count-${entry.id}`}>
                        {entry.id === 'all'
                          ? entry.assetCount
                          : `${entry.keyframeCount}k · ${entry.eventCount}e`}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              {!pack ? <p className="pw-muted">Folders appear once chapters are extracted.</p> : null}
            </nav>

            <Link className="pw-btn" href={`/studio?video=${encodeURIComponent(project.sourceUrl)}`}>
              Open in Studio
            </Link>
          </aside>

          <div className="pw-main pw-container">
            <header className="pw-head">
              <div>
                <h1 className="pw-title">{project.title}</h1>
                <p className="pw-sub">
                  {VIEW_LABELS[view]} ·{' '}
                  <a href={project.sourceUrl} target="_blank" rel="noopener noreferrer">
                    Watch on YouTube
                  </a>
                </p>
              </div>
            </header>

            {view === 'brief' ? (
              <ProjectBriefView
                project={project}
                pack={pack}
                packStatus={packStatus}
                packError={packError}
                onExtractPack={onExtractPack}
                onOpenChapter={openChapter}
              />
            ) : null}
            {view === 'run' ? (
              <ProjectRunView
                project={project}
                pack={pack}
                packStatus={packStatus}
                folder={folder}
                t={t}
                onSeekUrl={seekUrl}
                onSelectFolder={selectFolder}
                onExtractPack={onExtractPack}
              />
            ) : null}
            {view === 'elements' ? <ProjectElementsView project={project} pack={pack} packStatus={packStatus} /> : null}
            {view === 'canvas' ? <ProjectCanvasView project={project} pack={pack} packStatus={packStatus} /> : null}
          </div>
        </div>
        <Footer variant="compact" />
      </main>
    </AppShell>
  );
}
