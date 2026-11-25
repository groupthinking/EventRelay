import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { StudioError } from '../errors';

const boundary = vi.hoisted(() => ({
  owner: vi.fn(), list: vi.fn(), get: vi.fn(), reserve: vi.fn(), bind: vi.fn(), fail: vi.fn(),
  rate: vi.fn(), acquire: vi.fn(), release: vi.fn(), request: vi.fn(), receipt: vi.fn(), complete: vi.fn(),
  turn: vi.fn(), remember: vi.fn(), forget: vi.fn(), pack: vi.fn(),
  create: vi.fn(), remove: vi.fn(), messages: vi.fn(), message: vi.fn(), send: vi.fn(), resume: vi.fn(), stop: vi.fn(), resolve: vi.fn(), files: vi.fn(), download: vi.fn(),
}));
vi.mock('../security', async (original) => ({ ...await original<object>(), requireStudioOwner: boundary.owner }));
vi.mock('../chat-store', () => ({ listStudioChats: boundary.list, getStudioChat: boundary.get, reserveStudioChat: boundary.reserve, bindStudioChat: boundary.bind, failStudioChat: boundary.fail }));
vi.mock('../controls', () => ({ checkStudioRate: boundary.rate, acquireStudioLock: boundary.acquire, releaseStudioLock: boundary.release, reserveStudioRequest: boundary.request, readStudioRequest: boundary.receipt, completeStudioRequest: boundary.complete, getStudioTurn: boundary.turn, rememberStudioTurn: boundary.remember, forgetStudioTurn: boundary.forget }));
vi.mock('../pack-context', () => ({ loadStudioPackContext: boundary.pack }));
vi.mock('../provider', async (original) => ({
  ...await original<object>(),
  studioProvider: () => ({
    chats: { createAsync: boundary.create, delete: boundary.remove, resume: boundary.resume, getFiles: boundary.files, downloadFiles: boundary.download },
    messages: { list: boundary.messages, get: boundary.message, sendAsync: boundary.send, stop: boundary.stop, resolveAsync: boundary.resolve },
  }),
}));

const owner = { subject: 'verified-owner' };
const id = '0b0b55ec-81f8-4cbf-91b3-75f67796b9c1';
const requestId = 'a77dc8f2-eaca-4ac5-910b-c5cb01234ced';
const chat = { id, v0ChatId: 'upstream-chat', title: 'My app', requestId, requestHash: 'a'.repeat(64), packSourceHash: null, creationState: 'ready', createdAt: '2026-09-12T00:00:00Z', updatedAt: '2026-09-12T00:00:00Z' };
const finished = { id: 'old-message', chatId: 'upstream-chat', role: 'assistant', content: 'Done', parts: [], finishReason: 'stop' };
function result(data: unknown, status = 200) { return { data, response: new Response(null, { status }) }; }
function request(method = 'GET', body?: unknown, suffix = '') {
  return new NextRequest(`https://uvai.io/api/studio/chats/${id}${suffix}`, { method, headers: { origin: 'https://uvai.io', 'content-type': 'application/json' }, ...(body === undefined || method === 'GET' || method === 'HEAD' ? {} : { body: JSON.stringify(body) }) });
}
type Handler = (request: NextRequest, context: { params: Promise<{ chatId: string }> }) => Promise<Response>;
let routes: Record<string, Handler>;
beforeAll(async () => { routes = await import('../routes').catch(() => ({})) as Record<string, Handler>; });
async function call(name: string, req = request()) {
  expect(routes[name], `Studio must expose ${name}`).toBeTypeOf('function');
  return routes[name](req, { params: Promise.resolve({ chatId: id }) });
}
beforeEach(() => {
  vi.clearAllMocks();
  boundary.owner.mockResolvedValue(owner);
  boundary.list.mockResolvedValue([chat]); boundary.get.mockResolvedValue(chat);
  boundary.reserve.mockResolvedValue({ chat: { ...chat, v0ChatId: null, creationState: 'reserved' }, isNew: true });
  boundary.bind.mockResolvedValue(chat); boundary.fail.mockResolvedValue(undefined);
  boundary.rate.mockResolvedValue(undefined); boundary.acquire.mockResolvedValue({ key: 'lock', token: 'token' }); boundary.release.mockResolvedValue(undefined);
  boundary.request.mockResolvedValue(null); boundary.receipt.mockResolvedValue(null); boundary.complete.mockResolvedValue(undefined);
  boundary.turn.mockResolvedValue(null); boundary.remember.mockResolvedValue(undefined); boundary.forget.mockResolvedValue(undefined);
  boundary.pack.mockResolvedValue(null);
  boundary.create.mockResolvedValue(result({ chatId: 'upstream-chat', messageId: 'new-message' }, 202));
  boundary.remove.mockResolvedValue(result({}, 200));
  boundary.messages.mockResolvedValue(result({ messages: [finished], cursor: null }));
  boundary.message.mockResolvedValue(result(finished));
  boundary.send.mockResolvedValue(result({ messageId: 'new-message' }, 202));
  boundary.resolve.mockResolvedValue(result({ messageId: 'new-message' }, 202));
  boundary.resume.mockImplementation(async () => ({ stream: { async *[Symbol.asyncIterator]() { yield {}; } }, toResponse: () => new Response('data: test-fixture\n\n', { headers: { 'content-type': 'text/event-stream' } }) }));
  boundary.stop.mockResolvedValue(result({ messageId: 'old-message', stopped: true }));
  boundary.files.mockResolvedValue(result({ files: [{ path: 'app/page.tsx', content: '<main />', encoding: 'utf8' }] }));
  boundary.download.mockResolvedValue(result(new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array([80, 75])); controller.close(); } })));
});

