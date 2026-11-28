/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  LOCAL_PROJECTS_STORAGE_KEY,
  MAX_LOCAL_PROJECTS,
  createOrUpdateLocalProject,
  deleteLocalProject,
  readLocalProjects,
  removeLocalProjectsByIds,
  updateLocalProject,
} from '../project-local-store';

const URL_A = 'https://www.youtube.com/watch?v=auJzb1D-fag';
const URL_B = 'https://www.youtube.com/watch?v=jNQXAC9IVRw';

/** Distinct, valid 11-char ids so every row passes the identity check. */
function videoIdAt(index: number): string {
  return `vid${String(index).padStart(8, '0')}`;
}

function seedLocalProjects(count: number): void {
  const now = '2026-11-27T00:00:00.000Z';
  const rows = Array.from({ length: count }, (_, index) => {
    const videoId = videoIdAt(index);
    return {
      id: `seed-${index}`,
      sourceUrl: `https://www.youtube.com/watch?v=${videoId}`,
      videoId,
      title: `Seed ${index}`,
      visibility: 'private',
      createdAt: now,
      updatedAt: now,
    };
  });
  window.localStorage.setItem(LOCAL_PROJECTS_STORAGE_KEY, JSON.stringify(rows));
}

beforeEach(() => window.localStorage.clear());
afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe('guest local project store', () => {
  it('survives malformed or non-array storage', () => {
    window.localStorage.setItem(LOCAL_PROJECTS_STORAGE_KEY, '{not json');
    expect(readLocalProjects()).toEqual([]);
    window.localStorage.setItem(LOCAL_PROJECTS_STORAGE_KEY, JSON.stringify({ a: 1 }));
    expect(readLocalProjects()).toEqual([]);
  });

  it('drops rows whose video id does not match their URL', () => {
    window.localStorage.setItem(
      LOCAL_PROJECTS_STORAGE_KEY,
      JSON.stringify([
        {
          id: 'x',
          sourceUrl: URL_A,
          videoId: 'jNQXAC9IVRw',
          title: 'Mismatch',
          visibility: 'private',
          createdAt: 'now',
          updatedAt: 'now',
        },
      ]),
    );
    expect(readLocalProjects()).toEqual([]);
  });

  it('creates a canonical local project and dedupes by video id', () => {
    const first = createOrUpdateLocalProject({ sourceUrl: 'https://youtu.be/auJzb1D-fag', title: 'Test Video Pack' });
    expect(first).toMatchObject({ ok: true, created: true });
    if (!first.ok) throw new Error('expected ok');
    expect(first.project).toMatchObject({
      sourceUrl: URL_A,
      videoId: 'auJzb1D-fag',
      title: 'Test Video Pack',
      visibility: 'private',
      storage: 'local',
      sourceHash: '',
    });
    const second = createOrUpdateLocalProject({ sourceUrl: URL_A });
    expect(second).toMatchObject({ ok: true, created: false });
    if (!second.ok) throw new Error('expected ok');
    expect(second.project.id).toBe(first.project.id);
    expect(readLocalProjects()).toHaveLength(1);
  });

  it('rejects invalid URLs', () => {
    expect(createOrUpdateLocalProject({ sourceUrl: 'https://example.com/x' })).toEqual({
      ok: false,
      reason: 'invalid_source_url',
    });
    expect(readLocalProjects()).toEqual([]);
  });

  it('renames, toggles visibility, and deletes', () => {
    const created = createOrUpdateLocalProject({ sourceUrl: URL_A });
    if (!created.ok) throw new Error('expected ok');
    const { project } = created;
    expect(updateLocalProject(project.id, { title: 'Renamed', visibility: 'shared' })).toMatchObject({
      ok: true,
      project: { title: 'Renamed', visibility: 'shared' },
    });
    expect(readLocalProjects()[0]).toMatchObject({ title: 'Renamed', visibility: 'shared' });
    expect(updateLocalProject('missing', { title: 'x' })).toEqual({ ok: false, reason: 'not_found' });
    expect(deleteLocalProject(project.id)).toEqual({ ok: true });
    expect(deleteLocalProject(project.id)).toEqual({ ok: false, reason: 'not_found' });
    expect(readLocalProjects()).toEqual([]);
  });

  it('removes only the listed ids', () => {
    const a = createOrUpdateLocalProject({ sourceUrl: URL_A });
    const b = createOrUpdateLocalProject({ sourceUrl: URL_B });
    if (!a.ok || !b.ok) throw new Error('expected ok');
    expect(removeLocalProjectsByIds([a.project.id])).toBe(true);
    expect(readLocalProjects().map((project) => project.id)).toEqual([b.project.id]);
    expect(removeLocalProjectsByIds([])).toBe(true);
  });
});

describe('local project cap', () => {
  it('refuses the 51st project instead of evicting the oldest', () => {
    seedLocalProjects(MAX_LOCAL_PROJECTS);
    expect(readLocalProjects()).toHaveLength(MAX_LOCAL_PROJECTS);

    expect(createOrUpdateLocalProject({ sourceUrl: URL_A })).toEqual({ ok: false, reason: 'limit_reached' });
    const after = readLocalProjects();
    expect(after).toHaveLength(MAX_LOCAL_PROJECTS);
    expect(after.some((project) => project.id === 'seed-0')).toBe(true);
    expect(after.some((project) => project.videoId === 'auJzb1D-fag')).toBe(false);
  });

  it('still returns an existing project at the cap and still allows edits and deletes', () => {
    seedLocalProjects(MAX_LOCAL_PROJECTS);
    const existingUrl = `https://www.youtube.com/watch?v=${videoIdAt(3)}`;
    expect(createOrUpdateLocalProject({ sourceUrl: existingUrl })).toMatchObject({ ok: true, created: false });
    expect(updateLocalProject('seed-3', { title: 'Edited' })).toMatchObject({ ok: true });
    expect(readLocalProjects()).toHaveLength(MAX_LOCAL_PROJECTS);
    expect(deleteLocalProject('seed-0')).toEqual({ ok: true });
    expect(createOrUpdateLocalProject({ sourceUrl: URL_A })).toMatchObject({ ok: true, created: true });
    expect(readLocalProjects()).toHaveLength(MAX_LOCAL_PROJECTS);
  });
});

describe('local storage write failures', () => {
  it('reports storage_unavailable instead of success when writes throw', () => {
    const created = createOrUpdateLocalProject({ sourceUrl: URL_A, title: 'Keep me' });
    if (!created.ok) throw new Error('expected ok');
    const before = window.localStorage.getItem(LOCAL_PROJECTS_STORAGE_KEY);

    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('quota exceeded', 'QuotaExceededError');
    });

    expect(createOrUpdateLocalProject({ sourceUrl: URL_B })).toEqual({ ok: false, reason: 'storage_unavailable' });
    expect(updateLocalProject(created.project.id, { title: 'Nope' })).toEqual({
      ok: false,
      reason: 'storage_unavailable',
    });
    expect(deleteLocalProject(created.project.id)).toEqual({ ok: false, reason: 'storage_unavailable' });
    expect(removeLocalProjectsByIds([created.project.id])).toBe(false);

    vi.restoreAllMocks();
    // Nothing was lost or half-written.
    expect(window.localStorage.getItem(LOCAL_PROJECTS_STORAGE_KEY)).toBe(before);
    expect(readLocalProjects()).toHaveLength(1);
  });
});
