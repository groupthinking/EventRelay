import 'server-only';

import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { z } from 'zod';
import { StudioError } from './errors';
import type { StudioOwner } from './security';

const rowSchema = z.object({
  id: z.uuid(),
  owner_subject: z.string().min(1).max(512),
  request_id: z.uuid(),
  request_hash: z.string().regex(/^[a-f0-9]{64}$/),
  v0_chat_id: z.string().min(1).max(256).nullable(),
  title: z.string().min(1).max(160),
  pack_source_hash: z.string().min(1).max(256).nullable(),
  creation_state: z.enum(['reserved', 'ready', 'failed']),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
}).refine((row) => (row.creation_state === 'ready') === (row.v0_chat_id !== null));

type StudioChatRow = z.infer<typeof rowSchema>;
type StudioDatabase = {
  public: {
    Tables: {
      studio_chats: {
        Row: StudioChatRow;
        Insert: Pick<StudioChatRow, 'owner_subject' | 'request_id' | 'request_hash'> & Partial<Omit<StudioChatRow, 'owner_subject' | 'request_id' | 'request_hash'>>;
        Update: Partial<StudioChatRow>;
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
  };
};

export type StudioChat = {
  id: string;
  requestId: string;
  requestHash: string;
  v0ChatId: string | null;
  title: string;
  packSourceHash: string | null;
  creationState: 'reserved' | 'ready' | 'failed';
  createdAt: string;
  updatedAt: string;
};

const reservationSchema = z.object({
  requestId: z.uuid(),
  requestHash: z.string().regex(/^[a-f0-9]{64}$/),
  title: z.string().trim().min(1).max(160),
  packSourceHash: z.string().min(1).max(256).nullable(),
}).strict();

const columns = 'id,owner_subject,request_id,request_hash,v0_chat_id,title,pack_source_hash,creation_state,created_at,updated_at';
let cachedClient: { url: string; key: string; client: SupabaseClient<StudioDatabase> } | undefined;

function unavailable(): StudioError {
  return new StudioError(503, 'ownership_unavailable', 'Studio ownership storage is unavailable.');
}

function clientForOwner(owner: StudioOwner): SupabaseClient<StudioDatabase> {
  if (!owner.subject?.trim() || owner.subject.length > 512) {
    throw new StudioError(401, 'authentication_required', 'Sign in to use the app builder.');
  }
  const url = (process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL)?.trim();
  const key = (process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY)?.trim();
  if (!url || !key) throw unavailable();
  if (cachedClient?.url === url && cachedClient.key === key) return cachedClient.client;

  try {
    const endpoint = new URL(url);
    if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password) throw unavailable();
    const client = createClient<StudioDatabase>(url, key, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
      global: {
        fetch: (input, init) => fetch(input, {
          ...init,
          cache: 'no-store',
          signal: init?.signal
            ? AbortSignal.any([init.signal, AbortSignal.timeout(10_000)])
            : AbortSignal.timeout(10_000),
        }),
      },
    });
    cachedClient = { url, key, client };
    return client;
  } catch {
    throw unavailable();
  }
}

function validateId(id: string): void {
  if (!z.uuid().safeParse(id).success) {
    throw new StudioError(400, 'invalid_chat_id', 'Invalid Studio chat identifier.');
  }
}

