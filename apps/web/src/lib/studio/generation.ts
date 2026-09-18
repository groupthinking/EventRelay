import 'server-only';

import type { NextRequest } from 'next/server';
import type { Message, MessagesResolveAsyncData } from 'v0';
import type { StudioChat } from './chat-store';
import { acquireStudioLock, completeStudioRequest, forgetStudioTurn, getStudioTurn, readStudioRequest, releaseStudioLock, rememberStudioTurn, reserveStudioRequest } from './controls';
import { StudioError } from './errors';
import { studioProvider, unwrapStudioResult } from './provider';
import type { StudioOwner } from './security';

export function upstreamChatId(chat: StudioChat): string {
  if (chat.creationState !== 'ready' || !chat.v0ChatId) throw new StudioError(409, 'chat_not_ready', 'This chat is not ready. Reload before retrying.');
  return chat.v0ChatId;
}
const busy = () => new StudioError(409, 'chat_busy', 'A generation is active or its outcome is unknown. Reconnect to this chat before sending another request.');

export async function currentStudioMessage(owner: StudioOwner, chat: StudioChat): Promise<Message | null> {
  const chatId = upstreamChatId(chat);
  const provider = studioProvider();
  const [history, turn] = await Promise.all([
    provider.messages.list({ chatId, limit: 2 }).then(unwrapStudioResult),
    getStudioTurn(owner, chat.id),
  ]);
  let message = history.messages[0] ?? null;
  if (message && (message.chatId !== chatId || message.role !== 'assistant')) throw busy();
  if (turn?.messageId) {
    const accepted = unwrapStudioResult(await provider.messages.get({ chatId, messageId: turn.messageId }));
    if (accepted.id !== turn.messageId || accepted.chatId !== chatId || accepted.role !== 'assistant') throw busy();
    if (!accepted.finishReason || !message || message.id === turn.previousMessageId || message.id === accepted.id) message = accepted;
  } else if (turn && (!message || message.id === turn.previousMessageId)) {
    throw busy();
  }
  if (turn && message?.finishReason) await forgetStudioTurn(owner, chat.id, turn.requestId);
  return message;
}

export async function resumeStudioStream(request: NextRequest, chat: StudioChat): Promise<Response> {
  const stream = await studioProvider({ streaming: true }).chats.resume({ chatId: upstreamChatId(chat) }, {
    signal: request.signal,
    sseMaxRetryAttempts: 1,
    onSseEvent({ data }) {
      if (data === undefined) return;
      const kind = typeof data === 'object' && data !== null && 'object' in data ? data.object : null;
      if (typeof kind !== 'string' || !['chat', 'chat.title', 'message', 'message.parts.chunk', 'message.usage'].includes(kind)) {
        throw new StudioError(502, 'builder_stream_failed', 'The builder stream disconnected. Reconnect to this chat.');
      }
    },
    onSseError(error) {
      if (error instanceof StudioError) throw error;
      throw new StudioError(502, 'builder_stream_failed', 'The builder stream disconnected. Reconnect to this chat.');
    },
  });
  // SDK streams connect lazily. Prime its replayable subscription before committing HTTP 200.
  const subscription = stream.stream[Symbol.asyncIterator]();
  try { await subscription.next(); }
  catch (error) {
    if (error instanceof StudioError) throw error;
    throw new StudioError(502, 'builder_stream_failed', 'The builder stream could not start. Reconnect to this chat.');
  } finally { await subscription.return?.(); }
  return stream.toResponse();
}

type NextTurn = { message: string } | { task: MessagesResolveAsyncData['body']['task'] };
export async function advanceStudioChat(
  request: NextRequest,
  owner: StudioOwner,
  chat: StudioChat,
  requestId: string,
  hash: string,
  prepare: (message: Message) => NextTurn,
): Promise<Response> {
  const lock = await acquireStudioLock(owner, chat.id);
  try {
    const receipt = await readStudioRequest(owner, chat.id, requestId, hash);
    if (!receipt) {
      const current = await currentStudioMessage(owner, chat);
      if (!current || !current.finishReason) throw busy();
      const next = prepare(current);
      const replay = await reserveStudioRequest(owner, chat.id, requestId, hash);
      if (!replay) {
        await rememberStudioTurn(owner, chat.id, { requestId, previousMessageId: current.id, messageId: null }, lock);
        const provider = studioProvider();
        const chatId = upstreamChatId(chat);
        const accepted = unwrapStudioResult('message' in next
          ? await provider.messages.sendAsync({ chatId, message: next.message })
          : await provider.messages.resolveAsync({ chatId, task: next.task }));
        await rememberStudioTurn(owner, chat.id, { requestId, previousMessageId: current.id, messageId: accepted.messageId }, lock);
        await completeStudioRequest(owner, chat.id, requestId, hash, accepted.messageId);
      }
    }
  } finally {
    await releaseStudioLock(lock);
  }
  return resumeStudioStream(request, chat);
}
