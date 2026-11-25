import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { bindStudioChat, failStudioChat, getStudioChat, listStudioChats, reserveStudioChat } from '../chat-store';

const owner = { subject: 'verified-nextauth-subject' };
const otherOwner = { subject: 'another-verified-subject' };
const chatId = '0b0b55ec-81f8-4cbf-91b3-75f67796b9c1';
const requestId = 'a77dc8f2-eaca-4ac5-910b-c5cb01234ced';
const requestHash = 'a'.repeat(64);
const reservation = { requestId, requestHash, title: 'A small app', packSourceHash: null };
const row = {
  id: chatId, owner_subject: owner.subject, request_id: requestId, request_hash: requestHash,
  v0_chat_id: null, title: 'A small app', pack_source_hash: null, creation_state: 'reserved',
  created_at: '2026-09-12T00:00:00.000Z', updated_at: '2026-09-12T00:00:00.000Z',
};
const readyRow = { ...row, creation_state: 'ready', v0_chat_id: 'v0-test-chat' };
const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubEnv('SUPABASE_URL', 'https://studio-db.example');
  vi.stubEnv('NEXT_PUBLIC_SUPABASE_URL', 'https://studio-db.example');
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
function expectScoped(index = 0, subject = owner.subject) {
  const { url } = sent(index);
  expect(url.pathname).toBe('/rest/v1/studio_chats');
  expect(url.searchParams.get('owner_subject')).toBe(`eq.${subject}`);
}

