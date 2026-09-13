create table public.studio_chats (
  id uuid primary key default gen_random_uuid(),
  owner_subject text not null check (char_length(owner_subject) between 1 and 512),
  request_id uuid not null,
  request_hash text not null check (request_hash ~ '^[a-f0-9]{64}$'),
  v0_chat_id text unique check (char_length(v0_chat_id) between 1 and 256),
  title text not null default 'Untitled app' check (char_length(title) between 1 and 160),
  pack_source_hash text check (char_length(pack_source_hash) between 1 and 256),
  creation_state text not null default 'reserved' check (creation_state in ('reserved', 'ready', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint studio_chats_owner_request_unique unique (owner_subject, request_id),
  constraint studio_chats_ready_binding check ((creation_state = 'ready') = (v0_chat_id is not null))
);

create index studio_chats_owner_created_idx on public.studio_chats (owner_subject, created_at desc, id desc);

alter table public.studio_chats enable row level security;
alter table public.studio_chats force row level security;
revoke all on table public.studio_chats from public, anon, authenticated;
grant select, insert, update, delete on table public.studio_chats to service_role;
