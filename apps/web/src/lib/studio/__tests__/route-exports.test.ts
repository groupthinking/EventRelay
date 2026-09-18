import { describe, expect, it } from 'vitest';
import * as handlers from '../routes';

const endpoints = [
  [() => import('@/app/api/studio/chats/route'), { GET: handlers.listChats, POST: handlers.createChat }],
  [() => import('@/app/api/studio/chats/[chatId]/route'), { GET: handlers.loadChat }],
  [() => import('@/app/api/studio/chats/[chatId]/messages/route'), { GET: handlers.listMessages, POST: handlers.sendMessage }],
  [() => import('@/app/api/studio/chats/[chatId]/resume/route'), { POST: handlers.resumeChat }],
  [() => import('@/app/api/studio/chats/[chatId]/stop/route'), { POST: handlers.stopMessage }],
  [() => import('@/app/api/studio/chats/[chatId]/resolve/route'), { POST: handlers.resolveMessage }],
  [() => import('@/app/api/studio/chats/[chatId]/files/route'), { GET: handlers.readFiles }],
  [() => import('@/app/api/studio/chats/[chatId]/files/download/route'), { GET: handlers.downloadFiles }],
] as const;

describe('Studio API route wiring', () => {
  it.each(endpoints)('exposes only the guarded handlers for endpoint %#', async (load, expected) => {
    const route = await load().catch(() => ({}));
    expect(route).toMatchObject({ ...expected, runtime: 'nodejs', dynamic: 'force-dynamic' });
  });
});
