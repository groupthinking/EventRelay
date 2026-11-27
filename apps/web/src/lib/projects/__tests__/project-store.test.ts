import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GOLDEN_IDENTITY_HASHES } from '@/lib/video-pack';
import {
  createOrFindProject,
  deleteProject,
  getProject,
  listProjects,
  resolveProjectSource,
  updateProject,
} from '../project-store';

const owner = { subject: 'verified-nextauth-subject' };
const otherOwner = { subject: 'another-verified-subject' };
const projectId = '0b0b55ec-81f8-4cbf-91b3-75f67796b9c1';
const VIDEO_ID = 'auJzb1D-fag';
const SOURCE_URL = `https://www.youtube.com/watch?v=${VIDEO_ID}`;
const SOURCE_HASH = GOLDEN_IDENTITY_HASHES[VIDEO_ID];
const row = {
  id: projectId,
  owner_subject: owner.subject,
  source_hash: SOURCE_HASH,
  source_url: SOURCE_URL,
  title: 'Test Video Pack',
  visibility: 'private',
  created_at: '2026-11-27T00:00:00.000Z',
  updated_at: '2026-11-27T00:00:00.000Z',
};
const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubEnv('SUPABASE_URL', 'https://projects-db.example');
  vi.stubEnv('NEXT_PUBLIC_SUPABASE_URL', 'https://projects-db.example');
  vi.stubEnv('SUPABASE_SECRET_KEY', 'sb_secret_offline-test-only');
  vi.stubEnv('SUPABASE_SERVICE_ROLE_KEY', '');
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

function reply(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });
}
function sent(index = 0) {
  const [input, init] = fetchMock.mock.calls[index];
  return { url: new URL(String(input)), init, headers: new Headers(init?.headers) };
}

describe('resolveProjectSource', () => {
  it('derives the canonical URL and golden Video Pack hash from any YouTube form', () => {
    for (const input of [SOURCE_URL, `https://youtu.be/${VIDEO_ID}`, VIDEO_ID]) {
      expect(resolveProjectSource(input)).toEqual({
        videoId: VIDEO_ID,
        sourceUrl: SOURCE_URL,
        sourceHash: SOURCE_HASH,
      });
    }
    expect(SOURCE_HASH).toMatch(/^[a-f0-9]{64}$/);
  });

  it('rejects non-YouTube input', () => {
    expect(() => resolveProjectSource('https://example.com/watch?v=auJzb1D-fag')).toThrowError(
      expect.objectContaining({ status: 400, code: 'invalid_source_url' }),
    );
  });
});

