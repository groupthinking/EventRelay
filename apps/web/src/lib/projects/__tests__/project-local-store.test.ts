/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  LOCAL_PROJECTS_STORAGE_KEY,
  createOrUpdateLocalProject,
  deleteLocalProject,
  readLocalProjects,
  removeLocalProjectsByIds,
  updateLocalProject,
} from '../project-local-store';

const URL_A = 'https://www.youtube.com/watch?v=auJzb1D-fag';
const URL_B = 'https://www.youtube.com/watch?v=jNQXAC9IVRw';

beforeEach(() => window.localStorage.clear());
afterEach(() => window.localStorage.clear());

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
    expect(first?.created).toBe(true);
    expect(first?.project).toMatchObject({
      sourceUrl: URL_A,
      videoId: 'auJzb1D-fag',
      title: 'Test Video Pack',
      visibility: 'private',
      storage: 'local',
      sourceHash: '',
    });
    const second = createOrUpdateLocalProject({ sourceUrl: URL_A });
    expect(second?.created).toBe(false);
    expect(second?.project.id).toBe(first?.project.id);
    expect(readLocalProjects()).toHaveLength(1);
  });

  it('rejects invalid URLs', () => {
    expect(createOrUpdateLocalProject({ sourceUrl: 'https://example.com/x' })).toBeNull();
    expect(readLocalProjects()).toEqual([]);
  });

  it('renames, toggles visibility, and deletes', () => {
    const { project } = createOrUpdateLocalProject({ sourceUrl: URL_A })!;
    expect(updateLocalProject(project.id, { title: 'Renamed', visibility: 'shared' })).toMatchObject({
      title: 'Renamed',
      visibility: 'shared',
    });
    expect(readLocalProjects()[0]).toMatchObject({ title: 'Renamed', visibility: 'shared' });
    expect(updateLocalProject('missing', { title: 'x' })).toBeNull();
    expect(deleteLocalProject(project.id)).toBe(true);
    expect(deleteLocalProject(project.id)).toBe(false);
    expect(readLocalProjects()).toEqual([]);
  });

  it('removes only the listed ids', () => {
    const a = createOrUpdateLocalProject({ sourceUrl: URL_A })!.project;
    const b = createOrUpdateLocalProject({ sourceUrl: URL_B })!.project;
    removeLocalProjectsByIds([a.id]);
    expect(readLocalProjects().map((project) => project.id)).toEqual([b.id]);
  });
});
