import { canonicalYouTubeSource, resolveYouTubeSourceId } from '@/lib/video-source-identity';
import {
  PROJECT_VISIBILITIES,
  defaultProjectTitle,
  type ProjectRecord,
  type ProjectVisibility,
} from './project-types';

/** Guest (local-first) projects. Browser-only; never throws on bad storage or SSR. */
export const LOCAL_PROJECTS_STORAGE_KEY = 'uvai-local-projects-v1';
export const MAX_LOCAL_PROJECTS = 50;

export type LocalCreateResult =
  | { ok: true; project: ProjectRecord; created: boolean }
  | { ok: false; reason: 'invalid_source_url' | 'limit_reached' | 'storage_unavailable' };
export type LocalUpdateResult =
  | { ok: true; project: ProjectRecord }
  | { ok: false; reason: 'not_found' | 'storage_unavailable' };
export type LocalDeleteResult =
  | { ok: true }
  | { ok: false; reason: 'not_found' | 'storage_unavailable' };

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
    return parsed.filter(isProject).map((project) => ({ ...project, sourceHash: '', storage: 'local' as const }));
  } catch {
    return [];
  }
}

/** Returns false when nothing was persisted (SSR, blocked, or full storage). Never truncates. */
function writeLocalProjects(projects: ProjectRecord[]): boolean {
  try {
    if (typeof window === 'undefined') return false;
    window.localStorage.setItem(LOCAL_PROJECTS_STORAGE_KEY, JSON.stringify(projects));
    return true;
  } catch {
    return false;
  }
}

export type LocalProjectInput = { sourceUrl: string; title?: string; visibility?: ProjectVisibility };

/**
 * Create a guest project, or return the existing one for the same video (single-source rule).
 * At the cap it refuses instead of evicting: the user decides what to delete.
 */
export function createOrUpdateLocalProject(input: LocalProjectInput): LocalCreateResult {
  const videoId = resolveYouTubeSourceId(input.sourceUrl);
  if (!videoId) return { ok: false, reason: 'invalid_source_url' };
  const projects = readLocalProjects();
  const existing = projects.find((project) => project.videoId === videoId);
  if (existing) return { ok: true, project: existing, created: false };
  if (projects.length >= MAX_LOCAL_PROJECTS) return { ok: false, reason: 'limit_reached' };

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
  if (!writeLocalProjects([project, ...projects])) return { ok: false, reason: 'storage_unavailable' };
  return { ok: true, project, created: true };
}

export function updateLocalProject(
  id: string,
  patch: { title?: string; visibility?: ProjectVisibility },
): LocalUpdateResult {
  const projects = readLocalProjects();
  const index = projects.findIndex((project) => project.id === id);
  if (index < 0) return { ok: false, reason: 'not_found' };
  const title = patch.title?.trim().slice(0, 160);
  const next: ProjectRecord = {
    ...projects[index],
    ...(title ? { title } : {}),
    ...(patch.visibility ? { visibility: patch.visibility } : {}),
    updatedAt: new Date().toISOString(),
  };
  const rest = projects.filter((project) => project.id !== id);
  if (!writeLocalProjects([next, ...rest])) return { ok: false, reason: 'storage_unavailable' };
  return { ok: true, project: next };
}

export function deleteLocalProject(id: string): LocalDeleteResult {
  const projects = readLocalProjects();
  const remaining = projects.filter((project) => project.id !== id);
  if (remaining.length === projects.length) return { ok: false, reason: 'not_found' };
  if (!writeLocalProjects(remaining)) return { ok: false, reason: 'storage_unavailable' };
  return { ok: true };
}

/** Returns false if the local copies could not be removed. */
export function removeLocalProjectsByIds(ids: readonly string[]): boolean {
  if (ids.length === 0) return true;
  const drop = new Set(ids);
  return writeLocalProjects(readLocalProjects().filter((project) => !drop.has(project.id)));
}