describe('private project storage', () => {
  it('lists only owned projects, newest first, with an explicit column list', async () => {
    fetchMock.mockResolvedValueOnce(reply([row]));
    const projects = await listProjects(owner);
    expect(projects).toEqual([
      expect.objectContaining({ id: projectId, videoId: VIDEO_ID, storage: 'remote', sourceHash: SOURCE_HASH }),
    ]);
    const { url } = sent();
    expect(url.pathname).toBe('/rest/v1/projects');
    expect(url.searchParams.get('owner_subject')).toBe(`eq.${owner.subject}`);
    expect(url.searchParams.get('order')).toBe('updated_at.desc,id.desc');
    expect(Number(url.searchParams.get('limit'))).toBeLessThanOrEqual(100);
    expect(url.searchParams.get('select')).not.toBe('*');
  });

  it('never exposes owner_subject on returned projects', async () => {
    fetchMock.mockResolvedValueOnce(reply([row]));
    const [project] = await listProjects(owner);
    expect(JSON.stringify(project)).not.toContain('owner_subject');
    expect(JSON.stringify(project)).not.toContain(owner.subject);
  });

  it('filters by visibility server-side and by query in memory', async () => {
    fetchMock.mockResolvedValueOnce(reply([row, { ...row, id: '1b0b55ec-81f8-4cbf-91b3-75f67796b9c1', title: 'Other' }]));
    const projects = await listProjects(owner, { visibility: 'private', query: 'test video' });
    expect(sent().url.searchParams.get('visibility')).toBe('eq.private');
    expect(projects).toHaveLength(1);
    expect(projects[0].title).toBe('Test Video Pack');
  });

  it('gets a project only through the owner-scoped identifier', async () => {
    fetchMock.mockResolvedValueOnce(reply(row));
    await expect(getProject(owner, projectId)).resolves.toMatchObject({ id: projectId });
    expect(sent().url.searchParams.get('owner_subject')).toBe(`eq.${owner.subject}`);
    expect(sent().url.searchParams.get('id')).toBe(`eq.${projectId}`);
  });

  it('returns an indistinguishable 404 for another owner', async () => {
    fetchMock.mockResolvedValueOnce(reply(null));
    await expect(getProject(otherOwner, projectId)).rejects.toMatchObject({ status: 404, code: 'project_not_found' });
    expect(sent().url.searchParams.get('owner_subject')).toBe(`eq.${otherOwner.subject}`);
  });

  it('rejects malformed identifiers before any database query', async () => {
    await expect(getProject(owner, 'not-a-uuid')).rejects.toMatchObject({ status: 400, code: 'invalid_project_id' });
    await expect(updateProject(owner, 'not-a-uuid', { title: 'x' })).rejects.toMatchObject({ status: 400 });
    await expect(deleteProject(owner, 'not-a-uuid')).rejects.toMatchObject({ status: 400 });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('fails closed without a service key and never falls back to browser keys', async () => {
    vi.stubEnv('SUPABASE_SECRET_KEY', '');
    vi.stubEnv('NEXT_PUBLIC_SUPABASE_ANON_KEY', 'public-test-key');
    await expect(listProjects(owner)).rejects.toMatchObject({ status: 503, code: 'projects_unavailable' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('sanitizes database failure details', async () => {
    fetchMock.mockResolvedValueOnce(
      reply({ code: '42501', message: 'private database credential detail', details: '', hint: '' }, 403),
    );
    await expect(listProjects(owner)).rejects.toMatchObject({
      status: 503,
      message: 'Project storage is unavailable.',
    });
  });

  it('rejects unexpected cross-owner rows rather than exposing them', async () => {
    fetchMock.mockResolvedValueOnce(reply([{ ...row, owner_subject: otherOwner.subject }]));
    await expect(listProjects(owner)).rejects.toMatchObject({ status: 503 });
  });

  it('creates a project bound to the canonical source and golden hash', async () => {
    fetchMock.mockResolvedValueOnce(reply(row, 201));
    const result = await createOrFindProject(owner, { sourceUrl: `https://youtu.be/${VIDEO_ID}`, title: 'Test Video Pack' });
    expect(result.created).toBe(true);
    const body = JSON.parse(String(sent().init?.body));
    expect(body).toMatchObject({
      owner_subject: owner.subject,
      source_hash: SOURCE_HASH,
      source_url: SOURCE_URL,
      title: 'Test Video Pack',
      visibility: 'private',
    });
  });

  it('returns the existing project when the (owner, source_hash) constraint conflicts', async () => {
    fetchMock
      .mockResolvedValueOnce(reply({ code: '23505', message: 'duplicate key', details: '', hint: '' }, 409))
      .mockResolvedValueOnce(reply(row));
    const result = await createOrFindProject(owner, { sourceUrl: SOURCE_URL });
    expect(result).toMatchObject({ created: false, project: { id: projectId } });
    const lookup = sent(1).url;
    expect(lookup.searchParams.get('owner_subject')).toBe(`eq.${owner.subject}`);
    expect(lookup.searchParams.get('source_hash')).toBe(`eq.${SOURCE_HASH}`);
  });

  it('rejects invalid sources and extra fields before any database query', async () => {
    await expect(createOrFindProject(owner, { sourceUrl: 'https://example.com/x' })).rejects.toMatchObject({
      status: 400,
      code: 'invalid_source_url',
    });
    await expect(
      createOrFindProject(owner, { sourceUrl: SOURCE_URL, owner_subject: 'spoof' } as never),
    ).rejects.toMatchObject({ status: 400, code: 'invalid_request' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('updates title and visibility scoped to the owner', async () => {
    fetchMock.mockResolvedValueOnce(reply({ ...row, visibility: 'shared' }));
    await expect(updateProject(owner, projectId, { visibility: 'shared' })).resolves.toMatchObject({
      visibility: 'shared',
    });
    expect(sent().url.searchParams.get('owner_subject')).toBe(`eq.${owner.subject}`);
    expect(sent().url.searchParams.get('id')).toBe(`eq.${projectId}`);
    expect(JSON.parse(String(sent().init?.body))).toMatchObject({ visibility: 'shared' });
  });

  it('rejects empty updates and 404s a missing project on update/delete', async () => {
    await expect(updateProject(owner, projectId, {})).rejects.toMatchObject({ status: 400 });
    fetchMock.mockResolvedValueOnce(reply(null)).mockResolvedValueOnce(reply(null));
    await expect(updateProject(owner, projectId, { title: 'x' })).rejects.toMatchObject({ status: 404 });
    await expect(deleteProject(owner, projectId)).rejects.toMatchObject({ status: 404 });
  });

  it('deletes scoped to the owner', async () => {
    fetchMock.mockResolvedValueOnce(reply({ id: projectId }));
    await expect(deleteProject(owner, projectId)).resolves.toBeUndefined();
    expect(sent().init?.method).toBe('DELETE');
    expect(sent().url.searchParams.get('owner_subject')).toBe(`eq.${owner.subject}`);
  });
});
