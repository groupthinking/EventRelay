import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { readV0Stream, type V0StreamEvent } from 'v0';
import { resumeStudioStream } from '../generation';
import type { StudioChat } from '../chat-store';

const fetchMock = vi.fn<typeof fetch>();
const chat: StudioChat = {
  id: '0b0b55ec-81f8-4cbf-91b3-75f67796b9c1', v0ChatId: 'upstream-chat', title: 'App',
  requestId: 'a77dc8f2-eaca-4ac5-910b-c5cb01234ced', requestHash: 'a'.repeat(64),
  packSourceHash: null, creationState: 'ready', createdAt: '', updatedAt: '',
};
const request = () => new NextRequest('https://uvai.io/api/studio/chats/local/resume', { method: 'POST' });

beforeEach(() => {
  vi.stubEnv('V0_API_KEY', 'offline-test-key');
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

function eventResponse(events: V0StreamEvent[]) {
  return new Response(events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(''), { headers: { 'content-type': 'text/event-stream' } });
}
const titleEvent: V0StreamEvent = { object: 'chat.title', id: 'upstream-chat', delta: 'Counter app' };

describe('real v0 SDK stream handshake', () => {
  it('replays the first update through the SDK instead of losing it during priming', async () => {
    fetchMock.mockResolvedValue(eventResponse([titleEvent]));
    const response = await resumeStudioStream(request(), chat);
    expect(response.status).toBe(200);
    const stream = readV0Stream(response);
    const updates = [];
    for await (const update of stream.stream) updates.push(update);
    expect(updates).toHaveLength(1);
    expect(updates[0].title).toBe('Counter app');
    expect((await stream.final).status).toBe('done');
  });

  it('redacts provider error details that arrive after streaming begins', async () => {
    fetchMock.mockResolvedValue(eventResponse([titleEvent, { object: 'error', id: 'upstream-chat', message: 'private provider credentials', code: 'private-code' }]));
    const response = await resumeStudioStream(request(), chat);
    const wire = await response.text();
    expect(wire).toContain('Counter app');
    expect(wire).toContain('Reconnect');
    expect(wire).not.toMatch(/private provider credentials|private-code/);
  });

  it.each([401, 404, 429, 503])('preserves HTTP %s before committing a successful SSE response', async (status) => {
    fetchMock.mockResolvedValue(new Response('upstream private details', { status }));
    await expect(resumeStudioStream(request(), chat)).rejects.toMatchObject({ status, code: 'builder_request_failed' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does not lose or leak a failed connection inside a nominal HTTP 200 stream', async () => {
    fetchMock.mockRejectedValue(new Error('provider credential details'));
    await expect(resumeStudioStream(request(), chat)).rejects.toMatchObject({ status: 502, code: 'builder_unreachable' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