describe('authenticated Studio routes', () => {
  it.each(['listChats', 'createChat', 'loadChat', 'listMessages', 'sendMessage', 'resumeChat', 'stopMessage', 'resolveMessage', 'readFiles', 'downloadFiles'])('requires verified authentication for %s', async (name) => {
    boundary.owner.mockRejectedValue(new StudioError(401, 'authentication_required', 'Sign in.'));
    const response = await call(name, request(name.match(/create|send|resume|stop|resolve/) ? 'POST' : 'GET', { requestId, message: 'Build' }));
    expect(response.status).toBe(401);
    expect(boundary.get).not.toHaveBeenCalled(); expect(boundary.create).not.toHaveBeenCalled();
  });
  it.each(['loadChat', 'listMessages', 'sendMessage', 'resumeChat', 'stopMessage', 'resolveMessage', 'readFiles', 'downloadFiles'])('enforces owner access before %s reaches v0', async (name) => {
    boundary.get.mockRejectedValue(new StudioError(404, 'chat_not_found', 'Not found.'));
    const response = await call(name, request(name.match(/send|resume|stop|resolve/) ? 'POST' : 'GET', { requestId, message: 'Build', messageId: 'old-message' }));
    expect(response.status).toBe(404); expect(boundary.get).toHaveBeenCalledWith(owner, id);
    for (const fn of [boundary.messages, boundary.send, boundary.resume, boundary.stop, boundary.resolve, boundary.files, boundary.download]) expect(fn).not.toHaveBeenCalled();
  });
  it.each(['createChat', 'sendMessage', 'resumeChat', 'stopMessage', 'resolveMessage'])('requires independent CSRF origin protection on %s', async (name) => {
    const req = request('POST', { requestId, message: 'Build' }); req.headers.set('origin', 'https://attacker.example');
    expect((await call(name, req)).status).toBe(403); expect(boundary.create).not.toHaveBeenCalled(); expect(boundary.send).not.toHaveBeenCalled();
  });
  it('returns only owned public chat summaries with private non-cacheable responses', async () => {
    const response = await call('listChats');
    expect(response.status).toBe(200); expect(response.headers.get('cache-control')).toContain('no-store');
    const body = await response.json(); expect(body.chats[0]).toMatchObject({ id, title: 'My app' });
    expect(JSON.stringify(body)).not.toMatch(/requestHash|requestId|owner_subject|verified-owner/);
  });
  it('binds durable ownership before returning a newly accepted app', async () => {
    const response = await call('createChat', request('POST', { requestId, message: 'Build a counter' }));
    expect(response.status).toBe(201);
    expect(boundary.reserve.mock.invocationCallOrder[0]).toBeLessThan(boundary.create.mock.invocationCallOrder[0]);
    expect(boundary.create.mock.invocationCallOrder[0]).toBeLessThan(boundary.bind.mock.invocationCallOrder[0]);
    expect(boundary.create).toHaveBeenCalledWith(expect.objectContaining({ message: 'Build a counter', privacy: 'private', mcpServerIds: [], skills: [] }));
    expect(boundary.create.mock.calls[0][0]).not.toHaveProperty('environmentVariables');
    expect(boundary.create.mock.calls[0][0].systemPrompt).toMatch(/G\.A\.T\.E\./);
    expect((await response.json()).chat.id).toBe(id);
  });
  it('reuses a completed create receipt instead of creating a second upstream chat', async () => {
    boundary.reserve.mockResolvedValue({ chat, isNew: false });
    expect((await call('createChat', request('POST', { requestId, message: 'Build' }))).status).toBe(200);
    expect(boundary.create).not.toHaveBeenCalled();
  });
  it.each(['reserved', 'failed'])('does not repeat a create with %s outcome', async (creationState) => {
    boundary.reserve.mockResolvedValue({ chat: { ...chat, creationState, v0ChatId: null }, isNew: false });
    expect((await call('createChat', request('POST', { requestId, message: 'Build' }))).status).toBe(409);
    expect(boundary.create).not.toHaveBeenCalled();
  });
  it('does not incur generation when durable reservation fails', async () => {
    boundary.reserve.mockRejectedValue(new StudioError(503, 'ownership_unavailable', 'Unavailable.'));
    expect((await call('createChat', request('POST', { requestId, message: 'Build' }))).status).toBe(503); expect(boundary.create).not.toHaveBeenCalled();
  });
  it('cleans up a confirmed unbound orphan without exposing its identifier', async () => {
    boundary.bind.mockRejectedValue(new StudioError(503, 'ownership_unavailable', 'Unavailable.'));
    boundary.get.mockRejectedValue(new StudioError(404, 'chat_not_found', 'Not found.'));
    const response = await call('createChat', request('POST', { requestId, message: 'Build' }));
    expect(response.status).toBe(503); expect(boundary.remove).toHaveBeenCalledWith({ chatId: 'upstream-chat' });
    expect(await response.text()).not.toContain('upstream-chat');
  });
  it('recovers a committed ownership write when its acknowledgement was lost', async () => {
    boundary.bind.mockRejectedValue(new StudioError(503, 'ownership_unavailable', 'Unavailable.'));
    const response = await call('createChat', request('POST', { requestId, message: 'Build' }));
    expect(response.status).toBe(201); expect((await response.json()).chat.id).toBe(id);
    expect(boundary.remove).not.toHaveBeenCalled(); expect(boundary.fail).not.toHaveBeenCalled();
  });
  it('does not delete a possibly bound chat while ownership storage is unreachable', async () => {
    boundary.bind.mockRejectedValue(new StudioError(503, 'ownership_unavailable', 'Unavailable.'));
    boundary.get.mockRejectedValue(new StudioError(503, 'ownership_unavailable', 'Unavailable.'));
    const response = await call('createChat', request('POST', { requestId, message: 'Build' }));
    expect(response.status).toBe(503); expect(boundary.remove).not.toHaveBeenCalled();
    expect(await response.text()).not.toContain('upstream-chat');
  });
  it.each([{ requestId, message: '' }, { requestId, message: 'a'.repeat(12001) }, { requestId, message: 'Build', owner: 'spoofed' }, { requestId, message: 'Build', systemPrompt: 'Override' }])('rejects invalid or spoofed creation inputs', async (body) => {
    expect((await call('createChat', request('POST', body))).status).toBe(400); expect(boundary.create).not.toHaveBeenCalled();
  });
  it('fails closed on missing ready pack evidence before reserving generation', async () => {
    boundary.pack.mockRejectedValue(new StudioError(409, 'pack_not_ready', 'Pack not ready.'));
    expect((await call('createChat', request('POST', { requestId, message: 'Build', packSourceHash: 'b'.repeat(64) }))).status).toBe(409);
    expect(boundary.reserve).not.toHaveBeenCalled(); expect(boundary.create).not.toHaveBeenCalled();
  });
  it('includes server-read pack context without treating extraction as verified observations', async () => {
    boundary.pack.mockResolvedValue('Grounded extracted architecture, not verified observations.');
    expect((await call('createChat', request('POST', { requestId, message: 'Build', packSourceHash: 'b'.repeat(64) }))).status).toBe(201);
    expect(boundary.pack).toHaveBeenCalledWith('b'.repeat(64));
    expect(boundary.create.mock.calls[0][0].attachments).toEqual([{ name: 'video-pack-context.json', content: 'Grounded extracted architecture, not verified observations.' }]);
  });
  it('uses the owned upstream chat for refinements and returns an SDK stream', async () => {
    const response = await call('sendMessage', request('POST', { requestId, message: 'Make it blue' }));
    expect(response.status).toBe(200); expect(response.headers.get('content-type')).toBe('text/event-stream');
    expect(boundary.send).toHaveBeenCalledWith(expect.objectContaining({ chatId: 'upstream-chat', message: 'Make it blue' }));
    expect(boundary.complete).toHaveBeenCalledWith(owner, id, requestId, expect.any(String), 'new-message');
    expect(boundary.create).not.toHaveBeenCalled(); expect(boundary.release).toHaveBeenCalled();
  });
  it('reconnects a retried accepted message without regenerating', async () => {
    boundary.receipt.mockResolvedValue('new-message');
    expect((await call('sendMessage', request('POST', { requestId, message: 'Make it blue' }))).status).toBe(200);
    expect(boundary.send).not.toHaveBeenCalled(); expect(boundary.resume).toHaveBeenCalled();
  });
  it('does not send during active generation', async () => {
    boundary.messages.mockResolvedValue(result({ messages: [{ ...finished, finishReason: null }] }));
    expect((await call('sendMessage', request('POST', { requestId, message: 'Build' }))).status).toBe(409);
    expect(boundary.send).not.toHaveBeenCalled(); expect(boundary.request).not.toHaveBeenCalled();
  });
  it('holds when an earlier upstream send outcome is unknown and history has not advanced', async () => {
    boundary.turn.mockResolvedValue({ requestId, previousMessageId: finished.id, messageId: null });
    expect((await call('sendMessage', request('POST', { requestId, message: 'Build' }))).status).toBe(409); expect(boundary.send).not.toHaveBeenCalled();
  });
  it('checks the accepted message directly when the history endpoint lags', async () => {
    boundary.turn.mockResolvedValue({ requestId, previousMessageId: finished.id, messageId: 'new-message' });
    boundary.message.mockResolvedValue(result({ ...finished, id: 'new-message', finishReason: null }));
    expect((await call('sendMessage', request('POST', { requestId, message: 'Build' }))).status).toBe(409); expect(boundary.send).not.toHaveBeenCalled();
  });
  it('releases a mutation lock while preserving an unknown send receipt after provider failure', async () => {
    boundary.send.mockRejectedValue(new StudioError(502, 'builder_unreachable', 'Reload.'));
    expect((await call('sendMessage', request('POST', { requestId, message: 'Build' }))).status).toBe(502);
    expect(boundary.remember).toHaveBeenCalledWith(owner, id, { requestId, previousMessageId: finished.id, messageId: null }, { key: 'lock', token: 'token' });
    expect(boundary.complete).not.toHaveBeenCalled(); expect(boundary.release).toHaveBeenCalled();
  });
  it('rejects simultaneous send before it reaches the provider', async () => {
    boundary.acquire.mockRejectedValue(new StudioError(409, 'chat_busy', 'Busy.'));
    expect((await call('sendMessage', request('POST', { requestId, message: 'Build' }))).status).toBe(409); expect(boundary.send).not.toHaveBeenCalled();
  });
  it('resumes without starting another generation', async () => {
    expect((await call('resumeChat', request('POST'))).status).toBe(200);
    expect(boundary.resume).toHaveBeenCalledWith({ chatId: 'upstream-chat' }, expect.objectContaining({ signal: expect.any(AbortSignal), sseMaxRetryAttempts: 1 }));
    expect(boundary.send).not.toHaveBeenCalled();
  });
  it('cancels only the owned active assistant message', async () => {
    boundary.messages.mockResolvedValue(result({ messages: [{ ...finished, finishReason: null }] }));
    const response = await call('stopMessage', request('POST', { messageId: finished.id }));
    expect(response.status).toBe(200); expect(boundary.stop).toHaveBeenCalledWith({ chatId: 'upstream-chat', messageId: finished.id });
  });
  it('rejects a stale or foreign message identifier on cancellation', async () => {
    expect((await call('stopMessage', request('POST', { messageId: 'foreign-message' }))).status).toBe(409); expect(boundary.stop).not.toHaveBeenCalled();
  });
  it('preserves useful status codes without leaking unexpected exception details', async () => {
    boundary.files.mockRejectedValue(new Error('private token and connection details'));
    const response = await call('readFiles'); expect(response.status).toBe(500); expect(await response.text()).not.toMatch(/private token|connection details/);
  });
  it('returns real generated files and an attachment-only ZIP response', async () => {
    const response = await call('readFiles'); expect((await response.json()).files[0].path).toBe('app/page.tsx');
    const download = await call('downloadFiles'); expect(download.headers.get('content-type')).toBe('application/zip'); expect(download.headers.get('content-disposition')).toContain('attachment;');
    expect([...new Uint8Array(await download.arrayBuffer())]).toEqual([80, 75]);
  });
  it('bounds pagination input instead of forwarding arbitrary provider fields', async () => {
    expect((await call('listMessages', request('GET', undefined, '/messages?limit=10000'))).status).toBe(400); expect(boundary.messages).not.toHaveBeenCalled();
  });
  it('resolves only an actual pending question with user-selected answers', async () => {
    boundary.messages.mockResolvedValue(result({ messages: [{ ...finished, finishReason: 'tool-calls', parts: [{ type: 'agent-action', name: 'ask_user_questions', summary: 'Choose', data: { questions: [{ id: 'q1', question: 'Color?', header: 'Color', multiSelect: false, options: [{ id: 'a', label: 'Blue' }] }] } }] }] }));
    const response = await call('resolveMessage', request('POST', { requestId, messageId: finished.id, task: { type: 'answered-questions', answers: [{ questionId: 'q1', selectedLabels: ['Blue'] }] } }));
    expect(response.status).toBe(200); expect(boundary.resolve).toHaveBeenCalledWith(expect.objectContaining({ chatId: 'upstream-chat', task: expect.objectContaining({ type: 'answered-questions' }) }));
  });
  it('rejects invented interaction answers', async () => {
    expect((await call('resolveMessage', request('POST', { requestId, messageId: finished.id, task: { type: 'answered-questions', answers: [{ questionId: 'invented', selectedLabels: ['Yes'] }] } }))).status).toBe(409); expect(boundary.resolve).not.toHaveBeenCalled();
  });
  it('does not accept free-form continuation while an action is pending', async () => {
    boundary.messages.mockResolvedValue(result({ messages: [{ ...finished, finishReason: 'tool-calls' }] }));
    expect((await call('sendMessage', request('POST', { requestId, message: 'Continue' }))).status).toBe(409); expect(boundary.send).not.toHaveBeenCalled();
  });
  it('derives question text from the pending message and rejects unoffered labels', async () => {
    boundary.messages.mockResolvedValue(result({ messages: [{ ...finished, finishReason: 'tool-calls', parts: [{ type: 'agent-action', name: 'ask_user_questions', summary: 'Choose', data: { questions: [{ id: 'q1', question: 'Color?', header: 'Color', multiSelect: false, options: [{ id: 'a', label: 'Blue' }] }] } }] }] }));
    const body = { requestId, messageId: finished.id, task: { type: 'answered-questions', answers: [{ questionId: 'q1', selectedLabels: ['Red'] }] } };
    expect((await call('resolveMessage', request('POST', body))).status).toBe(400); expect(boundary.resolve).not.toHaveBeenCalled();
    body.task.answers[0].selectedLabels = ['Blue'];
    expect((await call('resolveMessage', request('POST', body))).status).toBe(200);
    expect(boundary.resolve.mock.calls[0][0].task.answers[0].questionText).toBe('Color?');
  });
  it('only accepts a plan response for the current pending plan', async () => {
    boundary.messages.mockResolvedValue(result({ messages: [{ ...finished, finishReason: 'tool-calls', parts: [{ type: 'agent-action', name: 'exit_plan_mode', summary: 'Review', data: { plan: 'Build a counter', path: 'plan.md' } }] }] }));
    expect((await call('resolveMessage', request('POST', { requestId, messageId: finished.id, task: { type: 'plan-exit-response', status: 'request-changes', content: 'Add a reset button' } }))).status).toBe(200);
    expect(boundary.resolve.mock.calls[0][0].task.status).toBe('request-changes');
  });
  it('lets the user explicitly skip integration setup without claiming a connection', async () => {
    boundary.messages.mockResolvedValue(result({ messages: [{ ...finished, finishReason: 'tool-calls', parts: [{ type: 'agent-action', name: 'get_or_request_integration', summary: 'Connect', data: { requestedIntegrations: ['Neon'], requestedNpmRegistryIds: [], requestedMcpPresets: [] } }] }] }));
    expect((await call('resolveMessage', request('POST', { requestId, messageId: finished.id, task: { type: 'skip-integration' } }))).status).toBe(200);
    expect(boundary.resolve.mock.calls[0][0].task).toEqual({ type: 'confirmed-steps', connectedIntegrationNames: [], connectedNpmRegistryIds: [], connectedMcpPresetNames: [] });
  });
  it('rejects browser claims that production integrations were connected', async () => {
    expect((await call('resolveMessage', request('POST', { requestId, messageId: finished.id, task: { type: 'confirmed-steps', connectedIntegrationNames: ['Neon'] } }))).status).toBe(400);
    expect(boundary.resolve).not.toHaveBeenCalled();
  });
  it('never turns an unchecked integration or deployment permission into approval', async () => {
    expect((await call('resolveMessage', request('POST', { requestId, messageId: finished.id, task: { type: 'confirmed-permissions', permissions: [{ type: 'ALLOW_DYNAMIC_TOOL_STRICT', toolName: 'deploy', input: {} }] } }))).status).toBe(400); expect(boundary.resolve).not.toHaveBeenCalled();
  });
});