describe('private Studio chat ownership storage', () => {
  it('lists only ready owned chats in stable newest-first order', async () => {
    fetchMock.mockResolvedValueOnce(reply([readyRow]));
    const chats = await listStudioChats(owner);
    expect(chats).toEqual([expect.objectContaining({ id: chatId, v0ChatId: 'v0-test-chat' })]);
    expectScoped();
    expect(sent().url.searchParams.get('creation_state')).toBe('eq.ready');
    expect(sent().url.searchParams.get('order')).toBe('created_at.desc,id.desc');
    expect(Number(sent().url.searchParams.get('limit'))).toBeLessThanOrEqual(50);
    expect(sent().url.searchParams.get('select')).not.toBe('*');
  });

  it('gets a chat only through the owner-scoped local identifier', async () => {
    fetchMock.mockResolvedValueOnce(reply(readyRow));
    await expect(getStudioChat(owner, chatId)).resolves.toMatchObject({ id: chatId });
    expectScoped();
    expect(sent().url.searchParams.get('id')).toBe(`eq.${chatId}`);
    expect(sent().url.searchParams.get('creation_state')).toBe('eq.ready');
  });

  it('returns indistinguishable not-found errors for another owner', async () => {
    fetchMock.mockResolvedValueOnce(reply(null));
    await expect(getStudioChat(otherOwner, chatId)).rejects.toMatchObject({ status: 404, code: 'chat_not_found' });
    expectScoped(0, otherOwner.subject);
  });

  it('rejects malformed IDs before making a database query', async () => {
    await expect(getStudioChat(owner, 'arbitrary-upstream-id')).rejects.toMatchObject({ status: 400 });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('fails closed when database credentials are unavailable', async () => {
    vi.stubEnv('SUPABASE_SECRET_KEY', '');
    await expect(listStudioChats(owner)).rejects.toMatchObject({ status: 503, code: 'ownership_unavailable' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('does not fall back to browser keys for ownership access', async () => {
    vi.stubEnv('SUPABASE_SECRET_KEY', '');
    vi.stubEnv('NEXT_PUBLIC_SUPABASE_ANON_KEY', 'public-test-key');
    await expect(listStudioChats(owner)).rejects.toMatchObject({ status: 503 });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('sanitizes database failure details', async () => {
    fetchMock.mockResolvedValueOnce(reply({ code: '42501', message: 'private database credential detail', details: '', hint: '' }, 403));
    await expect(listStudioChats(owner)).rejects.toMatchObject({ status: 503, message: 'Studio ownership storage is unavailable.' });
  });

  it('rejects unexpected rows rather than exposing another owner', async () => {
    fetchMock.mockResolvedValueOnce(reply([{ ...readyRow, owner_subject: otherOwner.subject }]));
    await expect(listStudioChats(owner)).rejects.toMatchObject({ status: 503 });
  });

  it('fails closed on malformed provider row shapes', async () => {
    fetchMock.mockResolvedValueOnce(reply([{ id: chatId }]));
    await expect(listStudioChats(owner)).rejects.toMatchObject({ status: 503 });
  });
});

describe('Studio create retry reservation', () => {
  it('reserves an owner-bound request before any upstream chat can be exposed', async () => {
    fetchMock.mockResolvedValueOnce(reply(row, 201));
    await expect(reserveStudioChat(owner, reservation)).resolves.toMatchObject({ isNew: true, chat: { id: chatId, creationState: 'reserved' } });
    expect(sent().init?.method).toBe('POST');
    expect(JSON.parse(String(sent().init?.body))).toEqual({
      owner_subject: owner.subject, request_id: requestId, request_hash: requestHash,
      title: reservation.title, pack_source_hash: null,
    });
  });

  it.each([
    { ...row, request_id: '5a9ea1c7-8047-43de-970a-215f17a3bdce' },
    { ...row, request_hash: 'b'.repeat(64) },
    readyRow,
  ])('rejects an insert receipt that does not match the reservation: %j', async (receipt) => {
    fetchMock.mockResolvedValueOnce(reply(receipt, 201));
    await expect(reserveStudioChat(owner, reservation)).rejects.toMatchObject({ status: 503 });
  });

  it('reuses a matching completed reservation without creating another app', async () => {
    fetchMock.mockResolvedValueOnce(reply({ code: '23505', message: 'duplicate', details: '', hint: '' }, 409))
      .mockResolvedValueOnce(reply(readyRow));
    await expect(reserveStudioChat(owner, reservation)).resolves.toMatchObject({ isNew: false, chat: { v0ChatId: 'v0-test-chat' } });
    expectScoped(1);
    expect(sent(1).url.searchParams.get('request_id')).toBe(`eq.${requestId}`);
  });

  it('does not re-run a reservation whose creation outcome is still unknown', async () => {
    fetchMock.mockResolvedValueOnce(reply({ code: '23505', message: 'duplicate', details: '', hint: '' }, 409))
      .mockResolvedValueOnce(reply(row));
    await expect(reserveStudioChat(owner, reservation)).resolves.toMatchObject({ isNew: false, chat: { creationState: 'reserved' } });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('rejects reuse of a request ID with different content', async () => {
    fetchMock.mockResolvedValueOnce(reply({ code: '23505', message: 'duplicate', details: '', hint: '' }, 409))
      .mockResolvedValueOnce(reply({ ...row, request_hash: 'b'.repeat(64) }));
    await expect(reserveStudioChat(owner, reservation)).rejects.toMatchObject({ status: 409, code: 'request_conflict' });
  });

  it('does not let a failed reservation silently launch a duplicate app', async () => {
    fetchMock.mockResolvedValueOnce(reply({ code: '23505', message: 'duplicate', details: '', hint: '' }, 409))
      .mockResolvedValueOnce(reply({ ...row, creation_state: 'failed' }));
    await expect(reserveStudioChat(owner, reservation)).resolves.toMatchObject({ isNew: false, chat: { creationState: 'failed' } });
  });

  it('does not substitute in-memory ownership after a failed insert', async () => {
    fetchMock.mockResolvedValueOnce(reply({ code: '08006', message: 'unavailable', details: '', hint: '' }, 500));
    await expect(reserveStudioChat(owner, reservation)).rejects.toMatchObject({ status: 503 });
  });

  it.each([
    { ...reservation, requestId: 'invalid' },
    { ...reservation, requestHash: 'not-a-hash' },
    { ...reservation, title: '' },
    { ...reservation, title: 'x'.repeat(161) },
    { ...reservation, packSourceHash: '' },
  ])('validates reservation input before insertion: %j', async (input) => {
    await expect(reserveStudioChat(owner, input)).rejects.toMatchObject({ status: 400 });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('conditional Studio ownership transitions', () => {
  it('binds the upstream ID only to an owned reserved row', async () => {
    fetchMock.mockResolvedValueOnce(reply(readyRow));
    await expect(bindStudioChat(owner, chatId, 'v0-test-chat')).resolves.toMatchObject({ v0ChatId: 'v0-test-chat', creationState: 'ready' });
    expectScoped();
    expect(sent().url.searchParams.get('id')).toBe(`eq.${chatId}`);
    expect(sent().url.searchParams.get('creation_state')).toBe('eq.reserved');
    expect(JSON.parse(String(sent().init?.body))).toMatchObject({ v0_chat_id: 'v0-test-chat', creation_state: 'ready' });
  });

  it('rejects a lost binding race instead of exposing an orphan chat', async () => {
    fetchMock.mockResolvedValueOnce(reply(null));
    await expect(bindStudioChat(owner, chatId, 'v0-test-chat')).rejects.toMatchObject({ status: 409, code: 'creation_conflict' });
  });

  it('cannot mark an existing ready chat failed', async () => {
    fetchMock.mockResolvedValueOnce(reply(null));
    await expect(failStudioChat(owner, chatId)).resolves.toBeUndefined();
    expectScoped();
    expect(sent().url.searchParams.get('creation_state')).toBe('eq.reserved');
    expect(JSON.parse(String(sent().init?.body))).toMatchObject({ creation_state: 'failed' });
  });

  it('sanitizes a failed ownership binding', async () => {
    fetchMock.mockResolvedValueOnce(reply({ code: '23505', message: 'private upstream id', details: '', hint: '' }, 409));
    await expect(bindStudioChat(owner, chatId, 'v0-test-chat')).rejects.toMatchObject({ status: 503 });
  });
});
