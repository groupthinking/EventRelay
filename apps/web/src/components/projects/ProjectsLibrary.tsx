'use client';

import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import AppShell from '@/components/AppShell';
import Footer from '@/components/Footer';
import {
  MAX_LOCAL_PROJECTS,
  createOrUpdateLocalProject,
  deleteLocalProject,
  readLocalProjects,
  removeLocalProjectsByIds,
  updateLocalProject,
} from '@/lib/projects/project-local-store';
import {
  PROJECT_VISIBILITIES,
  type ProjectRecord,
  type ProjectVisibility,
} from '@/lib/projects/project-types';
import { resolveYouTubeSourceId } from '@/lib/video-source-identity';
import '@/styles/projects-library.css';

type Tab = 'all' | ProjectVisibility;
const TABS: ReadonlyArray<{ id: Tab; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'private', label: 'Private' },
  { id: 'shared', label: 'Shared' },
];

async function callProjects(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  url: string,
  body?: unknown,
): Promise<{ ok: boolean; status: number; data: Record<string, unknown> | null }> {
  try {
    const response = await fetch(url, {
      method,
      credentials: 'same-origin',
      ...(body === undefined
        ? {}
        : { headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }),
    });
    const data = (await response.json().catch(() => null)) as Record<string, unknown> | null;
    return { ok: response.ok, status: response.status, data };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

const SAFE_VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;

/** Allowlist + encode at the sink: storage-derived ids never reach `src` unchecked. */
function projectThumbnailSrc(videoId: string): string | null {
  const match = SAFE_VIDEO_ID.exec(videoId);
  return match ? `https://i.ytimg.com/vi/${encodeURIComponent(match[0])}/hqdefault.jpg` : null;
}

function errorMessage(data: Record<string, unknown> | null, fallback: string): string {
  return typeof data?.error === 'string' ? data.error : fallback;
}

/** Honest copy for guest-storage failures; never reported as success. */
function localFailureMessage(
  reason: 'invalid_source_url' | 'limit_reached' | 'storage_unavailable' | 'not_found',
): string {
  switch (reason) {
    case 'invalid_source_url':
      return 'Enter a valid YouTube video URL to create a project.';
    case 'limit_reached':
      return `Browser storage is limited to ${MAX_LOCAL_PROJECTS} local projects. Delete one or sign in to save more.`;
    case 'not_found':
      return 'That project no longer exists in this browser.';
    default:
      return 'Browser storage is full or blocked. Free space or sign in to save projects.';
  }
}

/**
 * Plan 005 P2 library. One Project == one canonical YouTube source. Signed-in users use the
 * durable `/api/projects` store; guests (or an unavailable store) use honest local-only storage.
 */
export default function ProjectsLibrary() {
  const { status: sessionStatus } = useSession();
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [localCount, setLocalCount] = useState(0);
  const [cloudFallback, setCloudFallback] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>('all');
  const [search, setSearch] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [title, setTitle] = useState('');
  const [visibility, setVisibility] = useState<ProjectVisibility>('private');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const signedIn = sessionStatus === 'authenticated';
  const remote = signedIn && !cloudFallback;

  const load = useCallback(async () => {
    if (sessionStatus === 'loading') return;
    const local = readLocalProjects();
    setLocalCount(local.length);
    if (sessionStatus !== 'authenticated') {
      setCloudFallback(false);
      setProjects(local);
      setLoading(false);
      return;
    }
    const result = await callProjects('GET', '/api/projects');
    if (result.ok && Array.isArray(result.data?.projects)) {
      setCloudFallback(false);
      setProjects(result.data.projects as ProjectRecord[]);
    } else {
      setCloudFallback(true);
      setProjects(local);
    }
    setLoading(false);
  }, [sessionStatus]);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return projects.filter((project) => {
      if (tab !== 'all' && project.visibility !== tab) return false;
      if (!needle) return true;
      return [project.title, project.videoId, project.sourceUrl].some((value) =>
        value.toLowerCase().includes(needle),
      );
    });
  }, [projects, tab, search]);

  const counts = useMemo(
    () => ({
      all: projects.length,
      private: projects.filter((project) => project.visibility === 'private').length,
      shared: projects.filter((project) => project.visibility === 'shared').length,
    }),
    [projects],
  );

  const onCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setNotice('');
    if (!resolveYouTubeSourceId(sourceUrl)) {
      setError('Enter a valid YouTube video URL to create a project.');
      return;
    }
    setError('');
    const cleanTitle = title.trim() || undefined;
    if (remote) {
      const result = await callProjects('POST', '/api/projects', {
        sourceUrl: sourceUrl.trim(),
        title: cleanTitle,
        visibility,
      });
      if (!result.ok) {
        setError(errorMessage(result.data, 'The project could not be created. Try again.'));
        return;
      }
      setNotice(result.data?.created === false ? 'Project already exists for this video.' : 'Project created.');
    } else {
      const result = createOrUpdateLocalProject({ sourceUrl, title: cleanTitle, visibility });
      if (!result.ok) {
        setError(localFailureMessage(result.reason));
        return;
      }
      setNotice(result.created ? 'Project created in this browser.' : 'Project already exists for this video.');
    }
    setSourceUrl('');
    setTitle('');
    await load();
  };

  const onToggleVisibility = async (project: ProjectRecord) => {
    const next: ProjectVisibility = project.visibility === 'shared' ? 'private' : 'shared';
    if (project.storage === 'remote') {
      const result = await callProjects('PATCH', `/api/projects/${project.id}`, { visibility: next });
      if (!result.ok) {
        setError(errorMessage(result.data, 'Visibility could not be changed.'));
        return;
      }
    } else {
      const result = updateLocalProject(project.id, { visibility: next });
      if (!result.ok) {
        setError(localFailureMessage(result.reason));
        return;
      }
    }
    setError('');
    setNotice(`Project is now ${next}.`);
    await load();
  };

  const onRename = async (project: ProjectRecord) => {
    const next = renameValue.trim();
    if (!next) {
      setError('Project title cannot be empty.');
      return;
    }
    if (project.storage === 'remote') {
      const result = await callProjects('PATCH', `/api/projects/${project.id}`, { title: next });
      if (!result.ok) {
        setError(errorMessage(result.data, 'The project could not be renamed.'));
        return;
      }
    } else {
      const result = updateLocalProject(project.id, { title: next });
      if (!result.ok) {
        setError(localFailureMessage(result.reason));
        return;
      }
    }
    setError('');
    setRenamingId(null);
    setNotice('Project renamed.');
    await load();
  };

  const onDelete = async (project: ProjectRecord) => {
    if (project.storage === 'remote') {
      const result = await callProjects('DELETE', `/api/projects/${project.id}`);
      if (!result.ok) {
        setError(errorMessage(result.data, 'The project could not be deleted.'));
        return;
      }
    } else {
      const result = deleteLocalProject(project.id);
      if (!result.ok) {
        setError(localFailureMessage(result.reason));
        return;
      }
    }
    setError('');
    setConfirmDeleteId(null);
    setNotice('Project deleted.');
    await load();
  };

  const onImport = async () => {
    const local = readLocalProjects();
    const imported: string[] = [];
    for (const project of local) {
      const result = await callProjects('POST', '/api/projects', {
        sourceUrl: project.sourceUrl,
        title: project.title,
        visibility: project.visibility,
      });
      if (result.ok) imported.push(project.id);
    }
    const cleared = removeLocalProjectsByIds(imported);
    setNotice(`Imported ${imported.length} of ${local.length} local project(s).`);
    if (!cleared) {
      setError('Imported projects to your account, but local browser copies could not be cleared.');
    }
    await load();
  };

  return (
    <AppShell>
      <main className="pl" data-testid="projects-library">
        <div className="pl-inner">
          <header className="pl-head">
            <h1 id="projects-heading" className="pl-title">
              Projects
            </h1>
            <p className="pl-lede">
              One project per YouTube video. Each project opens the same hashed Video Pack run in Studio.
            </p>
          </header>

          {sessionStatus === 'unauthenticated' ? (
            <p className="pl-banner" data-testid="guest-banner">
              <span>Sign in to save projects across devices. Until then they stay in this browser only.</span>
              <Link href="/login?callbackUrl=%2Fprojects">Sign in to save</Link>
            </p>
          ) : null}
          {signedIn && cloudFallback ? (
            <p className="pl-banner" role="status">
              Cloud project storage is currently unavailable — showing local browser projects.
            </p>
          ) : null}
          {remote && localCount > 0 ? (
            <p className="pl-banner">
              <span>You have {localCount} local project(s) in this browser.</span>
              <button type="button" className="pl-btn" onClick={() => void onImport()}>
                Import local projects
              </button>
            </p>
          ) : null}

          <form className="pl-create" onSubmit={onCreate} noValidate aria-labelledby="projects-heading">
            <div className="pl-field">
              <label htmlFor="project-create-url">YouTube URL</label>
              <input
                id="project-create-url"
                name="sourceUrl"
                type="url"
                inputMode="url"
                autoComplete="off"
                placeholder="https://www.youtube.com/watch?v=…"
                value={sourceUrl}
                onChange={(event) => setSourceUrl(event.target.value)}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'project-create-error' : undefined}
              />
            </div>
            <div className="pl-field">
              <label htmlFor="project-create-title">Project title (optional)</label>
              <input
                id="project-create-title"
                name="title"
                type="text"
                autoComplete="off"
                maxLength={160}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>
            <div className="pl-field">
              <label htmlFor="project-create-visibility">Visibility</label>
              <select
                id="project-create-visibility"
                name="visibility"
                value={visibility}
                onChange={(event) => setVisibility(event.target.value as ProjectVisibility)}
              >
                {PROJECT_VISIBILITIES.map((item) => (
                  <option key={item} value={item}>
                    {item === 'private' ? 'Private' : 'Shared'}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="uvai-btn uvai-btn-primary">
              Create new project
            </button>
          </form>
          {error ? (
            <p id="project-create-error" className="pl-error" role="alert">
              {error}
            </p>
          ) : null}
          <p className="pl-status" aria-live="polite">
            {notice}
          </p>

          <div className="pl-toolbar">
            <div className="pl-tabs" role="tablist" aria-label="Project visibility">
              {TABS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  id={`projects-tab-${item.id}`}
                  aria-selected={tab === item.id}
                  aria-controls="projects-panel"
                  className="pl-tab"
                  onClick={() => setTab(item.id)}
                >
                  {item.label} ({counts[item.id]})
                </button>
              ))}
            </div>
            <div className="pl-search">
              <label htmlFor="projects-search" className="sr-only">
                Search projects
              </label>
              <input
                id="projects-search"
                name="projectsSearch"
                type="search"
                autoComplete="off"
                placeholder="Search projects by title or video ID"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>

          <div id="projects-panel" role="tabpanel" aria-labelledby={`projects-tab-${tab}`}>
            {loading ? (
              <p className="pl-empty">Loading projects…</p>
            ) : visible.length === 0 ? (
              <p className="pl-empty">
                {projects.length === 0
                  ? 'No projects yet. Paste a YouTube URL above to create your first one.'
                  : 'No projects match this filter.'}
              </p>
            ) : (
              <ul className="pl-grid">
                {visible.map((project) => {
                  const thumbSrc = projectThumbnailSrc(project.videoId);
                  return (
                  <li key={project.id} className="pl-card" data-testid="project-card">
                    {thumbSrc ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img className="pl-thumb" src={thumbSrc} alt="" loading="lazy" />
                    ) : (
                      <div className="pl-thumb" aria-hidden="true" />
                    )}
                    <div className="pl-card-body">
                      {renamingId === project.id ? (
                        <div className="pl-rename">
                          <div>
                            <label htmlFor={`project-rename-${project.id}`} className="sr-only">
                              Project title
                            </label>
                            <input
                              id={`project-rename-${project.id}`}
                              name="renameTitle"
                              type="text"
                              maxLength={160}
                              value={renameValue}
                              onChange={(event) => setRenameValue(event.target.value)}
                            />
                          </div>
                          <button type="button" className="pl-btn" onClick={() => void onRename(project)}>
                            Save
                          </button>
                          <button type="button" className="pl-btn" onClick={() => setRenamingId(null)}>
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <h2 className="pl-card-title">{project.title}</h2>
                      )}
                      <div className="pl-badges">
                        <span className="pl-badge" data-kind={project.visibility}>
                          {project.visibility === 'shared' ? 'Shared' : 'Private'}
                        </span>
                        {project.storage === 'local' ? <span className="pl-badge">Local only</span> : null}
                        <span className="pl-badge">{project.videoId}</span>
                      </div>
                      <div className="pl-actions">
                        <Link
                          className="pl-btn"
                          href={`/studio?video=${encodeURIComponent(project.sourceUrl)}`}
                        >
                          Open in Studio
                        </Link>
                        <button type="button" className="pl-btn" onClick={() => void onToggleVisibility(project)}>
                          {project.visibility === 'shared' ? 'Make private' : 'Make shared'}
                        </button>
                        <button
                          type="button"
                          className="pl-btn"
                          onClick={() => {
                            setRenamingId(project.id);
                            setRenameValue(project.title);
                          }}
                        >
                          Rename
                        </button>
                        {confirmDeleteId === project.id ? (
                          <>
                            <button
                              type="button"
                              className="pl-btn"
                              data-danger="true"
                              onClick={() => void onDelete(project)}
                            >
                              Confirm delete
                            </button>
                            <button type="button" className="pl-btn" onClick={() => setConfirmDeleteId(null)}>
                              Cancel
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            className="pl-btn"
                            data-danger="true"
                            onClick={() => setConfirmDeleteId(project.id)}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </div>
                  </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
        <Footer variant="compact" />
      </main>
    </AppShell>
  );
}
