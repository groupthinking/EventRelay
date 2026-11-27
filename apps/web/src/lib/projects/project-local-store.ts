import { canonicalYouTubeSource, resolveYouTubeSourceId } from '@/lib/video-source-identity';
import {
  PROJECT_VISIBILITIES,
  defaultProjectTitle,
  type ProjectRecord,
  type ProjectVisibility,
} from './project-types';

/** Guest (local-first) projects. Browser-only; never throws on bad storage or SSR. */
export const LOCAL_PROJECTS_STORAGE_KEY = 'uvai-local-projects-v1';
const MAX_LOCAL_PROJECTS = 50;

function newId(): string {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  } catch {
    // fall through
  }
  return `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function isProject(value: unknown): value is ProjectRecord {
  if (!value || typeof value !== 'object') return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.id === 'string' &&
    row.id.length > 0 &&
    typeof row.sourceUrl === 'string' &&
    typeof row.videoId === 'string' &&
    resolveYouTubeSourceId(row.sourceUrl) === row.videoId &&
    typeof row.title === 'string' &&
    row.title.trim().length > 0 &&
    typeof row.visibility === 'string' &&
    (PROJECT_VISIBILITIES as readonly string[]).includes(row.visibility) &&
    typeof row.createdAt === 'string' &&
    typeof row.updatedAt === 'string'
  );
}

export function readLocalProjects(): ProjectRecord[] {
  try {
    if (typeof window === 'undefined') return [];
    const raw = window.localStorage.getItem(LOCAL_PROJECTS_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(isProject)
      .map((project) => ({ ...project, sourceHash: '', storage: 'local' as const }))
      .slice(0, MAX_LOCAL_PROJECTS);
  } catch {
    return [];
  }
}

function writeLocalProjects(projects: ProjectRecord[]): void {
  try {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(LOCAL_PROJECTS_STORAGE_KEY, JSON.stringify(projects.slice(0, MAX_LOCAL_PROJECTS)));
  } catch {
    // Storage full or blocked: guest mode degrades to in-memory for this session.
  }
}

export type LocalProjectInput = { sourceUrl: string; title?: string; visibility?: ProjectVisibility };

/** Create a guest project, or return the existing one for the same video (single-source rule). */
export function createOrUpdateLocalProject(input: LocalProjectInput): {
  project: ProjectRecord;
  created: boolean;
} | null {
  const videoId = resolveYouTubeSourceId(input.sourceUrl);
  if (!videoId) return null;
  const projects = readLocalProjects();
  const existing = projects.find((project) => project.videoId === videoId);
  if (existing) return { project: existing, created: false };

  const now = new Date().toISOString();
  const project: ProjectRecord = {
    id: newId(),
    sourceHash: '',
    sourceUrl: canonicalYouTubeSource(videoId),
    videoId,
    title: input.title?.trim().slice(0, 160) || defaultProjectTitle(videoId),
    visibility: input.visibility ?? 'private',
    createdAt: now,
    updatedAt: now,
    storage: 'local',
  };
  writeLocalProjects([project, ...projects]);
  return { project, created: true };
}

export function updateLocalProject(
  id: string,
  patch: { title?: string; visibility?: ProjectVisibility },
): ProjectRecord | null {
  const projects = readLocalProjects();
  const index = projects.findIndex((project) => project.id === id);
  if (index < 0) return null;
  const title = patch.title?.trim().slice(0, 160);
  const next: ProjectRecord = {
    ...projects[index],
    ...(title ? { title } : {}),
    ...(patch.visibility ? { visibility: patch.visibility } : {}),
    updatedAt: new Date().toISOString(),
  };
  const rest = projects.filter((project) => project.id !== id);
  writeLocalProjects([next, ...rest]);
  return next;
}

export function deleteLocalProject(id: string): boolean {
  const projects = readLocalProjects();
  const remaining = projects.filter((project) => project.id !== id);
  if (remaining.length === projects.length) return false;
  writeLocalProjects(remaining);
  return true;
}

export function removeLocalProjectsByIds(ids: readonly string[]): void {
  const drop = new Set(ids);
  writeLocalProjects(readLocalProjects().filter((project) => !drop.has(project.id)));
}
