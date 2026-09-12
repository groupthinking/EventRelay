import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { studioProvider, unwrapStudioResult } from '../provider';

const fetchMock = vi.fn<typeof fetch>();
beforeEach(() => {
  vi.stubEnv('V0_API_KEY', 'v0-offline-test-key');
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

function reply(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });
}

describe('Studio v2 provider boundary', () => {
  it('requires the v0-specific key rather than falling back to Gateway or project identity', () => {
    vi.stubEnv('V0_API_KEY', '');
    vi.stubEnv('AI_GATEWAY_API_KEY', 'not-a-v0-key');
    expect(() => studioProvider()).toThrow(expect.objectContaining({ status: 503, code: 'builder_unavailable' }));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('uses the installed v2 SDK and keeps authentication server-side', async () => {
    fetchMock.mockResolvedValueOnce(reply({ chatId: 'upstream-chat', messageId: 'upstream-message' }, 202));
    const result = await studioProvider().chats.createAsync({ message: 'Build a small app', privacy: 'private', mcpServerIds: [], skills: [] });
    expect(unwrapStudioResult(result)).toEqual({ chatId: 'upstream-chat', messageId: 'upstream-message' });
    const request = fetchMock.mock.calls[0][0] as Request;
    expect(request.url).toBe('https://api.v0.dev/v2/chats/async');
    expect(request.headers.get('authorization')).toBe('Bearer v0-offline-test-key');
    expect(request.cache).toBe('no-store');
  });

  it.each([401, 403, 404, 409, 422, 429, 500, 503])('preserves provider HTTP status %s without leaking provider details', async (status) => {
    fetchMock.mockResolvedValueOnce(reply({ error: { message: 'private-provider-detail' } }, status));
    await expect(studioProvider().chats.get({ chatId: 'upstream-chat' })).rejects.toMatchObject({ status, code: 'builder_request_failed' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('sanitizes network errors without retrying a potentially accepted mutation', async () => {
    fetchMock.mockRejectedValueOnce(new Error('private-network-detail'));
    await expect(studioProvider().chats.createAsync({ message: 'Build' })).rejects.toMatchObject({ status: 502, message: 'The app builder could not be reached. Reload the chat before retrying.' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('fails closed on unexpected result shapes', () => {
    expect(() => unwrapStudioResult({ data: undefined, error: undefined, response: new Response(null, { status: 200 }) }))
      .toThrow(expect.objectContaining({ status: 502 }));
  });

  it('does not automatically follow provider redirects with credentials', async () => {
    fetchMock.mockImplementationOnce(async (input) => {
      expect((input as Request).redirect).toBe('error');
      throw new TypeError('redirect');
    });
    await expect(studioProvider().chats.get({ chatId: 'upstream-chat' })).rejects.toMatchObject({ status: 502 });
  });
});