function chatFromRow(data: unknown, owner: StudioOwner): StudioChat {
  const parsed = rowSchema.safeParse(data);
  if (!parsed.success || parsed.data.owner_subject !== owner.subject) throw unavailable();
  const row = parsed.data;
  return {
    id: row.id,
    requestId: row.request_id,
    requestHash: row.request_hash,
    v0ChatId: row.v0_chat_id,
    title: row.title,
    packSourceHash: row.pack_source_hash,
    creationState: row.creation_state,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export async function listStudioChats(owner: StudioOwner): Promise<StudioChat[]> {
  const { data, error } = await clientForOwner(owner).from('studio_chats')
    .select(columns)
    .eq('owner_subject', owner.subject)
    .eq('creation_state', 'ready')
    .order('created_at', { ascending: false })
    .order('id', { ascending: false })
    .limit(50);
  if (error || !Array.isArray(data)) throw unavailable();
  return data.map((row) => {
    const chat = chatFromRow(row, owner);
    if (chat.creationState !== 'ready') throw unavailable();
    return chat;
  });
}

export async function getStudioChat(owner: StudioOwner, id: string): Promise<StudioChat> {
  validateId(id);
  const { data, error } = await clientForOwner(owner).from('studio_chats')
    .select(columns)
    .eq('owner_subject', owner.subject)
    .eq('id', id)
    .eq('creation_state', 'ready')
    .maybeSingle();
  if (error) throw unavailable();
  if (!data) throw new StudioError(404, 'chat_not_found', 'Studio chat not found.');
  const chat = chatFromRow(data, owner);
  if (chat.creationState !== 'ready' || chat.id !== id) throw unavailable();
  return chat;
}

export async function reserveStudioChat(
  owner: StudioOwner,
  input: z.input<typeof reservationSchema>,
): Promise<{ chat: StudioChat; isNew: boolean }> {
  const parsed = reservationSchema.safeParse(input);
  if (!parsed.success) throw new StudioError(400, 'invalid_request', 'Invalid Studio creation request.');
  const request = parsed.data;
  const client = clientForOwner(owner);
  const { data, error } = await client.from('studio_chats').insert({
    owner_subject: owner.subject,
    request_id: request.requestId,
    request_hash: request.requestHash,
    title: request.title,
    pack_source_hash: request.packSourceHash,
  }).select(columns).single();

  if (!error && data) {
    const chat = chatFromRow(data, owner);
    if (chat.requestId !== request.requestId || chat.requestHash !== request.requestHash || chat.creationState !== 'reserved') {
      throw unavailable();
    }
    return { chat, isNew: true };
  }
  if (error?.code !== '23505') throw unavailable();

  // The database uniqueness constraint arbitrates concurrent retries. Never
  // reopen a reservation: an interrupted upstream create may already exist.
  const existing = await client.from('studio_chats').select(columns)
    .eq('owner_subject', owner.subject)
    .eq('request_id', request.requestId)
    .maybeSingle();
  if (existing.error || !existing.data) throw unavailable();
  const chat = chatFromRow(existing.data, owner);
  if (chat.requestId !== request.requestId) throw unavailable();
  if (chat.requestHash !== request.requestHash) {
    throw new StudioError(409, 'request_conflict', 'This request identifier belongs to different content.');
  }
  return { chat, isNew: false };
}

export async function bindStudioChat(owner: StudioOwner, id: string, v0ChatId: string): Promise<StudioChat> {
  validateId(id);
  if (!z.string().trim().min(1).max(256).safeParse(v0ChatId).success) {
    throw new StudioError(400, 'invalid_upstream_id', 'Invalid upstream chat identifier.');
  }
  const { data, error } = await clientForOwner(owner).from('studio_chats')
    .update({ v0_chat_id: v0ChatId, creation_state: 'ready', updated_at: new Date().toISOString() })
    .eq('owner_subject', owner.subject)
    .eq('id', id)
    .eq('creation_state', 'reserved')
    .select(columns)
    .maybeSingle();
  if (error) throw unavailable();
  if (!data) throw new StudioError(409, 'creation_conflict', 'Chat ownership could not be bound.');
  const chat = chatFromRow(data, owner);
  if (chat.id !== id || chat.v0ChatId !== v0ChatId || chat.creationState !== 'ready') throw unavailable();
  return chat;
}

export async function failStudioChat(owner: StudioOwner, id: string): Promise<void> {
  validateId(id);
  const { error } = await clientForOwner(owner).from('studio_chats')
    .update({ creation_state: 'failed', updated_at: new Date().toISOString() })
    .eq('owner_subject', owner.subject)
    .eq('id', id)
    .eq('creation_state', 'reserved');
  if (error) throw unavailable();
}
